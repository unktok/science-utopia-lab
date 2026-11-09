import "./preScaleObservatory.css";
import { validatePreScale, valueLabel, statusLabel, snapshotSource, type PreScaleSnapshot } from "./preScaleContract";

const app = document.querySelector<HTMLElement>("#app")!;
const el = <K extends keyof HTMLElementTagNameMap>(tag: K, text = "", cls = ""): HTMLElementTagNameMap[K] => {
  const n = document.createElement(tag); n.textContent = text; n.className = cls; return n;
};
const link = (label: string, href: string) => { const a = el("a", label); a.href = href; return a; };

function render(p: PreScaleSnapshot, source: "recorded" | "latest"): void {
  app.replaceChildren();
  const rail = el("nav", "", "truth-rail"); rail.setAttribute("aria-label", "Evidence boundary and navigation");
  rail.append(link("← ARCOLOGY", "./hub.html"), el("span", `${source === "latest" ? "LOCAL JOURNAL PROJECTION" : "RECORDED SNAPSHOT"} · NOT A LIVE HEARTBEAT`), link("INSTITUTION FOUNDRY →", "./native.html"));
  const header = el("header"); const icon = el("img"); icon.src = "./assets/noctiluca/production/institution-lab.svg";
  icon.alt = "Research institution icon, presentation only";
  const titles = el("div"); titles.append(el("p", "NOCTILUCA / RESEARCH CONTROL", "eyebrow"), el("h1", "Before the scale jump"),
    el("p", "Free scientific institutions. Explicit objectives. Inspectable search."));
  header.append(icon, titles);
  const boundary = el("section", "", "boundary");
  boundary.append(el("strong", "Observed " + p.observed_utc), el("p", "Viewing this page starts no experiment. “Started” is not proof of a running process. A dash is unknown, never zero."),
    el("small", `${p.scientist_model} researchers / ${p.designer_model} designer · native world · no weight training`));
  const refresh = el("button", "RELOAD SNAPSHOT"); refresh.addEventListener("click", () => { void load(); }); boundary.append(refresh);
  const choices = el("p"); choices.append(link("RECORDED FILE", "./pre-scale.html?source=recorded"), el("span", " / "),
    link("LOCAL UPDATES", "./pre-scale.html?source=latest"));
  boundary.append(choices, el("small", source === "latest" ? "Checks the local projection file every30 seconds. Its date changes only when recorded facts change. No fallback to older evidence." : "A committed historical snapshot. Local updates use a separate, explicitly selected file."));
  app.append(rail, header, boundary);

  const completed = p.information.worlds.filter(r => r.status === "complete").length;
  const steps = el("section", "", "pipeline"); steps.setAttribute("aria-label", "Study pipeline and actual progress");
  for (const [letter, title, count, detail] of [
    ["D", "Submission", `${p.information.numeric_readiness.filter(r => r.status === "submitted").length}/2`, "Numeric readiness only. No scientific loss."],
    ["M", "Information paths", `${completed}/12`, "Four conditions · three development seeds · four years."],
    ["O", "Objective → system", `${p.search.candidate_slots.length}/16`, "Terminal slots · T/E × numeric / code / graph / uniform × two generations."],
    ["E", "Selection fixed", `${p.search.evaluation_observations}/${p.search.evaluation_plan_worlds ?? "≤36"}`, p.search.selection_fixed ? "Frozen selection recorded. No evaluation feedback." : "Not yet frozen. Evaluation cannot select a new winner."],
  ]) {
    const card = el("article", "", "station"); card.append(el("b", letter, "station-code"), el("h2", title), el("strong", count, "counter"), el("p", detail)); steps.append(card);
  }
  app.append(steps);
  const refs = p.search.reference_worlds;
  if (refs) {
    const references = el("section", "", "panel reference-progress");
    references.append(el("p", "O / FRESH BASELINE FORWARDS", "eyebrow"),
      el("h2", "Fresh reference worlds"),
      el("p", `${refs.filter(r => r.status === "complete").length}/6 complete · four years · development seed41001. These precede the16 proposal slots; they are not generated candidates or unused-seed evaluations.`));
    const cards = el("div", "", "reference-worlds");
    for (const r of refs) {
      const card = el("article"); card.dataset.referenceId = r.id; card.dataset.status = r.status;
      card.append(el("h3", r.id), el("p", statusLabel(r.status)),
        el("small", `T ${valueLabel(r.scores?.throughput)} · E ${valueLabel(r.scores?.efficiency)} · C ${valueLabel(r.scores?.selective)}`));
      cards.append(card);
    }
    references.append(cards); app.append(references);
  }
  const grid = el("div", "", "evidence-grid");
  const mechanisms = el("section", "", "panel"); mechanisms.append(el("p", "M / ACTUAL WORLD RECORDS", "eyebrow"), el("h2", "The information switchyard"));
  const routes = el("div", "", "routes");
  for (const [id, title, route] of [["M0", "Disconnected", "History office ─╳─ researcher"], ["M1", "Own history", "Own records ───▶ next research choice"], ["M2", "Society history", "Society records ─▶ next research choice"], ["M3", "Delayed own history", "Own records ─[+1 year]─▶ researcher"]]) {
    const card = el("article"); card.append(el("b", id), el("h3", title), el("pre", route)); routes.append(card);
  }
  mechanisms.append(routes, el("p", "Same producer; explicit delivery interventions. Handwritten controls, not invented systems. Arrival does not prove causal benefit.", "note"));
  const table = el("table"); table.append(el("caption", "All twelve declared mechanism slots. T, E and C are proxy losses; lower is better, not necessarily better science."));
  const head = el("tr"); for (const title of ["Condition / seed", "Recorded status", "T", "E", "C"]) head.append(el("th", title)); const thead = el("thead"); thead.append(head); table.append(thead);
  const body = el("tbody");
  for (const r of p.information.worlds) {
    const row = el("tr"); row.dataset.status = r.status;
    row.append(el("th", `${r.condition} / ${r.seed}`), el("td", statusLabel(r.status)),
      el("td", valueLabel(r.scores?.throughput)), el("td", valueLabel(r.scores?.efficiency)), el("td", valueLabel(r.scores?.selective))); body.append(row);
  }
  table.append(body); const scroll = el("div", "", "table-scroll"); scroll.append(table); mechanisms.append(scroll); grid.append(mechanisms);
  const sidebar = el("aside", "", "panel"); sidebar.append(el("p", "D / READINESS IS NOT SEARCH", "eyebrow"), el("h2", "Submission receipts"));
  for (const r of p.information.numeric_readiness) {
    const card = el("article", "", "receipt"); card.append(el("h3", r.objective), el("p", statusLabel(r.status)),
      el("p", r.retained_parent_explicitly ? "All parent values explicitly retained." : "Changed literal coordinates submitted."),
      el("small", "Scientific loss: unavailable. No world was evaluated."));
    const details = el("details"); details.append(el("summary", "Terminal content identity"), el("code", r.result_sha256)); card.append(details); sidebar.append(card);
  }
  sidebar.append(el("h2", "Search and evaluation"), el("p", statusLabel(p.search.status)), el("p", "Every complete/null proposal and exact tie is retained. An initial-system selection is not an invention."));
  if (p.search.readiness) {
    sidebar.append(el("h3", "New search source readiness"));
    for (const [key, label] of [["numeric", "Numeric submissions"], ["editor", "Staged controls"]] as const) {
      const r = p.search.readiness[key];
      sidebar.append(el("p", r ? `${label}: ${r.accepted}/${r.total} accepted · ${r.passed ? "certificate passed" : "certificate did not pass"}` : `${label}: no certificate recorded.`));
    }
    sidebar.append(el("small", "Technical interface checks only. Directed controls are not scientific outcomes or free-design competence."));
  }
  if (p.search.observed_stage) sidebar.append(el("p", `Recorded stage: ${p.search.observed_stage}`));
  if (p.search.stage_error_type) sidebar.append(el("p", `Terminal error class: ${p.search.stage_error_type}. See journals for diagnosis.`));
  for (const r of p.search.candidate_slots) sidebar.append(el("p", `${r.arm} / G${r.generation}: ${statusLabel(r.status)} / ${valueLabel(r.loss)}`));
  sidebar.append(link("Earlier method evidence →", "./method-observatory.html")); grid.append(sidebar); app.append(grid);
  const footer = el("footer"); footer.append(el("p", "SOURCE BOUNDARY / Different source pins are different evidence scopes."), el("p", "Information study and the submission receipts above:"), el("code", p.information.source_commit));
  if (p.search.source_commit) footer.append(el("p", "Search/evaluation, with its own fresh readiness:"), el("code", p.search.source_commit));
  footer.append(el("p", "A source-specific readiness pass is not an optimizer win, autonomous institutional invention, full-world differentiation or scientific truth.")); app.append(footer);
}

let busy = false, renderedHash: string | null = null;
async function load(): Promise<void> {
  if (busy) return;
  busy = true;
  try {
    const source = snapshotSource(location.search);
    const file = source === "latest" ? "latest" : "actual";
    const response = await fetch(`./data/pre-scale-observatory.${file}.json`, { cache: "no-store", signal: AbortSignal.timeout(10_000) });
    if (!response.ok) throw new Error(`Evidence snapshot unavailable (${response.status})`);
    const envelope = await response.json(); const p = await validatePreScale(envelope);
    if (renderedHash !== envelope.web_sha256) { render(p, source); renderedHash = envelope.web_sha256; }
  } catch (error) {
    renderedHash = null;
    app.replaceChildren(el("h1", "Evidence unavailable"), el("p", String(error)), el("p", "No outcomes, progress or running-process state are inferred."), link("Choose the recorded historical file →", "./pre-scale.html?source=recorded"), link("← ARCOLOGY", "./hub.html"));
  } finally {
    busy = false;
  }
}
void load();
if (new URLSearchParams(location.search).get("source") === "latest") window.setInterval(() => { void load(); }, 30_000);
