import Phaser from "phaser";
import { ArcologyScene, arcologyConfig } from "./ArcologyScene";
import { webCanonicalHash } from "./hash";
import { loadJson, parseAssetPack, parseReplayV2 } from "./replay";
import { replaySource } from "./source";
import { installArcologyRail } from "./arcologyNav";
import type { CanonicalEvent, EpistemicFlowKind, EvidenceRecord, FlowType, ProjectionFrame, ReplayV2, RuntimePreferences, SelectionDetail, WorldEntity } from "./types";
import "./style.css";

const ASSET_PACK_URL = "/assets/noctiluca/asset-pack.json";
installArcologyRail("replay");

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
  const projectionSnapshot = (frame: ProjectionFrame | undefined, event: CanonicalEvent): Record<string, unknown> => {
    if (!frame) return { unavailable: true };
    const agents = frame.state.agents && typeof frame.state.agents === "object" ? frame.state.agents as Record<string, unknown> : {};
    const artifacts = frame.state.artifacts && typeof frame.state.artifacts === "object" ? frame.state.artifacts as Record<string, unknown> : {};
    return {
      cursor: frame.cursor,
      event_id: frame.event_id ?? null,
      agents: Object.fromEntries(event.actor_ids.filter((id) => id in agents).map((id) => [id, agents[id]])),
      artifacts: Object.fromEntries(event.artifact_ids.filter((id) => id in artifacts).map((id) => [id, artifacts[id]])),
      completed_years: frame.state.completed_years ?? [],
    };
  };
  const causeCards = refs.map((event) => {
    const before = replay.projection.frames[event.sequence];
    const after = replay.projection.frames[event.sequence + 1];
    return `<article class="cause-card">
      <h4>CAUSE // ${escapeHtml(event.kind)}</h4>
      <p>actors ${escapeHtml(event.actor_ids.join(", ") || "none")} · artifacts ${escapeHtml(event.artifact_ids.join(", ") || "none")}</p>
      <pre>${escapeHtml(JSON.stringify({ payload: event.payload ?? {}, provenance: event.provenance }, null, 2))}</pre>
      <div class="projection-pair">
        <article><h5>AUTHORITATIVE BEFORE</h5><pre>${escapeHtml(JSON.stringify(projectionSnapshot(before, event), null, 2))}</pre></article>
        <article><h5>AUTHORITATIVE AFTER</h5><pre>${escapeHtml(JSON.stringify(projectionSnapshot(after, event), null, 2))}</pre></article>
      </div>
    </article>`;
  }).join("");
  return `
    <dl class="evidence-card">
      <div><dt>TRUTH STATUS</dt><dd><span class="truth-chip" data-truth="${escapeHtml(record.truth_status)}">${escapeHtml(record.truth_status.toUpperCase())}</span></dd></div>
      <div><dt>RECORD ID</dt><dd><code>${escapeHtml(record.id)}</code></dd></div>
      <div><dt>TYPE</dt><dd>${escapeHtml(record.kind)}</dd></div>
      <div><dt>LOGICAL TIME</dt><dd>${formatTime(record.logical_timestamp_ms)}</dd></div>
      ${record.derivation_version ? `<div><dt>DERIVATION</dt><dd>${escapeHtml(record.derivation_version)}</dd></div>` : ""}
      ${record.causal_parent_id ? `<div><dt>CAUSAL PARENT</dt><dd><code>${escapeHtml(record.causal_parent_id)}</code></dd></div>` : ""}
    </dl>
    <section class="evidence-links"><h3>CANONICAL CAUSE &amp; EVIDENCE</h3>${record.truth_status === "canonical" ? "<p>Direct fact from the canonical event stream.</p>" : refs.length ? refs.map((event) => `<button type="button" data-event-id="${escapeHtml(event.id)}"><strong>${escapeHtml(event.label)}</strong><code>${escapeHtml(event.id)}</code></button>`).join("") : `<p>${record.truth_status === "ambient" ? "No scientific claim; atmosphere only." : "No source event is attached."}</p>`}${causeCards}</section>
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
  const entities = [...replay.canonical.entities.researchers, ...replay.canonical.entities.institutions, ...replay.canonical.entities.artifacts, ...replay.choreography.workflow_nodes, ...replay.choreography.workstations, ...replay.ambient.actors];
  const group = (title: string, rows: Array<WorldEntity | EvidenceRecord>, category: SelectionDetail["category"]): string => `
    <section><h3>${escapeHtml(title)}</h3><ul>${rows.map((row) => `<li><button type="button" data-select-id="${escapeHtml(row.id)}" data-select-category="${escapeHtml(category)}"><span>${escapeHtml(row.label)}</span><small>${escapeHtml(row.truth_status)}; ${escapeHtml(row.kind)}; ${formatTime(row.logical_timestamp_ms)}</small></button></li>`).join("")}</ul></section>`;
  target.innerHTML = group("Entities, workflow nodes, and workstations", entities, "entity") + group("Researcher actions", replay.choreography.actions, "action") + group("Institution interior activities", replay.choreography.interior_activities, "interior") + group("Information flows", replay.choreography.flows, "flow") + group("Epistemic routes", replay.choreography.epistemic_flows, "epistemic") + group("Canonical events", replay.canonical.events, "event");
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
    button.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent<number>("noctiluca:seek", { detail: event.logical_timestamp_ms }));
      window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: event.id, category: "event" } }));
    });
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
    const entities = [...replay.canonical.entities.researchers, ...replay.canonical.entities.institutions, ...replay.canonical.entities.artifacts, ...replay.choreography.workflow_nodes, ...replay.choreography.workstations, ...replay.ambient.actors];
    const record = category === "entity" ? entities.find((item) => item.id === id) : category === "flow" ? replay.choreography.flows.find((item) => item.id === id) : category === "epistemic" ? replay.choreography.epistemic_flows.find((item) => item.id === id) : category === "interior" ? replay.choreography.interior_activities.find((item) => item.id === id) : category === "action" ? replay.choreography.actions.find((item) => item.id === id) : replay.canonical.events.find((item) => item.id === id);
    if (!record) return;
    scene.select(id);
    kicker.textContent = category === "interior" ? "INSTITUTION INTERIOR · CANONICAL SOURCES" : category === "epistemic" ? "EPISTEMIC ROUTE · CANONICAL SOURCES" : category === "flow" ? "INFORMATION FLOW" : category === "action" ? "DERIVED RESEARCHER ACTION" : category === "event" ? "CANONICAL EVENT" : "ENTITY DOSSIER";
    heading.textContent = record.label;
    body.innerHTML = evidenceMarkup(record, replay);
    inspector.hidden = false;
    body.querySelectorAll<HTMLButtonElement>("[data-event-id]").forEach((button) => button.addEventListener("click", () => {
      const eventId = button.dataset.eventId;
      const source = replay.canonical.events.find((item) => item.id === eventId);
      if (source) {
        window.dispatchEvent(new CustomEvent<number>("noctiluca:seek", { detail: source.logical_timestamp_ms }));
        window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: source.id, category: "event" } }));
      }
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
  const eventTimes = [...new Set(replay.canonical.events.map((event) => event.logical_timestamp_ms))].sort((a, b) => a - b);
  const chapterNav = required<HTMLElement>("chapter-nav");
  const epistemicStatus = required<HTMLElement>("epistemic-status");
  const interiorStatus = required<HTMLElement>("interior-status");

  const setCursor = (value: number): void => {
    cursor = Math.max(0, Math.min(value, replay.choreography.duration_ms));
    timeline.value = String(Math.round(cursor));
    output.value = formatTime(cursor);
    scene.setCursor(cursor);
    chapterNav.querySelectorAll<HTMLButtonElement>("button[data-start]").forEach((button) => {
      const start = Number(button.dataset.start);
      const end = Number(button.dataset.end);
      button.dataset.active = String(cursor >= start && cursor <= end);
    });
    const activeRoutes = replay.choreography.epistemic_flows.filter((flow) => cursor >= flow.logical_timestamp_ms && cursor <= flow.logical_timestamp_ms + flow.duration_ms);
    epistemicStatus.textContent = activeRoutes.length
      ? `EPISTEMIC ROUTE // ${activeRoutes.map((flow) => flow.flow_kind.toUpperCase()).join(" + ")} // ${activeRoutes.reduce((sum, flow) => sum + flow.derived_from_event_ids.length, 0)} CANONICAL EVENT${activeRoutes.length === 1 && activeRoutes[0]!.derived_from_event_ids.length === 1 ? "" : "S"}`
      : "EPISTEMIC ROUTE // IDLE";
    epistemicStatus.dataset.kind = activeRoutes[0]?.flow_kind ?? "idle";
    const activeInteriors = replay.choreography.interior_activities.filter((activity) => cursor >= activity.logical_timestamp_ms && cursor <= activity.logical_timestamp_ms + activity.duration_ms);
    interiorStatus.textContent = activeInteriors.length
      ? `INSTITUTION INTERIOR // ${activeInteriors.map((activity) => activity.activity_type.toUpperCase()).join(" + ")} // ${activeInteriors.length} ACTIVE`
      : "INSTITUTION INTERIOR // IDLE";
    interiorStatus.dataset.active = String(activeInteriors.length > 0);
  };
  const setPlaying = (value: boolean): void => {
    playing = value;
    play.textContent = playing ? "PAUSE" : "PLAY";
    play.setAttribute("aria-label", playing ? "Pause replay" : "Play replay");
  };
  play.addEventListener("click", () => setPlaying(!playing));
  timeline.addEventListener("input", () => { setPlaying(false); setCursor(Number(timeline.value)); });
  required<HTMLButtonElement>("step-back").addEventListener("click", () => { setPlaying(false); setCursor(eventTimes.filter((time) => time < cursor).at(-1) ?? 0); });
  required<HTMLButtonElement>("step-forward").addEventListener("click", () => { setPlaying(false); setCursor(eventTimes.find((time) => time > cursor) ?? replay.choreography.duration_ms); });
  window.addEventListener("noctiluca:seek", ((event: CustomEvent<number>) => { setPlaying(false); setCursor(event.detail); }) as EventListener);

  chapterNav.replaceChildren();
  for (const chapter of replay.choreography.chapters) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = chapter.label;
    button.dataset.start = String(chapter.logical_timestamp_ms);
    button.dataset.end = String(chapter.end_ms);
    button.title = `${formatTime(chapter.logical_timestamp_ms)}–${formatTime(chapter.end_ms)} · ${chapter.derived_from_event_ids.length} canonical events`;
    button.addEventListener("click", () => { setPlaying(false); setCursor(chapter.logical_timestamp_ms); });
    chapterNav.append(button);
  }

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
  required<HTMLFieldSetElement>("epistemic-filters").querySelectorAll<HTMLInputElement>("input[type=checkbox]").forEach((checkbox) => checkbox.addEventListener("change", () => scene.setEpistemicVisible(checkbox.value as EpistemicFlowKind, checkbox.checked)));
  const interiors = required<HTMLButtonElement>("interior-toggle");
  interiors.addEventListener("click", () => {
    const enabled = interiors.getAttribute("aria-pressed") !== "true";
    interiors.setAttribute("aria-pressed", String(enabled));
    interiors.textContent = `INTERIORS: ${enabled ? "ON" : "OFF"}`;
    scene.setInteriorsVisible(enabled);
  });
  const interiorAmbient = required<HTMLButtonElement>("interior-ambient-toggle");
  interiorAmbient.addEventListener("click", () => {
    const enabled = interiorAmbient.getAttribute("aria-pressed") !== "true";
    interiorAmbient.setAttribute("aria-pressed", String(enabled));
    interiorAmbient.textContent = `COSMETIC: ${enabled ? "ON" : "OFF"}`;
    scene.setInteriorAmbientVisible(enabled);
  });
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
      required<HTMLButtonElement>("step-back").click();
    } else if (event.key === "]") {
      event.preventDefault();
      setPlaying(false);
      required<HTMLButtonElement>("step-forward").click();
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
  if (urlParameters.get("follow") === "on") follow.click();
}

async function boot(): Promise<void> {
  installIntegerScaling();
  const errorPanel = required<HTMLDivElement>("world-error");
  let replayUrl = "allowlisted replay source";
  try {
    replayUrl = replaySource(window.location.search).url;
    const [replay, assetPack] = await Promise.all([
      loadJson(replayUrl, parseReplayV2),
      loadJson(ASSET_PACK_URL, parseAssetPack),
    ]);
    const actualHash = await webCanonicalHash(replay.canonical.raw_events);
    const supplied = (replay.web_stream_hash ?? replay.stream_hash).replace(/^sha256:/, "");
    if (supplied !== actualHash) throw new Error(`Canonical stream hash mismatch: supplied ${supplied}, recomputed ${actualHash}`);
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
        const category = replay.canonical.events.some((event) => event.id === selected)
          ? "event"
          : selected.startsWith("interior:") ? "interior" : selected.startsWith("epistemic:") ? "epistemic" : selected.startsWith("flow:") ? "flow" : selected.startsWith("action:") ? "action" : "entity";
        window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: selected, category } }));
      }
      const verification = required<HTMLDivElement>("verification");
      const verified = supplied === actualHash;
      verification.dataset.state = verified ? "verified" : "error";
      verification.textContent = verified ? `${replay.metadata.empirical ? "COMPLETED · " : "SYNTHETIC · "}STREAM VERIFIED` : "HASH MISMATCH";
      verification.title = verified ? `SHA-256 ${actualHash}` : `${replay.metadata.disclosure}; supplied ${supplied}, recomputed ${actualHash}`;
    }, { once: true });
    new Phaser.Game(arcologyConfig(scene));

    required<HTMLElement>("run-id").textContent = replay.metadata.run_id;
    required<HTMLElement>("branch-id").textContent = replay.metadata.branch;
    required<HTMLElement>("world-time").textContent = [replay.metadata.year, replay.metadata.phase].filter(Boolean).join(" / ") || "REPLAY";
    const disclosure = required<HTMLElement>("source-disclosure");
    disclosure.textContent = replay.metadata.claim_boundary ?? replay.metadata.disclosure;
    disclosure.title = [replay.metadata.campaign_id, replay.metadata.campaign_revision, replay.metadata.source_commit].filter(Boolean).join(" · ");
    const sourceMode = required<HTMLElement>("source-mode");
    sourceMode.textContent = replay.metadata.empirical ? "VERIFIED REAL CAMPAIGN" : "SYNTHETIC CONTRACT";
    sourceMode.dataset.source = replay.metadata.empirical ? "campaign" : "synthetic";
    renderSemanticWorld(replay);
    renderEventLane(replay);
  } catch (error) {
    required<HTMLDivElement>("loading-state").hidden = true;
    errorPanel.hidden = false;
    const message = error instanceof Error ? error.message : String(error);
    errorPanel.innerHTML = `<strong>REPLAY CHANNEL FAILED</strong><span>${escapeHtml(message)}</span><small>Expected ${escapeHtml(replayUrl)} and ${escapeHtml(ASSET_PACK_URL)}. The renderer does not invent scientific activity or substitute temporary art.</small>`;
    const verification = required<HTMLDivElement>("verification");
    verification.dataset.state = "error";
    verification.textContent = "LOAD ERROR";
  }
}

void boot();
