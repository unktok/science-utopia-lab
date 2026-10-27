import Phaser from "phaser";
import { ArcologyScene, arcologyConfig } from "./ArcologyScene";
import { canonicalHash } from "./hash";
import { loadJson, parseAssetPack, parseReplayV2 } from "./replay";
import type { EvidenceRecord, FlowType, ReplayV2, RuntimePreferences, SelectionDetail, WorldEntity } from "./types";
import "./style.css";

const REPLAY_URL = "/data/vertical-slice.replay.json";
const ASSET_PACK_URL = "/assets/noctiluca/asset-pack.json";

const required = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing required DOM node #${id}`);
  return node as T;
};

const escapeHtml = (value: unknown): string => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const formatTime = (milliseconds: number): string => {
  const seconds = milliseconds / 1000;
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
};

function evidenceMarkup(record: EvidenceRecord, replay: ReplayV2): string {
  const refs = record.derived_from_event_ids
    .map((id) => replay.canonical.events.find((event) => event.id === id))
    .filter((event): event is NonNullable<typeof event> => Boolean(event));
  return `
    <dl class="evidence-card">
      <div><dt>TRUTH STATUS</dt><dd><span class="truth-chip" data-truth="${escapeHtml(record.truth_status)}">${escapeHtml(record.truth_status.toUpperCase())}</span></dd></div>
      <div><dt>RECORD ID</dt><dd><code>${escapeHtml(record.id)}</code></dd></div>
      <div><dt>TYPE</dt><dd>${escapeHtml(record.kind)}</dd></div>
      <div><dt>LOGICAL TIME</dt><dd>${formatTime(record.logical_timestamp_ms)}</dd></div>
      ${record.derivation_version ? `<div><dt>DERIVATION</dt><dd>${escapeHtml(record.derivation_version)}</dd></div>` : ""}
      ${record.causal_parent_id ? `<div><dt>CAUSAL PARENT</dt><dd><code>${escapeHtml(record.causal_parent_id)}</code></dd></div>` : ""}
    </dl>
    <section class="evidence-links"><h3>CANONICAL EVIDENCE</h3>${record.truth_status === "canonical" ? "<p>Direct fact from the canonical event stream.</p>" : refs.length ? refs.map((event) => `<button type="button" data-event-id="${escapeHtml(event.id)}"><strong>${escapeHtml(event.label)}</strong><code>${escapeHtml(event.id)}</code></button>`).join("") : `<p>${record.truth_status === "ambient" ? "No scientific claim; atmosphere only." : "No source event is attached."}</p>`}</section>
  `;
}

function installIntegerScaling(): void {
  const frame = required<HTMLDivElement>("game-frame");
  const root = required<HTMLDivElement>("phaser-root");
  const resize = (): void => {
    const availableWidth = Math.max(480, Math.min(window.innerWidth - (window.innerWidth > 980 ? 390 : 24), 1440));
    const availableHeight = Math.max(270, window.innerHeight - 238);
    const scale = Math.max(1, Math.min(3, Math.floor(Math.min(availableWidth / 480, availableHeight / 270))));
    frame.style.setProperty("--display-width", `${480 * scale}px`);
    frame.style.setProperty("--display-height", `${270 * scale}px`);
    root.dataset.scale = String(scale);
  };
  resize();
  window.addEventListener("resize", resize);
}

function renderSemanticWorld(replay: ReplayV2): void {
  const target = required<HTMLDivElement>("semantic-entities");
  const entities = [...replay.canonical.entities.researchers, ...replay.canonical.entities.institutions, ...replay.canonical.entities.artifacts, ...replay.ambient.actors];
  const group = (title: string, rows: Array<WorldEntity | EvidenceRecord>, category: "entity" | "flow" | "event"): string => `
    <section><h3>${escapeHtml(title)}</h3><ul>${rows.map((row) => `<li><button type="button" data-select-id="${escapeHtml(row.id)}" data-select-category="${escapeHtml(category)}"><span>${escapeHtml(row.label)}</span><small>${escapeHtml(row.truth_status)}; ${escapeHtml(row.kind)}; ${formatTime(row.logical_timestamp_ms)}</small></button></li>`).join("")}</ul></section>`;
  target.innerHTML = group("Entities", entities, "entity") + group("Information flows", replay.choreography.flows, "flow") + group("Canonical events", replay.canonical.events, "event");
  target.querySelectorAll<HTMLButtonElement>("[data-select-id]").forEach((button) => button.addEventListener("click", () => {
    const id = button.dataset.selectId;
    const category = button.dataset.selectCategory as SelectionDetail["category"] | undefined;
    if (id && category) window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id, category } }));
  }));
}

function renderEventLane(replay: ReplayV2): void {
  const lane = required<HTMLDivElement>("event-lane");
  lane.replaceChildren();
  for (const event of replay.canonical.events) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "event-lane__marker";
    button.style.left = `${Math.min(100, event.logical_timestamp_ms / replay.choreography.duration_ms * 100)}%`;
    button.title = `${formatTime(event.logical_timestamp_ms)} — ${event.label}`;
    button.setAttribute("aria-label", button.title);
    button.addEventListener("click", () => window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: event.id, category: "event" } })));
    lane.append(button);
  }
}

function installInspector(replay: ReplayV2, scene: ArcologyScene): void {
  const inspector = required<HTMLElement>("inspector");
  const heading = required<HTMLHeadingElement>("inspector-heading");
  const body = required<HTMLDivElement>("inspector-body");
  const kicker = required<HTMLSpanElement>("inspector-kicker");
  const close = (): void => { inspector.hidden = true; };
  required<HTMLButtonElement>("inspector-close").addEventListener("click", close);
  window.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
  window.addEventListener("noctiluca:select", ((event: CustomEvent<SelectionDetail>) => {
    const { id, category } = event.detail;
    const entities = [...replay.canonical.entities.researchers, ...replay.canonical.entities.institutions, ...replay.canonical.entities.artifacts, ...replay.ambient.actors];
    const record = category === "entity" ? entities.find((item) => item.id === id) : category === "flow" ? replay.choreography.flows.find((item) => item.id === id) : replay.canonical.events.find((item) => item.id === id);
    if (!record) return;
    scene.select(id);
    kicker.textContent = category === "flow" ? "INFORMATION FLOW" : category === "event" ? "CANONICAL EVENT" : "ENTITY DOSSIER";
    heading.textContent = record.label;
    body.innerHTML = evidenceMarkup(record, replay);
    inspector.hidden = false;
    body.querySelectorAll<HTMLButtonElement>("[data-event-id]").forEach((button) => button.addEventListener("click", () => {
      const eventId = button.dataset.eventId;
      if (eventId) window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: eventId, category: "event" } }));
    }));
    required<HTMLButtonElement>("inspector-close").focus();
  }) as EventListener);
}

function installControls(replay: ReplayV2, scene: ArcologyScene): void {
  const timeline = required<HTMLInputElement>("timeline");
  const play = required<HTMLButtonElement>("play-toggle");
  const output = required<HTMLOutputElement>("cursor-output");
  const speed = required<HTMLSelectElement>("speed");
  timeline.max = String(replay.choreography.duration_ms);
  let cursor = 0;
  let playing = false;
  let lastFrame = performance.now();
  const urlParameters = new URLSearchParams(window.location.search);

  const setCursor = (value: number): void => {
    cursor = Math.max(0, Math.min(value, replay.choreography.duration_ms));
    timeline.value = String(Math.round(cursor));
    output.value = formatTime(cursor);
    scene.setCursor(cursor);
  };
  const setPlaying = (value: boolean): void => {
    playing = value;
    play.textContent = playing ? "PAUSE" : "PLAY";
    play.setAttribute("aria-label", playing ? "Pause replay" : "Play replay");
  };
  play.addEventListener("click", () => setPlaying(!playing));
  timeline.addEventListener("input", () => { setPlaying(false); setCursor(Number(timeline.value)); });
  required<HTMLButtonElement>("step-back").addEventListener("click", () => { setPlaying(false); setCursor(cursor - 1000); });
  required<HTMLButtonElement>("step-forward").addEventListener("click", () => { setPlaying(false); setCursor(cursor + 1000); });

  const tick = (now: number): void => {
    const delta = Math.min(now - lastFrame, 100);
    lastFrame = now;
    if (playing) {
      const next = cursor + delta * Number(speed.value);
      if (next >= replay.choreography.duration_ms) setPlaying(false);
      setCursor(next >= replay.choreography.duration_ms ? replay.choreography.duration_ms : next);
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  required<HTMLFieldSetElement>("layer-filters").querySelectorAll<HTMLInputElement>("input[type=checkbox]").forEach((checkbox) => checkbox.addEventListener("change", () => scene.setLayerVisible(checkbox.value as FlowType, checkbox.checked)));
  const follow = required<HTMLButtonElement>("follow-toggle");
  follow.addEventListener("click", () => {
    const enabled = follow.getAttribute("aria-pressed") !== "true";
    follow.setAttribute("aria-pressed", String(enabled));
    follow.textContent = `FOLLOW: ${enabled ? "ON" : "OFF"}`;
    scene.setFollow(enabled);
  });
  window.addEventListener("keydown", (event) => {
    const target = event.target as HTMLElement | null;
    if (target?.matches("input, select, textarea, button")) return;
    if (event.key.toLowerCase() === "f") {
      event.preventDefault();
      follow.click();
    } else if (event.code === "Space") {
      event.preventDefault();
      play.click();
    } else if (event.key === "[") {
      event.preventDefault();
      setPlaying(false);
      setCursor(cursor - 1000);
    } else if (event.key === "]") {
      event.preventDefault();
      setPlaying(false);
      setCursor(cursor + 1000);
    }
  });

  const preferences: RuntimePreferences = {
    reducedMotion: urlParameters.get("motion") === "reduced" || matchMedia("(prefers-reduced-motion: reduce)").matches,
    highContrast: urlParameters.get("contrast") === "high" || matchMedia("(prefers-contrast: more)").matches,
    atmosphere: 0.62,
  };
  const applyPreferences = (): void => {
    document.documentElement.dataset.contrast = preferences.highContrast ? "high" : "normal";
    required<HTMLDivElement>("app").dataset.motion = preferences.reducedMotion ? "reduced" : "full";
    required<HTMLDivElement>("game-frame").style.setProperty("--atmosphere", String(preferences.atmosphere));
    scene.setPreferences(preferences);
  };
  const contrast = required<HTMLButtonElement>("contrast-toggle");
  contrast.setAttribute("aria-pressed", String(preferences.highContrast));
  contrast.addEventListener("click", () => { preferences.highContrast = !preferences.highContrast; contrast.setAttribute("aria-pressed", String(preferences.highContrast)); applyPreferences(); });
  const motion = required<HTMLButtonElement>("motion-toggle");
  motion.setAttribute("aria-pressed", String(preferences.reducedMotion));
  motion.addEventListener("click", () => { preferences.reducedMotion = !preferences.reducedMotion; motion.setAttribute("aria-pressed", String(preferences.reducedMotion)); applyPreferences(); });
  const atmosphere = required<HTMLInputElement>("atmosphere");
  atmosphere.addEventListener("input", () => { preferences.atmosphere = Number(atmosphere.value) / 100; applyPreferences(); });
  applyPreferences();
  const requestedCursor = Number(urlParameters.get("cursor") ?? 0);
  setCursor(Number.isFinite(requestedCursor) ? requestedCursor : 0);
}

async function boot(): Promise<void> {
  installIntegerScaling();
  const errorPanel = required<HTMLDivElement>("world-error");
  try {
    const [replay, assetPack] = await Promise.all([
      loadJson(REPLAY_URL, parseReplayV2),
      loadJson(ASSET_PACK_URL, parseAssetPack),
    ]);
    const scene = new ArcologyScene(replay, assetPack);
    const missing = new Set<string>();
    window.addEventListener("noctiluca:asset-missing", ((event: CustomEvent<{ key: string }>) => {
      missing.add(event.detail.key);
      errorPanel.hidden = false;
      errorPanel.innerHTML = `<strong>PRODUCTION ASSET MISSING</strong><span>${escapeHtml([...missing].join(", "))}</span><small>No generic substitute has been rendered.</small>`;
    }) as EventListener);
    window.addEventListener("noctiluca:renderer-ready", async () => {
      required<HTMLDivElement>("loading-state").hidden = true;
      installInspector(replay, scene);
      installControls(replay, scene);
      const selected = new URLSearchParams(window.location.search).get("select");
      if (selected) {
        const category = selected.startsWith("flow:") ? "flow" : selected.startsWith("event:") ? "event" : "entity";
        window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: selected, category } }));
      }
      const actualHash = await canonicalHash(replay.canonical.raw_events);
      const verification = required<HTMLDivElement>("verification");
      const supplied = replay.stream_hash.replace(/^sha256:/, "");
      const verified = supplied === actualHash;
      verification.dataset.state = verified ? "verified" : "error";
      verification.textContent = verified ? `${replay.metadata.empirical ? "" : "SYNTHETIC · "}STREAM VERIFIED` : "HASH MISMATCH";
      verification.title = verified ? `SHA-256 ${actualHash}` : `${replay.metadata.disclosure}; supplied ${supplied}, recomputed ${actualHash}`;
    }, { once: true });
    new Phaser.Game(arcologyConfig(scene));

    required<HTMLElement>("run-id").textContent = replay.metadata.run_id;
    required<HTMLElement>("branch-id").textContent = replay.metadata.branch;
    required<HTMLElement>("world-time").textContent = [replay.metadata.year, replay.metadata.phase].filter(Boolean).join(" / ") || "REPLAY";
    renderSemanticWorld(replay);
    renderEventLane(replay);
  } catch (error) {
    required<HTMLDivElement>("loading-state").hidden = true;
    errorPanel.hidden = false;
    const message = error instanceof Error ? error.message : String(error);
    errorPanel.innerHTML = `<strong>REPLAY CHANNEL FAILED</strong><span>${escapeHtml(message)}</span><small>Expected ${escapeHtml(REPLAY_URL)} and ${escapeHtml(ASSET_PACK_URL)}. The renderer does not invent scientific activity or substitute temporary art.</small>`;
    const verification = required<HTMLDivElement>("verification");
    verification.dataset.state = "error";
    verification.textContent = "LOAD ERROR";
  }
}

void boot();
