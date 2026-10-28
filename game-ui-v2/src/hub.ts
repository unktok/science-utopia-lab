import { ARCOLOGY_MODES, installArcologyRail, navigateWithTransition, rememberedMode, type ArcologyModeId } from "./arcologyNav";
import "./style.css";
import "./hub.css";

const escapeHtml = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const required = <T extends HTMLElement>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing #${id}`);
  return element as T;
};

installArcologyRail("hub");

const queryFocus = new URLSearchParams(location.search).get("focus");
const initialId = ARCOLOGY_MODES.some((mode) => mode.id === queryFocus) ? queryFocus as ArcologyModeId : rememberedMode();
let selected = Math.max(0, ARCOLOGY_MODES.findIndex((mode) => mode.id === initialId));
if (selected < 0) selected = 0;

function render(): void {
  required("terminal-grid").innerHTML = ARCOLOGY_MODES.map((mode, index) => `
    <a class="district-terminal" href="${mode.href}" data-mode="${mode.id}" data-selected="${index === selected}" data-truth="${mode.truthClass}" aria-label="Open ${escapeHtml(mode.title)} — ${mode.truth}">
      <span class="district-number">0${index + 1}</span>
      <span class="district-sign"><small>${escapeHtml(mode.district)}</small><b>${escapeHtml(mode.title)}</b></span>
      <span class="district-art" aria-hidden="true"><img src="${mode.asset}" alt=""/><i></i><i></i><i></i></span>
      <span class="district-truth">${mode.truth}</span>
      <span class="district-copy">${escapeHtml(mode.description)}</span>
      <span class="district-door"><i aria-hidden="true"></i><b>ENTER GATE</b><kbd>${mode.key}</kbd></span>
    </a>`).join("");
  document.querySelectorAll<HTMLAnchorElement>(".district-terminal").forEach((link, index) => {
    link.addEventListener("focus", () => { selected = index; syncSelection(); });
    link.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const mode = ARCOLOGY_MODES[index]!;
      navigateWithTransition(mode.href, `${mode.district} // ${mode.truth}`);
    });
  });
  syncSelection();
}

function syncSelection(): void {
  document.querySelectorAll<HTMLElement>(".district-terminal").forEach((element, index) => { element.dataset.selected = String(index === selected); });
}

const motion = required<HTMLButtonElement>("motion-choice");
const reducedBySystem = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (reducedBySystem) {
  required("hub-app").dataset.motion = "reduced";
  motion.setAttribute("aria-pressed", "true");
  motion.textContent = "TRANSIT MOTION REDUCED";
}
motion.addEventListener("click", () => {
  const reduced = required("hub-app").dataset.motion !== "reduced";
  required("hub-app").dataset.motion = reduced ? "reduced" : "full";
  motion.setAttribute("aria-pressed", String(reduced));
  motion.textContent = reduced ? "TRANSIT MOTION REDUCED" : "REDUCE TRANSIT MOTION";
});

window.addEventListener("keydown", (event) => {
  if (event.altKey || event.metaKey || event.ctrlKey || event.target instanceof HTMLButtonElement || event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) return;
  if (event.key === "ArrowRight") { event.preventDefault(); selected = (selected + 1) % ARCOLOGY_MODES.length; syncSelection(); document.querySelectorAll<HTMLAnchorElement>(".district-terminal")[selected]?.focus(); }
  if (event.key === "ArrowLeft") { event.preventDefault(); selected = (selected - 1 + ARCOLOGY_MODES.length) % ARCOLOGY_MODES.length; syncSelection(); document.querySelectorAll<HTMLAnchorElement>(".district-terminal")[selected]?.focus(); }
  if (event.key === "Enter" && !(event.target instanceof HTMLAnchorElement)) { const mode = ARCOLOGY_MODES[selected]!; navigateWithTransition(mode.href, `${mode.district} // ${mode.truth}`); }
});

render();
