import { AdoptionController } from "./designLifecycleContract";
import { NativeSocietyApi, SocietyApiUnavailable, latestRecoverableAdoption, parseSocietyFixture, type NativeSocietyProjection, type SocietyRequest } from "./nativeSocietySession";

const node = <T extends HTMLElement>(id: string): T => { const value = document.getElementById(id); if (!value) throw new Error(`Missing same-society UI element ${id}`); return value as T; };
const escape = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const compact = (value: unknown, count = 16): string => typeof value === "string" && value.length > count ? `${value.slice(0, count)}…` : String(value ?? "—");
type Source = "real" | "fixture" | "unavailable" | "failed";

export class SameSocietyView {
  private projection: NativeSocietyProjection | null = null;
  private api: NativeSocietyApi | null = null;
  private controller: AdoptionController | null = null;
  private source: Source = "unavailable";
  private polling: number | undefined;
  private busy = false;

  constructor(private readonly search = location.search, private readonly fetcher: typeof fetch = fetch) {
    node("society-refresh").addEventListener("click", () => { void this.refresh(); });
    node("society-confirm-hash").addEventListener("input", () => this.updateConfirmAvailability());
    node("society-consent").addEventListener("change", () => this.updateConfirmAvailability());
    node("society-confirm").addEventListener("click", () => { void this.confirm(); });
    window.addEventListener("pagehide", () => { if (this.polling !== undefined) clearTimeout(this.polling); });
  }

  async start(): Promise<void> {
    if (new URLSearchParams(this.search).get("society") === "fixture") {
      const response = await this.fetcher.call(globalThis, "./data/native-society-session-ui-fixture-v1.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`Society UI fixture unavailable (${response.status})`);
      this.projection = parseSocietyFixture(await response.json()).projection;
      this.source = "fixture"; this.render(); return;
    }
    try {
      this.api = await NativeSocietyApi.connect(this.fetcher);
      this.controller = new AdoptionController(this.api);
      this.projection = await this.api.projection();
      this.source = "real";
      await this.restoreBackendState();
      this.render();
      if (this.controller.state === "pending") this.schedulePoll();
    } catch (error) {
      this.source = error instanceof SocietyApiUnavailable ? "unavailable" : "failed";
      this.renderUnavailable(error);
    }
  }

  private pending(): SocietyRequest | null { return this.projection?.pending ?? null; }

  private displayedRequest(): SocietyRequest | null {
    const pending = this.pending();
    if (pending) return pending;
    if (this.controller?.state !== "completed" || !this.projection) return null;
    return this.projection.requests.find((item) => item.request_id === this.controller!.requestId && item.request_sha256 === this.controller!.requestSha256) ?? null;
  }

  private async restoreBackendState(): Promise<void> {
    const pending = this.pending();
    if (!this.controller || this.controller.state !== "confirm-required") return;
    if (pending) {
      const confirmed = this.projection!.confirmations.some((item) => item.request_id === pending.request_id && item.request_sha256 === pending.request_sha256);
      if (confirmed) this.controller.resumePending(pending, pending.request_sha256);
      return;
    }
    const adopted = latestRecoverableAdoption(this.projection!);
    if (!adopted) return;
    this.controller.resumePending(adopted, adopted.request_sha256);
    await this.controller.refresh();
    if ((this.controller.state as string) !== "completed") throw new Error("Recorded adoption lacks a verified durable migration receipt");
  }

  private render(): void {
    if (!this.projection) return;
    const fixture = this.source === "fixture";
    node("society-truth").textContent = fixture ? "SYNTHETIC UI FIXTURE" : "VERIFIED LOCAL SESSION";
    node("society-truth").className = fixture ? "fixture" : "";
    node("society-service").textContent = fixture ? "ACTIONS DISABLED / NO BACKEND" : "LOOPBACK SERVICE / TOKEN BOUND";
    node("society-loss-title").textContent = String(this.projection.loss_spec.id ?? "EXPLICIT ONLINE LOSS");
    node("society-journal").textContent = this.projection.journal_sha256 ? `JOURNAL ${compact(this.projection.journal_sha256, 22)}` : "EMPTY JOURNAL / NO OBSERVATION";
    node("society-founding").textContent = compact(this.projection.binding.founding_fingerprint, 18);
    node("society-observation-count").textContent = String(this.projection.observations.length);
    node("society-request-count").textContent = String(this.projection.requests.length);
    this.renderIntervals(); this.renderAdoptions(); this.renderRequest();
  }

  private renderIntervals(): void {
    const observations = this.projection!.observations;
    node("society-intervals").innerHTML = observations.length ? observations.map((observation, index) => `<article class="interval-cell"><div class="interval-years"><span>INTERVAL ${index + 1}</span><b>Y${observation.after_year} → Y${observation.through_year}</b></div><strong>${escape(observation.loss)}</strong><code>SYSTEM ${escape(compact(observation.system_fingerprint, 20))}</code><p>${escape(observation.comparison.replaceAll("-", " ").toUpperCase())}</p>${observation.preceding_adoption ? `<span class="migration-pip">AFTER ADOPTION ${escape(compact(observation.preceding_adoption, 10))}</span>` : `<span class="migration-pip">FOUNDING DESIGN</span>`}</article>`).join("") : `<p>No completed scientific interval has been observed. No loss is invented.</p>`;
  }

  private renderAdoptions(): void {
    node("society-adoptions").className = "migration-ledger";
    node("society-adoptions").innerHTML = this.projection!.adoptions.length ? this.projection!.adoptions.map((adoption, index) => `<div class="migration-chip"><b>ADOPTION ${index + 1} / AFTER Y${adoption.after_year}</b><br />${escape(compact(adoption.candidate_fingerprint, 18))}<br />RECEIPT ${escape(compact(adoption.migration_receipt_sha256, 18))}</div>`).join("") : `<div class="migration-chip">NO DURABLE MIGRATION RECEIPT IN THIS SESSION</div>`;
  }

  private renderRequest(): void {
    const request = this.displayedRequest(), fixture = this.source === "fixture";
    const input = node<HTMLInputElement>("society-confirm-hash"), consent = node<HTMLInputElement>("society-consent");
    if (!request) {
      node("society-request-state").textContent = "NO STAGED REQUEST"; node("society-request-state").className = "";
      node("society-candidate").textContent = "Nothing staged";
      for (const id of ["society-request-id", "society-candidate-hash", "society-checkpoint", "society-author"]) node(id).textContent = "—";
      node("society-request-hash").textContent = "NO LIVE HASH"; input.value = ""; input.disabled = true; consent.checked = false; consent.disabled = true;
      node("society-action-status").textContent = "No exact staged request is waiting. Viewing observations performs no action.";
      this.updateConfirmAvailability(); return;
    }
    const mechanisms = Array.isArray((request.candidate_system as any).mechanisms) ? (request.candidate_system as any).mechanisms.length : null;
    node("society-request-state").textContent = fixture ? "FIXTURE / READ ONLY" : this.controller?.state === "pending" ? "WORKER PENDING" : this.controller?.state === "completed" ? "RECEIPT VERIFIED" : this.controller?.state === "failed" ? "REQUEST FAILED" : "STAGED / UNCONFIRMED";
    node("society-request-state").className = fixture ? "staged" : this.controller?.state ?? "staged";
    node("society-candidate").textContent = `${String((request.candidate_system as any).system_id ?? "CANDIDATE SYSTEM")} / ${mechanisms ?? "?"} NODES`;
    node("society-request-id").textContent = request.request_id;
    node("society-candidate-hash").textContent = compact(request.candidate_fingerprint, 24);
    node("society-checkpoint").textContent = compact(request.expected_checkpoint_sha256, 24);
    node("society-author").textContent = String((request.authoring as any).identity ?? "SELF-REPORTED / UNKNOWN");
    node("society-request-hash").textContent = request.request_sha256;
    input.disabled = fixture || this.busy || this.controller?.state === "pending" || this.controller?.state === "completed";
    consent.disabled = input.disabled;
    node("society-action-status").textContent = fixture ? "SYNTHETIC UI FIXTURE / confirmation and worker dispatch are disabled." : this.controller?.message ?? "Paste the exact displayed hash and explicitly authorize this staged request.";
    this.updateConfirmAvailability();
  }

  private updateConfirmAvailability(): void {
    const request = this.pending(), input = node<HTMLInputElement>("society-confirm-hash"), consent = node<HTMLInputElement>("society-consent"), button = node<HTMLButtonElement>("society-confirm");
    button.disabled = this.source !== "real" || !request || this.busy || input.disabled || input.value !== request.request_sha256 || !consent.checked || this.controller?.state === "pending" || this.controller?.state === "completed";
  }

  private renderUnavailable(error: unknown): void {
    node("society-truth").textContent = this.source === "unavailable" ? "LOCAL SERVICE UNAVAILABLE" : "SESSION READ FAILED";
    node("society-truth").className = "unavailable";
    node("society-service").textContent = String(error);
    node("society-loss-title").textContent = "NO LIVE SESSION LOADED";
    node("society-intervals").innerHTML = `<p>Start the loopback-only native lab with a configured society session to inspect continuity. No historical v5 candidate is submitted as a substitute.</p>`;
    node("society-action-status").textContent = "UNAVAILABLE / no POST was sent and no worker was authorized.";
    node<HTMLInputElement>("society-confirm-hash").disabled = true; node<HTMLInputElement>("society-consent").disabled = true; node<HTMLButtonElement>("society-confirm").disabled = true;
  }

  private async refresh(): Promise<void> {
    if (this.busy) return;
    if (this.source === "fixture") { this.render(); return; }
    if (!this.api) { await this.start(); return; }
    this.busy = true;
    try {
      if (this.controller?.state === "pending") await this.controller.refresh();
      this.projection = await this.api.projection(); await this.restoreBackendState(); this.source = "real"; this.render();
      if (this.controller?.state === "pending") this.schedulePoll();
    } catch (error) {
      if (error instanceof SocietyApiUnavailable) { this.source = "unavailable"; this.renderUnavailable(error); }
      else { node("society-action-status").textContent = `SESSION ERROR / ${String(error)}`; this.renderRequest(); }
    } finally {
      this.busy = false;
      if (this.source === "real") this.renderRequest();
    }
  }

  private async confirm(): Promise<void> {
    const request = this.pending(); if (!request || !this.controller || this.source !== "real" || this.busy) return;
    const exact = node<HTMLInputElement>("society-confirm-hash").value;
    this.busy = true; this.renderRequest();
    try {
      await this.controller.submit(request, exact);
      node<HTMLInputElement>("society-confirm-hash").value = ""; node<HTMLInputElement>("society-consent").checked = false;
      this.renderRequest(); this.schedulePoll();
    } catch (error) { node("society-action-status").textContent = `CONFIRMATION FAILED / ${String(error)}`; }
    finally { this.busy = false; this.renderRequest(); }
  }

  private schedulePoll(): void {
    if (this.polling !== undefined) clearTimeout(this.polling);
    if (this.controller?.state !== "pending" || this.source !== "real") return;
    this.polling = window.setTimeout(() => { this.polling = undefined; void this.refresh(); }, 2000);
  }
}

export function initializeSameSocietyView(): void {
  const view = new SameSocietyView();
  void view.start().catch((error) => {
    node("society-truth").textContent = "SESSION READ FAILED";
    node("society-truth").className = "unavailable";
    node("society-service").textContent = String(error);
    node("society-action-status").textContent = "FAIL CLOSED / no confirmation or worker authorization was sent.";
    node<HTMLInputElement>("society-confirm-hash").disabled = true;
    node<HTMLInputElement>("society-consent").disabled = true;
    node<HTMLButtonElement>("society-confirm").disabled = true;
  });
}
