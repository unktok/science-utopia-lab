import {
  agentLocation,
  deriveSummary,
  eventDescription,
  eventLabel,
  frameAt,
  validateReplay,
} from "./model.js";

const $ = (selector) => document.querySelector(selector);
const elements = {
  status: $("#load-status"),
  title: $("#replay-title"),
  year: $("#year-value"),
  phase: $("#phase-value"),
  progress: $("#progress"),
  cursor: $("#cursor-label"),
  play: $("#play"),
  previous: $("#previous"),
  next: $("#next"),
  reset: $("#reset"),
  speed: $("#speed"),
  researchers: $("#stat-researchers"),
  resources: $("#stat-resources"),
  papers: $("#stat-papers"),
  accepted: $("#stat-accepted"),
  world: $("#agent-layer"),
  papersList: $("#papers-list"),
  eventTitle: $("#event-title"),
  eventDescription: $("#event-description"),
  eventMeta: $("#event-meta"),
  payload: $("#event-payload"),
  eventList: $("#event-list"),
};

let replayData;
let cursor = 0;
let timer = null;

function initials(id) {
  return id.split(/[-_]/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function stop() {
  if (timer) window.clearInterval(timer);
  timer = null;
  elements.play.textContent = "▶ Play";
  elements.play.setAttribute("aria-pressed", "false");
}

function start() {
  if (cursor >= replayData.events.length) cursor = 0;
  stop();
  elements.play.textContent = "❚❚ Pause";
  elements.play.setAttribute("aria-pressed", "true");
  timer = window.setInterval(() => {
    if (cursor >= replayData.events.length) return stop();
    cursor += 1;
    render();
  }, Number(elements.speed.value));
}

function togglePlay() {
  if (timer) stop();
  else start();
}

function setCursor(value) {
  cursor = Math.max(0, Math.min(Number(value), replayData.events.length));
  stop();
  render();
}

function renderAgents(state, event) {
  elements.world.replaceChildren();
  Object.entries(state.agents).forEach(([id, agent], index) => {
    const token = document.createElement("article");
    const location = agentLocation(event, id);
    token.className = `agent agent-${index % 4} at-${location}${agent.active ? "" : " inactive"}`;
    token.setAttribute("aria-label", `${id}, ${agent.balance ?? 0} credits, ${agent.active ? "active" : "inactive"}`);
    const person = document.createElement("span");
    person.className = "pixel-person";
    person.setAttribute("aria-hidden", "true");
    const badge = document.createElement("b");
    badge.textContent = initials(id);
    person.append(badge);
    const name = document.createElement("span");
    name.className = "agent-name";
    name.textContent = id;
    const resources = document.createElement("span");
    resources.className = "resource-chip";
    resources.textContent = `◆ ${agent.balance ?? "—"}`;
    token.append(person, name, resources);
    elements.world.append(token);
  });
}

function renderPapers(state) {
  elements.papersList.replaceChildren();
  const papers = Object.entries(state.artifacts);
  if (!papers.length) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = "No papers in the world yet.";
    elements.papersList.append(empty);
    return;
  }
  papers.forEach(([id, paper]) => {
    const item = document.createElement("li");
    item.className = "paper-card";
    const icon = document.createElement("span");
    icon.className = "paper-icon";
    icon.setAttribute("aria-hidden", "true");
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = paper.title ?? id;
    const meta = document.createElement("small");
    meta.textContent = `${id} · ${paper.reviews?.length ?? 0} review(s)`;
    copy.append(title, meta);
    const status = document.createElement("span");
    const statusKind = ["accept", "reject"].includes(paper.status) ? paper.status : "unknown";
    status.className = `paper-status status-${statusKind}`;
    status.textContent = paper.status ?? "draft";
    item.append(icon, copy, status);
    elements.papersList.append(item);
  });
}

function renderTimeline() {
  elements.eventList.replaceChildren();
  replayData.events.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `event-dot${index + 1 === cursor ? " current" : ""}${index + 1 < cursor ? " passed" : ""}`;
    button.setAttribute("aria-label", `Go to event ${index + 1}: ${eventLabel(item)}`);
    button.setAttribute("aria-current", index + 1 === cursor ? "step" : "false");
    button.title = `${index + 1}. ${eventLabel(item)}`;
    button.addEventListener("click", () => setCursor(index + 1));
    elements.eventList.append(button);
  });
}

function render() {
  const { frame, event } = frameAt(replayData, cursor);
  const state = frame.state;
  const summary = deriveSummary(state);
  elements.year.textContent = event?.year ?? state.year ?? 0;
  elements.phase.textContent = event?.phase ?? "—";
  elements.progress.value = cursor;
  elements.cursor.textContent = `${cursor} / ${replayData.events.length}`;
  elements.previous.disabled = cursor === 0;
  elements.next.disabled = cursor === replayData.events.length;
  elements.researchers.textContent = `${summary.activeResearchers}/${summary.researchers}`;
  elements.resources.textContent = summary.totalResources;
  elements.papers.textContent = summary.papers;
  elements.accepted.textContent = summary.accepted;
  elements.eventTitle.textContent = eventLabel(event);
  elements.eventDescription.textContent = eventDescription(event);
  elements.eventMeta.textContent = event ? `year ${event.year} · phase ${event.phase} · ${event.event_type}` : "cursor 0 · before the first event";
  elements.payload.textContent = event ? JSON.stringify(event.payload, null, 2) : "{}";
  renderAgents(state, event);
  renderPapers(state);
  renderTimeline();
}

async function loadReplay() {
  try {
    const response = await fetch("./data/one-year.replay.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    replayData = validateReplay(await response.json());
    elements.title.textContent = replayData.metadata.title ?? "ScienceUtopia replay";
    elements.status.textContent = `verified stream · ${replayData.stream_hash.slice(0, 10)}`;
    elements.progress.max = replayData.events.length;
    render();
  } catch (error) {
    elements.status.textContent = "replay unavailable";
    elements.status.classList.add("error");
    elements.eventTitle.textContent = "Could not load replay";
    elements.eventDescription.textContent = `${error.message}. Serve game-ui over local HTTP; see its README.`;
  }
}

elements.play.addEventListener("click", togglePlay);
elements.previous.addEventListener("click", () => setCursor(cursor - 1));
elements.next.addEventListener("click", () => setCursor(cursor + 1));
elements.reset.addEventListener("click", () => setCursor(0));
elements.speed.addEventListener("change", () => { if (timer) start(); });
elements.progress.addEventListener("input", (event) => setCursor(event.target.value));
document.addEventListener("keydown", (event) => {
  if (!replayData) return;
  if (["INPUT", "SELECT", "BUTTON"].includes(document.activeElement?.tagName)) return;
  if (event.code === "Space") { event.preventDefault(); togglePlay(); }
  if (event.code === "ArrowRight") setCursor(cursor + 1);
  if (event.code === "ArrowLeft") setCursor(cursor - 1);
  if (event.code === "Home") setCursor(0);
  if (event.code === "End") setCursor(replayData.events.length);
});

loadReplay();
