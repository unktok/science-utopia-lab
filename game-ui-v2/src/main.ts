import Phaser from "phaser";
import { ArcologyScene, arcologyConfig } from "./ArcologyScene";
import { buildCollaborationEvidenceGraph, EVIDENCE_EDGE_KINDS, graphAtCursor, type EvidenceEdgeKind, type EvidenceGraphNode } from "./collaborationGraph";
import { agentStateAtCue, buildEvidenceQuayProjection, cueAtCursor } from "./evidenceQuay";
import { webCanonicalHash } from "./hash";
import { buildInstitutionalInteriorProjection, interiorAtCursor, type InteriorPose } from "./institutionInterior";
import { buildResearcherLifeCourseProjection, dossierAtCursor } from "./researcherLifeCourse";
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

interface EvidenceQuayController {
  setCursor(cursorMs: number): void;
}

interface InstitutionInteriorController {
  setCursor(cursorMs: number): void;
  toggle(): void;
}

interface ResearcherDossierController {
  setCursor(cursorMs: number): void;
  toggle(): void;
}

interface CollaborationGraphController {
  setCursor(cursorMs: number): void;
  toggle(): void;
}

function installEvidenceQuay(replay: ReplayV2): EvidenceQuayController {
  const quay = required<HTMLElement>("evidence-quay");
  const heading = required<HTMLHeadingElement>("quay-heading");
  const frameLabel = required<HTMLElement>("quay-frame");
  const origin = required<HTMLElement>("quay-origin");
  const destination = required<HTMLElement>("quay-destination");
  const courier = required<HTMLElement>("quay-courier");
  const workers = required<HTMLDivElement>("quay-workers");
  const eventButton = required<HTMLButtonElement>("quay-event");
  const boundary = required<HTMLParagraphElement>("quay-boundary");
  if (!replay.metadata.empirical) {
    quay.dataset.state = "synthetic";
    heading.textContent = "Unavailable for synthetic replay fixtures";
    frameLabel.textContent = "NO VERIFIED FRAME";
    boundary.innerHTML = "<strong>FAIL-CLOSED</strong> Evidence Quay only projects verified commit-pinned campaign events and authoritative frames.";
    return { setCursor: () => undefined };
  }
  const projection = buildEvidenceQuayProjection(replay);
  boundary.innerHTML = `<strong>TRUTH BOUNDARY</strong> ${escapeHtml(projection.disclosure)}`;
  eventButton.disabled = false;
  eventButton.addEventListener("click", () => {
    const id = eventButton.dataset.eventId;
    if (id) window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id, category: "event" } }));
  });
  let renderedEventId = "";
  return {
    setCursor(cursorMs: number): void {
      const selection = cueAtCursor(projection, cursorMs);
      if (!selection) {
        heading.textContent = "No canonical event applied yet";
        frameLabel.textContent = "FRAME 0 · INITIAL";
        courier.dataset.packet = "none";
        courier.style.left = "0%";
        workers.replaceChildren();
        eventButton.disabled = true;
        eventButton.removeAttribute("data-event-id");
        eventButton.innerHTML = "<strong>INITIAL AUTHORITATIVE FRAME</strong><span>Advance to the first canonical event.</span>";
        renderedEventId = "";
        return;
      }
      const { cue, progress } = selection;
      courier.style.left = `${Math.round(progress * 100)}%`;
      if (renderedEventId === cue.event.id) return;
      renderedEventId = cue.event.id;
      quay.dataset.activity = cue.activity;
      heading.textContent = `${cue.activity.toUpperCase()} // ${cue.activity_label}`;
      frameLabel.textContent = `FRAME ${cue.frame.cursor} · VERIFIED`;
      origin.textContent = cue.motion.from;
      destination.textContent = cue.motion.to;
      courier.dataset.packet = cue.motion.packet_kind;
      workers.innerHTML = cue.actor_ids.length ? cue.actor_ids.map((actorId) => {
        const state = agentStateAtCue(cue, actorId);
        const balance = typeof state?.balance === "number" ? `BAL ${state.balance.toFixed(0)}` : "STATE RECORDED";
        return `<button class="quay-worker" type="button" data-researcher-id="${escapeHtml(actorId)}" title="Open ${escapeHtml(actorId)}">
          <i class="quay-worker__pixel" aria-hidden="true"></i><strong>${escapeHtml(actorId)}</strong><small>${escapeHtml(balance)}</small>
        </button>`;
      }).join("") : "<span class=\"evidence-quay__system\">SYSTEM-LEVEL CANONICAL EVENT</span>";
      workers.querySelectorAll<HTMLButtonElement>("[data-researcher-id]").forEach((button) => button.addEventListener("click", () => {
        const id = button.dataset.researcherId;
        if (id) window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id, category: "entity" } }));
      }));
      eventButton.disabled = false;
      eventButton.dataset.eventId = cue.event.id;
      eventButton.innerHTML = `<strong>${escapeHtml(cue.event.kind)} · ${escapeHtml(cue.subject)}</strong><span>SEQ ${cue.event.sequence} · CANONICAL EVENT → AUTHORITATIVE FRAME ${cue.frame.cursor}</span>`;
    },
  };
}

function installInstitutionInteriors(replay: ReplayV2): InstitutionInteriorController {
  const deck = required<HTMLElement>("institution-interiors");
  const toggle = required<HTMLButtonElement>("interior-deck-toggle");
  const close = required<HTMLButtonElement>("interior-deck-close");
  const packet = required<HTMLElement>("interior-packet");
  const eventButton = required<HTMLButtonElement>("interior-fact-event");
  const researcherButton = required<HTMLButtonElement>("interior-fact-researcher");
  const graphButton = required<HTMLButtonElement>("interior-fact-graph");
  const factStatus = required<HTMLElement>("interior-fact-status");
  const factTitle = required<HTMLElement>("interior-fact-title");
  const factState = required<HTMLElement>("interior-fact-state");
  const boundary = required<HTMLElement>("interior-truth-boundary");
  let open = new URLSearchParams(window.location.search).get("interior") === "on";
  const setOpen = (value: boolean): void => {
    open = value;
    deck.hidden = !open;
    toggle.setAttribute("aria-pressed", String(open));
    toggle.textContent = `INTERIOR DECK: ${open ? "ON" : "OFF"}`;
  };
  if (!replay.metadata.empirical) {
    toggle.disabled = true;
    toggle.title = "Verified commit-pinned campaign replay required";
    setOpen(false);
    return { setCursor: () => undefined, toggle: () => undefined };
  }
  const projection = buildInstitutionalInteriorProjection(replay);
  boundary.innerHTML = `<strong>AUTHORITATIVE:</strong> canonical event and matching frame readout only. <strong>PRESENTATION-ONLY:</strong> ${escapeHtml(projection.disclosure.split(". ").at(-1) ?? "all spatial staging")}`;
  const roomNodes = [...deck.querySelectorAll<HTMLElement>("[data-room]")];
  const actorVariant = (id: string): number => [...id].reduce((sum, character) => sum + character.charCodeAt(0), 0) % 4;
  const actorMarkup = (id: string, pose: InteriorPose): string => `<i class="interior-researcher" data-variant="${actorVariant(id)}" data-pose="${escapeHtml(pose)}" title="${escapeHtml(id)} · presentation-only pose"><span class="interior-researcher__signal">${escapeHtml(pose.toUpperCase())}</span></i>`;
  eventButton.addEventListener("click", () => {
    const id = eventButton.dataset.eventId;
    if (id) window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id, category: "event" } }));
  });
  researcherButton.addEventListener("click", () => {
    const id = researcherButton.dataset.researcherId;
    if (id) window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id, category: "entity" } }));
  });
  graphButton.addEventListener("click", () => {
    const id = graphButton.dataset.graphId;
    if (id) window.dispatchEvent(new CustomEvent<{ id: string }>("noctiluca:graph-open", { detail: { id } }));
  });
  toggle.addEventListener("click", () => setOpen(!open));
  close.addEventListener("click", () => {
    setOpen(false);
    toggle.focus();
  });
  setOpen(open);
  let renderedEventId = "";
  return {
    toggle: () => toggle.click(),
    setCursor(cursorMs: number): void {
      const selected = interiorAtCursor(projection, cursorMs);
      if (!selected) return;
      packet.style.left = `${Math.round(selected.progress * 100)}%`;
      if (renderedEventId === selected.scene.evidence.event.id) return;
      renderedEventId = selected.scene.evidence.event.id;
      const { evidence, presentation, activity_label: activityLabel, subject } = selected.scene;
      packet.dataset.packet = presentation.packet_kind;
      for (const room of roomNodes) {
        const active = room.dataset.room === presentation.room_id;
        room.dataset.active = String(active);
        room.title = active ? `Presentation-only route: ${presentation.route_label}` : "Presentation-only institutional room";
        const occupants = room.querySelector<HTMLElement>(".interior-occupants");
        if (occupants) occupants.innerHTML = active ? Object.keys(evidence.actor_states).slice(0, 2).map((id) => actorMarkup(id, presentation.pose)).join("") : "";
      }
      const actorEntries = Object.entries(evidence.actor_states);
      const balanceReadout = actorEntries.map(([id, state]) => `${id}: ${typeof state.balance === "number" ? `balance ${state.balance}` : "state recorded"}`).join(" · ");
      const artifactEntries = Object.entries(evidence.artifact_states);
      const artifactReadout = artifactEntries.map(([, state]) => typeof state.status === "string" ? `paper ${state.status}` : "artifact recorded").join(" · ");
      factStatus.textContent = `${selected.scene.activity.toUpperCase()} · CANONICAL`;
      factTitle.textContent = `${activityLabel} · ${subject}`;
      factState.textContent = `AUTHORITATIVE FRAME ${evidence.frame.cursor}${balanceReadout ? ` · ${balanceReadout}` : ""}${artifactReadout ? ` · ${artifactReadout}` : ""}`;
      eventButton.disabled = false;
      eventButton.dataset.eventId = evidence.event.id;
      const primaryResearcher = Object.keys(evidence.actor_states)[0];
      researcherButton.disabled = !primaryResearcher;
      if (primaryResearcher) researcherButton.dataset.researcherId = primaryResearcher;
      else researcherButton.removeAttribute("data-researcher-id");
      graphButton.disabled = !primaryResearcher;
      if (primaryResearcher) graphButton.dataset.graphId = primaryResearcher;
      else graphButton.removeAttribute("data-graph-id");
    },
  };
}

function installResearcherDossier(replay: ReplayV2): ResearcherDossierController {
  const panel = required<HTMLElement>("researcher-dossier");
  const toggleButton = required<HTMLButtonElement>("dossier-toggle");
  const closeButton = required<HTMLButtonElement>("dossier-close");
  const graphButton = required<HTMLButtonElement>("dossier-graph");
  if (!replay.metadata.empirical) {
    toggleButton.disabled = true;
    toggleButton.title = "Verified commit-pinned campaign replay required";
    return { setCursor: () => undefined, toggle: () => undefined };
  }
  const projection = buildResearcherLifeCourseProjection(replay);
  const dossiers = new Map(projection.dossiers.map((dossier) => [dossier.researcher_id, dossier]));
  const defaultDossier = projection.dossiers.find((dossier) => dossier.researcher_id.includes("_researcher_")) ?? projection.dossiers[0]!;
  let selected = defaultDossier;
  let cursorMs = 0;
  let open = false;
  const setOpen = (value: boolean): void => {
    open = value;
    panel.hidden = !value;
    toggleButton.setAttribute("aria-pressed", String(value));
    toggleButton.textContent = `DOSSIER: ${value ? "ON" : "OFF"}`;
  };
  const selectEvent = (id: string): void => {
    const event = replay.canonical.events.find((candidate) => candidate.id === id);
    if (!event) return;
    window.dispatchEvent(new CustomEvent<number>("noctiluca:seek", { detail: event.logical_timestamp_ms }));
    window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id, category: "event" } }));
  };
  const render = (): void => {
    if (!open) return;
    const state = dossierAtCursor(projection, selected, cursorMs);
    const agent = state.agent_state;
    const active = typeof agent?.active === "boolean" ? agent.active : undefined;
    required<HTMLHeadingElement>("dossier-heading").textContent = selected.label;
    required<HTMLElement>("dossier-identity").textContent = `CANONICAL ID ${selected.researcher_id}`;
    graphButton.dataset.graphId = selected.researcher_id;
    required<HTMLElement>("dossier-frame").textContent = `${state.frame.cursor} · ${formatTime(state.frame.logical_timestamp_ms)}`;
    const activeNode = required<HTMLElement>("dossier-active");
    activeNode.textContent = active === undefined ? "NOT OBSERVED" : active ? "ACTIVE" : "INACTIVE AT FRAME";
    activeNode.dataset.state = active === false ? "inactive" : "active";
    required<HTMLElement>("dossier-face").dataset.state = active === false ? "inactive" : "active";
    required<HTMLElement>("dossier-balance").textContent = typeof agent?.balance === "number" ? agent.balance.toFixed(1) : "NOT OBSERVED";
    required<HTMLElement>("dossier-institution").textContent = typeof agent?.institution === "string" ? agent.institution : "NOT OBSERVED";

    const byYear = new Map<number, typeof state.events>();
    for (const event of state.events) byYear.set(event.event.year, [...(byYear.get(event.event.year) ?? []), event]);
    const timeline = required<HTMLElement>("dossier-timeline");
    timeline.innerHTML = byYear.size ? [...byYear.entries()].map(([year, events]) => `<section class="dossier-year"><strong>YEAR ${year}</strong><div class="dossier-year__events">${events.map(({ event, activity_kind: activityKind, canonical_label: label }) => `<button class="dossier-event" type="button" data-life-event="${escapeHtml(event.id)}" data-kind="${escapeHtml(activityKind)}"><time>${formatTime(event.logical_timestamp_ms)}</time><span>${escapeHtml(label)}</span></button>`).join("")}</div></section>`).join("") : "<p class=\"dossier-empty\">NO CANONICAL EVENTS OBSERVED AT THIS CURSOR</p>";
    timeline.querySelectorAll<HTMLButtonElement>("[data-life-event]").forEach((button) => button.addEventListener("click", () => {
      const id = button.dataset.lifeEvent;
      if (id) selectEvent(id);
    }));

    const observedTopics = [...new Set(state.events.filter(({ event }) => event.kind === "paper.submitted").flatMap(({ event }) => Array.isArray(event.payload?.topics) ? event.payload.topics.filter((topic): topic is string => typeof topic === "string") : []))];
    required<HTMLElement>("dossier-directions").innerHTML = observedTopics.length ? observedTopics.map((topic) => `<span>${escapeHtml(topic)}</span>`).join("") : "<p class=\"dossier-empty\">NOT OBSERVED — NO AUTHORED-PAPER TOPICS AT THIS CURSOR</p>";
    const activityKinds = ["paper", "review", "funding", "research", "reporting", "registration"] as const;
    required<HTMLElement>("dossier-activities").innerHTML = activityKinds.map((kind) => `<div><span>${kind.toUpperCase()}</span><strong>${state.events.filter((event) => event.activity_kind === kind).length}</strong></div>`).join("");

    const maximumBalance = Math.max(1, ...state.resource_points.map((point) => point.balance));
    required<HTMLElement>("dossier-resource-chart").innerHTML = state.resource_points.length ? state.resource_points.map((point) => `<i class="resource-bar" data-active="${point.active}" style="--bar-height:${Math.max(6, Math.round(point.balance / maximumBalance * 100))}%" title="${escapeHtml(point.category)} · balance ${point.balance} · authoritative frame ${point.frame_cursor}"><span>${point.balance}</span></i>`).join("") : "<p class=\"dossier-empty\">NO NUMERIC RESOURCE STATE OBSERVED</p>";

    const relationships = selected.relationships.filter((relationship) => relationship.logical_timestamp_ms <= cursorMs);
    const peers = [...new Set(relationships.map((relationship) => relationship.peer_id))].slice(0, 3);
    const map = required<HTMLElement>("dossier-relationship-map");
    map.innerHTML = `<button class="relation-center" type="button" title="Current researcher">${escapeHtml(selected.researcher_id)}</button>${peers.map((peer, index) => `<i class="relation-line" data-position="${index}" aria-hidden="true"></i><button class="relation-peer" type="button" data-peer-id="${escapeHtml(peer)}" data-position="${index}">${escapeHtml(peer)}</button>`).join("")}${peers.length ? "" : "<p class=\"dossier-empty\">NO ARTIFACT-MEDIATED PEER EVENT OBSERVED</p>"}`;
    map.querySelectorAll<HTMLButtonElement>("[data-peer-id]").forEach((button) => button.addEventListener("click", () => {
      const peer = button.dataset.peerId;
      const next = peer ? dossiers.get(peer) : undefined;
      if (next) {
        selected = next;
        render();
      }
    }));
    const evidence = required<HTMLElement>("dossier-relationship-evidence");
    evidence.innerHTML = relationships.length ? relationships.map((relationship) => `<button type="button" data-relationship-event="${escapeHtml(relationship.event_id)}"><span>${escapeHtml(relationship.evidence_label)} · ${escapeHtml(relationship.peer_id)}</span><code>${escapeHtml(relationship.artifact_id.replace("https://arxiv.org/abs/", "arXiv:"))}</code></button>`).join("") : "";
    evidence.querySelectorAll<HTMLButtonElement>("[data-relationship-event]").forEach((button) => button.addEventListener("click", () => {
      const id = button.dataset.relationshipEvent;
      if (id) selectEvent(id);
    }));
    required<HTMLUListElement>("dossier-missing").innerHTML = selected.missingness.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  };

  toggleButton.addEventListener("click", () => {
    setOpen(!open);
    render();
  });
  closeButton.addEventListener("click", () => {
    setOpen(false);
    toggleButton.focus();
  });
  graphButton.addEventListener("click", () => {
    const id = graphButton.dataset.graphId;
    if (id) window.dispatchEvent(new CustomEvent<{ id: string }>("noctiluca:graph-open", { detail: { id } }));
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && open) setOpen(false);
  });
  window.addEventListener("noctiluca:select", ((event: CustomEvent<SelectionDetail>) => {
    if (event.detail.category !== "entity") return;
    const dossier = dossiers.get(event.detail.id);
    if (!dossier) return;
    selected = dossier;
    setOpen(true);
    render();
  }) as EventListener);
  return {
    toggle: () => toggleButton.click(),
    setCursor(value: number): void {
      cursorMs = value;
      render();
    },
  };
}

function installCollaborationGraph(replay: ReplayV2): CollaborationGraphController {
  const panel = required<HTMLElement>("collaboration-graph");
  const toggleButton = required<HTMLButtonElement>("graph-toggle");
  const closeButton = required<HTMLButtonElement>("graph-close");
  if (!replay.metadata.empirical) {
    toggleButton.disabled = true;
    toggleButton.title = "Verified commit-pinned campaign replay required";
    return { setCursor: () => undefined, toggle: () => undefined };
  }
  const fullGraph = buildCollaborationEvidenceGraph(replay);
  const enabled = new Set<EvidenceEdgeKind>(EVIDENCE_EDGE_KINDS);
  const defaultNode = fullGraph.nodes.find((node) => node.id === "institution_0001_researcher_2") ?? fullGraph.nodes[0]!;
  const requestedFocus = new URLSearchParams(window.location.search).get("graph");
  let focusId = fullGraph.nodes.some((node) => node.id === requestedFocus) ? requestedFocus! : defaultNode.id;
  let cursorMs = 0;
  let open = Boolean(requestedFocus);
  const setOpen = (value: boolean): void => {
    open = value;
    panel.hidden = !value;
    toggleButton.setAttribute("aria-pressed", String(value));
    toggleButton.textContent = `EVIDENCE GRAPH: ${value ? "ON" : "OFF"}`;
  };
  setOpen(open);
  const openEvent = (eventId: string): void => {
    const event = replay.canonical.events.find((candidate) => candidate.id === eventId);
    if (!event) return;
    setOpen(false);
    window.dispatchEvent(new CustomEvent<number>("noctiluca:seek", { detail: event.logical_timestamp_ms }));
    window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: eventId, category: "event" } }));
  };
  const nodeForEntity = (id: string): EvidenceGraphNode | undefined => {
    const direct = fullGraph.nodes.find((node) => node.id === id);
    if (direct) return direct;
    const institution = replay.canonical.entities.institutions.find((candidate) => candidate.id === id);
    return institution ? fullGraph.nodes.find((node) => node.id === `institution:${institution.label}`) : undefined;
  };
  const render = (): void => {
    if (!open) return;
    const graph = graphAtCursor(fullGraph, cursorMs);
    const focus = graph.nodes.find((node) => node.id === focusId) ?? graph.nodes.find((node) => node.kind === "researcher") ?? graph.nodes[0];
    if (!focus) return;
    focusId = focus.id;
    required<HTMLElement>("graph-focus-label").textContent = `FOCUS ${focus.kind.toUpperCase()} · ${focus.label}`;
    required<HTMLElement>("graph-boundary").innerHTML = `<strong>CANONICAL EVIDENCE</strong> ${escapeHtml(fullGraph.disclosure.split(". ")[0] ?? fullGraph.disclosure)}. <em>PRESENTATION-ONLY</em> force layout, routes, motion, colour and narrative styling.`;
    required<HTMLElement>("graph-observations").innerHTML = fullGraph.observations.map((observation) => `<article class="graph-observation" data-status="${observation.status}" title="Loaded verified run · ${escapeHtml(observation.note)}"><span>RUN · ${observation.kind.toUpperCase()}</span><strong>${observation.count}</strong><small>${escapeHtml(observation.status.replaceAll("_", " "))}</small></article>`).join("");
    required<HTMLUListElement>("graph-missing").innerHTML = fullGraph.missingness.map((item) => `<li>${escapeHtml(item)}</li>`).join("");

    const incidentEdges = graph.edges.filter((edge) => enabled.has(edge.kind) && (edge.source_id === focus.id || edge.target_id === focus.id));
    const peerIds = [...new Set(incidentEdges.map((edge) => edge.source_id === focus.id ? edge.target_id : edge.source_id))].slice(0, 8);
    const slots = [{ x: 18, y: 20 }, { x: 50, y: 16 }, { x: 82, y: 20 }, { x: 86, y: 50 }, { x: 82, y: 80 }, { x: 50, y: 84 }, { x: 18, y: 80 }, { x: 14, y: 50 }];
    const positions = new Map<string, { x: number; y: number }>([[focus.id, { x: 50, y: 50 }]]);
    peerIds.forEach((id, index) => positions.set(id, slots[index]!));
    const visibleEdges = incidentEdges.filter((edge) => positions.has(edge.source_id) && positions.has(edge.target_id));
    const edgeMarkup = visibleEdges.map((edge) => {
      const peerId = edge.source_id === focus.id ? edge.target_id : edge.source_id;
      const peer = positions.get(peerId)!;
      const dx = peer.x - 50;
      const dy = peer.y - 50;
      const length = Math.sqrt(dx * dx + dy * dy);
      const angle = Math.atan2(dy, dx) * 180 / Math.PI;
      return `<i class="graph-edge-line" data-kind="${edge.kind}" style="--x:50%;--y:50%;--length:${length}%;--angle:${angle}deg" title="${escapeHtml(edge.kind)} · presentation-only route"></i>`;
    }).join("");
    const nodeIds = [focus.id, ...peerIds];
    const nodeMarkup = nodeIds.map((id) => graph.nodes.find((node) => node.id === id)).filter((node): node is EvidenceGraphNode => Boolean(node)).map((node) => {
      const position = positions.get(node.id)!;
      return `<button class="graph-node" type="button" data-graph-node="${escapeHtml(node.id)}" data-kind="${node.kind}" data-focus="${node.id === focus.id}" style="--x:${position.x}%;--y:${position.y}%"><strong>${escapeHtml(node.label)}</strong><small>${escapeHtml(node.kind.toUpperCase())} · ${escapeHtml(node.truth_status)}</small></button>`;
    }).join("");
    const canvas = required<HTMLElement>("graph-canvas");
    canvas.innerHTML = edgeMarkup + nodeMarkup;
    canvas.querySelectorAll<HTMLButtonElement>("[data-graph-node]").forEach((button) => button.addEventListener("click", () => {
      const id = button.dataset.graphNode;
      const node = id ? fullGraph.nodes.find((candidate) => candidate.id === id) : undefined;
      if (!node) return;
      if (node.kind === "researcher") {
        setOpen(false);
        window.dispatchEvent(new CustomEvent<SelectionDetail>("noctiluca:select", { detail: { id: node.id, category: "entity" } }));
      } else if (node.kind === "event") {
        const eventId = node.evidence_event_ids[0];
        if (eventId) openEvent(eventId);
      } else {
        focusId = node.id;
        render();
      }
    }));

    const evidenceList = required<HTMLElement>("graph-evidence-list");
    evidenceList.innerHTML = visibleEdges.length ? visibleEdges.map((edge) => `<button class="graph-evidence-edge" type="button" data-graph-event="${escapeHtml(edge.event_id)}"><strong>${escapeHtml(edge.source_id)} → ${escapeHtml(edge.target_id)}</strong><span>${edge.kind.toUpperCase()}</span><code>${escapeHtml(edge.event_kind)} · ${escapeHtml(edge.label)}</code></button>`).join("") : "<p class=\"dossier-empty\">NO ENABLED CANONICAL EDGE INCIDENT TO THIS NODE</p>";
    evidenceList.querySelectorAll<HTMLButtonElement>("[data-graph-event]").forEach((button) => button.addEventListener("click", () => {
      const id = button.dataset.graphEvent;
      if (id) openEvent(id);
    }));
    const connectedEventIds = new Set(visibleEdges.map((edge) => edge.event_id));
    const lineage = required<HTMLElement>("graph-lineage");
    lineage.innerHTML = graph.lineage.map((event) => `<button type="button" data-lineage-event="${escapeHtml(event.id)}" data-connected="${connectedEventIds.has(event.id)}" aria-label="Sequence ${event.sequence}: ${escapeHtml(event.kind)}"></button>`).join("");
    lineage.querySelectorAll<HTMLButtonElement>("[data-lineage-event]").forEach((button) => button.addEventListener("click", () => {
      const id = button.dataset.lineageEvent;
      if (id) openEvent(id);
    }));
  };

  const filters = required<HTMLElement>("graph-filters");
  filters.innerHTML = EVIDENCE_EDGE_KINDS.map((kind) => `<label><input type="checkbox" value="${kind}" checked />${kind.replaceAll("_", " ").toUpperCase()}</label>`).join("");
  filters.querySelectorAll<HTMLInputElement>("input").forEach((checkbox) => checkbox.addEventListener("change", () => {
    const kind = checkbox.value as EvidenceEdgeKind;
    if (checkbox.checked) enabled.add(kind);
    else enabled.delete(kind);
    render();
  }));
  toggleButton.addEventListener("click", () => {
    setOpen(!open);
    render();
  });
  closeButton.addEventListener("click", () => {
    setOpen(false);
    toggleButton.focus();
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && open) setOpen(false);
  });
  window.addEventListener("noctiluca:graph-open", ((event: CustomEvent<{ id: string }>) => {
    const node = nodeForEntity(event.detail.id);
    if (node) focusId = node.id;
    setOpen(true);
    render();
  }) as EventListener);
  window.addEventListener("noctiluca:select", ((event: CustomEvent<SelectionDetail>) => {
    if (event.detail.category !== "entity") return;
    const isResearcher = fullGraph.nodes.some((node) => node.kind === "researcher" && node.id === event.detail.id);
    if (isResearcher) return;
    const node = nodeForEntity(event.detail.id);
    if (!node || !["artifact", "institution"].includes(node.kind)) return;
    focusId = node.id;
    setOpen(true);
    render();
  }) as EventListener);
  return {
    toggle: () => toggleButton.click(),
    setCursor(value: number): void {
      cursorMs = value;
      render();
    },
  };
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
    if (category === "entity" && [...replay.canonical.entities.researchers, ...replay.canonical.entities.artifacts, ...replay.canonical.entities.institutions].some((entity) => entity.id === id)) {
      scene.select(id);
      return;
    }
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

function installControls(replay: ReplayV2, scene: ArcologyScene, evidenceQuay: EvidenceQuayController, institutionInteriors: InstitutionInteriorController, researcherDossier: ResearcherDossierController, collaborationGraph: CollaborationGraphController): void {
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
    evidenceQuay.setCursor(cursor);
    institutionInteriors.setCursor(cursor);
    researcherDossier.setCursor(cursor);
    collaborationGraph.setCursor(cursor);
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
    } else if (event.key.toLowerCase() === "q") {
      event.preventDefault();
      required<HTMLButtonElement>("quay-event").focus();
    } else if (event.key.toLowerCase() === "i") {
      event.preventDefault();
      institutionInteriors.toggle();
    } else if (event.key.toLowerCase() === "d") {
      event.preventDefault();
      researcherDossier.toggle();
    } else if (event.key.toLowerCase() === "g") {
      event.preventDefault();
      collaborationGraph.toggle();
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
      const evidenceQuay = installEvidenceQuay(replay);
      const institutionInteriors = installInstitutionInteriors(replay);
      const researcherDossier = installResearcherDossier(replay);
      const collaborationGraph = installCollaborationGraph(replay);
      installControls(replay, scene, evidenceQuay, institutionInteriors, researcherDossier, collaborationGraph);
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
