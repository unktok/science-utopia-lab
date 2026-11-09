import "./preScaleObservatory.css";
import { validatePreScale, valueLabel, statusLabel, type PreScaleSnapshot } from "./preScaleContract";

const app = document.querySelector<HTMLElement>("#app")!;
const el = <K extends keyof HTMLElementTagNameMap>(tag: K, text = "", cls = ""): HTMLElementTagNameMap[K] => {
  const n = document.createElement(tag); n.textContent = text; n.className = cls; return n;
};
const link = (label: string, href: string) => { const a = el("a", label); a.href = href; return a; };

function render(p: PreScaleSnapshot): void {
  app.replaceChildren();
  const rail = el("nav", "", "truth-rail"); rail.setAttribute("aria-label", "Evidence boundary and navigation");
  rail.append(link("← ARCOLOGY", "./hub.html"), el("span", "RECORDED SNAPSHOT · NOT A LIVE HEARTBEAT"), link("INSTITUTION FOUNDRY →", "./native.html"));
  const header = el("header"); const icon = el("img"); icon.src = "./assets/noctiluca/production/institution-lab.svg";
  icon.alt = "Research institution icon, presentation only";
  const titles = el("div"); titles.append(el("p", "NOCTILUCA / RESEARCH CONTROL", "eyebrow"), el("h1", "Before the scale jump"),
    el("p", "Free scientific institutions. Explicit objectives. Inspectable search."));
  header.append(icon, titles);
  const boundary = el("section", "", "boundary");
  boundary.append(el("strong", "Observed " + p.observed_utc), el("p", "Viewing this page starts no experiment. “Started” is not proof of a running process. A dash is unknown, never zero."),
    el("small", `${p.scientist_model} researchers / ${p.designer_model} designer · native world · no weight training`));
  const refresh = el("button", "RELOAD SNAPSHOT"); refresh.addEventListener("click", () => { void load(); }); boundary.append(refresh);
  app.append(rail, header, boundary);

  const completed = p.information.worlds.filter(r => r.status === "complete").length;
  const steps = el("section", "", "pipeline"); steps.setAttribute("aria-label", "Study pipeline and actual progress");
  for (const [letter, title, count, detail] of [
    ["D", "Submission", `${p.information.numeric_readiness.filter(r => r.status === "submitted").length}/2`, "Numeric readiness only. No scientific loss."],
    ["M", "Information paths", `${completed}/12`, "Four conditions · three development seeds · four years."],
    ["O", "Objective → system", `${p.search.candidate_slots.length}/16`, "T/E × numeric / code / graph / uniform × two generations."],
    ["E", "Selection fixed", `${p.search.evaluation_observations}/${p.search.evaluation_plan_worlds ?? "≤36"}`, p.search.selection_fixed ? "Frozen selection recorded. No evaluation feedback." : "Not yet frozen. Evaluation cannot select a new winner."],
  ]) {
    const card = el("article", "", "station"); card.append(el("b", letter, "station-code"), el("h2", title), el("strong", count, "counter"), el("p", detail)); steps.append(card);
  }
  app.append(steps);
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
  for (const r of p.search.candidate_slots) sidebar.append(el("p", `${r.arm} / G${r.generation}: ${statusLabel(r.status)} / ${valueLabel(r.loss)}`));
  sidebar.append(link("Earlier method evidence →", "./method-observatory.html")); grid.append(sidebar); app.append(grid);
  const footer = el("footer"); footer.append(el("p", "SOURCE BOUNDARY / Different source pins are different evidence scopes."), el("code", p.information.source_commit),
    el("p", "A source-specific readiness pass is not an optimizer win, autonomous institutional invention, full-world differentiation or scientific truth.")); app.append(footer);
}

async function load(): Promise<void> {
  try {
    const response = await fetch("./data/pre-scale-observatory.actual.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Evidence snapshot unavailable (${response.status})`);
    render(await validatePreScale(await response.json()));
  } catch (error) {
    app.replaceChildren(el("h1", "Evidence unavailable"), el("p", String(error)), el("p", "No outcomes, progress or running-process state are inferred."), link("← ARCOLOGY", "./hub.html"));
  }
}
void load();
