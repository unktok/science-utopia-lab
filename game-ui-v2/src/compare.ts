import Phaser from "phaser";
import { ArcologyScene, arcologyConfig } from "./ArcologyScene";
import { parseBranchManifest, verifyBranchBundle, type BranchManifest } from "./branch";
import { loadJson, parseAssetPack, parseReplayV2 } from "./replay";
import type { CanonicalEvent, ReplayV2, SelectionDetail } from "./types";
import "./style.css";
import "./compare.css";

const MANIFEST_URL = "/data/intervention-branches.manifest.json";
const ASSET_PACK_URL = "/assets/noctiluca/asset-pack.json";
const required = <T extends HTMLElement>(id: string): T => {
  const value = document.getElementById(id);
  if (!value) throw new Error(`Missing #${id}`);
  return value as T;
};
const escapeHtml = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const formatTime = (milliseconds: number): string => `${String(Math.floor(milliseconds / 60_000)).padStart(2, "0")}:${(milliseconds % 60_000 / 1000).toFixed(1).padStart(4, "0")}`;

function finalProjection(replay: ReplayV2): { status: string; balance: string } {
  const state = replay.projection.frames.at(-1)?.state ?? {};
  const artifacts = state.artifacts as Record<string, Record<string, unknown>> | undefined;
  const agents = state.agents as Record<string, Record<string, unknown>> | undefined;
  return {
    status: String(artifacts?.["paper:arcology-signals"]?.status ?? "—"),
    balance: String(agents?.["researcher:aya"]?.balance ?? "—"),
  };
}

function eventForSelection(replay: ReplayV2, selection: SelectionDetail): CanonicalEvent | undefined {
  if (selection.category === "event") return replay.canonical.events.find((event) => event.id === selection.id);
  const derived = selection.category === "flow"
    ? replay.choreography.flows.find((item) => item.id === selection.id)
    : selection.category === "action"
      ? replay.choreography.actions.find((item) => item.id === selection.id)
      : undefined;
  return replay.canonical.events.find((event) => event.id === derived?.derived_from_event_ids[0]);
}

function openInspector(branchIndex: number, replay: ReplayV2, selection: SelectionDetail): void {
  const inspector = required<HTMLElement>("compare-inspector");
  const direct = replay.canonical.events.find((event) => event.id === selection.id);
  const event = direct ?? eventForSelection(replay, selection);
  const record = direct ?? (selection.category === "flow" ? replay.choreography.flows.find((item) => item.id === selection.id) : selection.category === "action" ? replay.choreography.actions.find((item) => item.id === selection.id) : undefined);
  if (!event && !record) return;
  required<HTMLElement>("compare-inspector-kicker").textContent = `FUTURE ${branchIndex === 0 ? "A" : "B"} // ${direct ? "CANONICAL EVENT" : "DERIVED VISUAL → CANONICAL"}`;
  required<HTMLHeadingElement>("compare-inspector-title").textContent = record?.label ?? event?.label ?? "Evidence";
  required<HTMLDivElement>("compare-inspector-body").innerHTML = `
    <dl class="evidence-card">
      <div><dt>TRUTH STATUS</dt><dd><span class="truth-chip" data-truth="${direct ? "canonical" : "derived"}">${direct ? "CANONICAL" : "DERIVED"}</span></dd></div>
      <div><dt>RECORD ID</dt><dd><code>${escapeHtml(record?.id ?? event?.id)}</code></dd></div>
      ${event ? `<div><dt>SOURCE EVENT</dt><dd><code>${escapeHtml(event.id)}</code></dd></div><div><dt>EVENT TYPE</dt><dd>${escapeHtml(event.kind)}</dd></div><div><dt>PAYLOAD</dt><dd><pre>${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre></dd></div>` : ""}
    </dl>`;
  inspector.hidden = false;
}

function installManifestText(manifest: BranchManifest, replays: [ReplayV2, ReplayV2]): void {
  required<HTMLElement>("origin-event").textContent = `${manifest.shared_origin.split_after_event_type} // ${manifest.shared_origin.last_event_id.slice(0, 10)}`;
  required<HTMLParagraphElement>("fork-disclosure").textContent = manifest.disclosure;
  manifest.branches.forEach((branch, index) => {
    const event = replays[index]!.canonical.events.find((row) => row.id === branch.intervention_event_id);
    required<HTMLElement>(`branch-label-${index}`).textContent = branch.label;
    required<HTMLElement>(`branch-hash-${index}`).textContent = `SHA256 ${branch.stream_hash.slice(0, 10)}`;
    required<HTMLElement>(`intervention-label-${index}`).textContent = String(event?.payload?.change ?? event?.label ?? "—");
    required<HTMLElement>(`intervention-id-${index}`).textContent = branch.intervention_event_id;
    required<HTMLElement>(`branch-panel-${index}`).style.setProperty("--branch-accent", branch.color);
    required<HTMLButtonElement>(`intervention-${index}`).addEventListener("click", () => openInspector(index, replays[index]!, { id: branch.intervention_event_id, category: "event" }));
    const summary = finalProjection(replays[index]!);
    const values = required<HTMLElement>(`projection-${index}`).querySelectorAll("dd");
    if (values[0]) values[0].textContent = summary.status.toUpperCase();
    if (values[1]) values[1].textContent = summary.balance;
  });
}

function installTransport(replays: [ReplayV2, ReplayV2], scenes: [ArcologyScene, ArcologyScene]): void {
  const duration = Math.min(...replays.map((replay) => replay.choreography.duration_ms));
  const slider = required<HTMLInputElement>("compare-timeline");
  const output = required<HTMLOutputElement>("compare-time");
  const play = required<HTMLButtonElement>("compare-play");
  slider.max = String(duration);
  let cursor = 0;
  let playing = false;
  let lastFrame = performance.now();
  const setCursor = (next: number): void => {
    cursor = Math.max(0, Math.min(duration, next));
    slider.value = String(Math.round(cursor));
    output.value = formatTime(cursor);
    scenes.forEach((scene) => scene.setCursor(cursor));
  };
  const setPlaying = (next: boolean): void => {
    playing = next;
    play.textContent = next ? "PAUSE BOTH" : "PLAY BOTH";
  };
  play.addEventListener("click", () => setPlaying(!playing));
  slider.addEventListener("input", () => { setPlaying(false); setCursor(Number(slider.value)); });
  required<HTMLButtonElement>("compare-back").addEventListener("click", () => { setPlaying(false); setCursor(cursor - 1000); });
  required<HTMLButtonElement>("compare-forward").addEventListener("click", () => { setPlaying(false); setCursor(cursor + 1000); });
  const tick = (now: number): void => {
    if (playing) {
      const next = cursor + Math.min(100, now - lastFrame);
      setCursor(next);
      if (next >= duration) setPlaying(false);
    }
    lastFrame = now;
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  const requested = Number(new URLSearchParams(location.search).get("cursor") ?? 0);
  setCursor(Number.isFinite(requested) ? requested : 0);
}

async function boot(): Promise<void> {
  const verification = required<HTMLElement>("compare-verification");
  try {
    const manifest = await loadJson(MANIFEST_URL, parseBranchManifest);
    const [assetPack, left, right] = await Promise.all([
      loadJson(ASSET_PACK_URL, parseAssetPack),
      loadJson(manifest.branches[0].replay_url, parseReplayV2),
      loadJson(manifest.branches[1].replay_url, parseReplayV2),
    ]);
    const replays: [ReplayV2, ReplayV2] = [left, right];
    await verifyBranchBundle(manifest, replays);
    installManifestText(manifest, replays);
    const inspectParameter = new URLSearchParams(location.search).get("inspect");
    const inspectBranch = inspectParameter === null ? Number.NaN : Number(inspectParameter);
    if (inspectBranch === 0 || inspectBranch === 1) {
      openInspector(inspectBranch, replays[inspectBranch], {
        id: manifest.branches[inspectBranch].intervention_event_id,
        category: "event",
      });
    }
    verification.dataset.state = "verified";
    verification.textContent = "2 STREAMS + ORIGIN VERIFIED";
    verification.title = `origin SHA-256 ${manifest.shared_origin.stream_hash}`;
    const scenes = replays.map((replay, index) => new ArcologyScene(replay, assetPack, {
      key: `ArcologyBranch${index}`,
      onSelect: (selection) => openInspector(index, replay, selection),
      onReady: () => { required<HTMLElement>(`loading-state-${index}`).hidden = true; },
    })) as [ArcologyScene, ArcologyScene];
    scenes.forEach((scene, index) => { new Phaser.Game(arcologyConfig(scene, `phaser-root-${index}`)); });
    installTransport(replays, scenes);
  } catch (error) {
    verification.dataset.state = "error";
    verification.textContent = "EVIDENCE CONTRACT FAILED";
    required<HTMLParagraphElement>("fork-disclosure").textContent = error instanceof Error ? error.message : String(error);
  }
}

required<HTMLButtonElement>("compare-inspector-close").addEventListener("click", () => { required<HTMLElement>("compare-inspector").hidden = true; });
void boot();
