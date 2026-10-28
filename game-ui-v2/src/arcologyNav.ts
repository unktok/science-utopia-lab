import "./arcologyNav.css";

export type ArcologyModeId = "replay" | "sandbox" | "mission";
export type ArcologyLocation = ArcologyModeId | "hub";

export interface ArcologyMode {
  id: ArcologyModeId;
  key: string;
  district: string;
  title: string;
  truth: "VERIFIED REPLAY" | "SYNTHETIC SANDBOX" | "VERIFIED SNAPSHOT";
  truthClass: "verified" | "synthetic" | "snapshot";
  href: string;
  description: string;
  asset: string;
}

export const ARCOLOGY_MODES: readonly ArcologyMode[] = [
  {
    id: "replay", key: "R", district: "EVIDENCE QUAY", title: "Research city",
    truth: "VERIFIED REPLAY", truthClass: "verified",
    href: "./index.html?replay=campaign&motion=reduced",
    description: "Walk a completed, commit-pinned campaign through canonical events and authoritative projections.",
    asset: "/assets/noctiluca/production/institution-lab.svg",
  },
  {
    id: "sandbox", key: "S", district: "SYSTEM FOUNDRY", title: "Design console",
    truth: "SYNTHETIC SANDBOX", truthClass: "synthetic", href: "./sandbox.html",
    description: "Compose a structural SystemSpec. Validity is technical; no simulation or outcome exists here.",
    asset: "/assets/noctiluca/production/system-government.svg",
  },
  {
    id: "mission", key: "M", district: "ORBITAL CONTROL", title: "Optimization ops",
    truth: "VERIFIED SNAPSHOT", truthClass: "snapshot", href: "./mission.html",
    description: "Read timestamped orchestration progress without objective values, provisional winners, or held-out evidence.",
    asset: "/assets/noctiluca/production/institution-funding.svg",
  },
] as const;

export const HUB_HREF = "./hub.html";
const PRESENTATION_KEY = "noctiluca.presentation.lastMode";

export function currentBoundary(location: ArcologyLocation, search = ""): { label: string; truthClass: string } {
  if (location === "hub") return { label: "PRESENTATION-ONLY TRANSIT", truthClass: "transit" };
  if (location === "replay" && new URLSearchParams(search).get("replay") === "synthetic") return { label: "SYNTHETIC REPLAY", truthClass: "synthetic" };
  if (location === "mission" && new URLSearchParams(search).get("source") === "synthetic") return { label: "SYNTHETIC UI FIXTURE", truthClass: "synthetic" };
  const mode = ARCOLOGY_MODES.find((item) => item.id === location);
  if (!mode) throw new Error(`Unknown arcology location ${location}`);
  return { label: mode.truth, truthClass: mode.truthClass };
}

function remember(mode: ArcologyModeId): void {
  try { sessionStorage.setItem(PRESENTATION_KEY, mode); } catch { /* presentation state is optional */ }
}

export function rememberedMode(): ArcologyModeId | null {
  try {
    const value = sessionStorage.getItem(PRESENTATION_KEY);
    return ARCOLOGY_MODES.some((mode) => mode.id === value) ? value as ArcologyModeId : null;
  } catch { return null; }
}

export function navigateWithTransition(href: string, label: string): void {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches || Boolean(document.querySelector('[data-motion="reduced"]'));
  const destination = ARCOLOGY_MODES.find((mode) => mode.href === href);
  if (destination) remember(destination.id);
  if (reduced) { location.href = href; return; }
  const overlay = document.createElement("div");
  overlay.className = "arcology-transition";
  overlay.innerHTML = `<span>ARCOLOGY TRANSIT</span><strong>${label.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</strong><i aria-hidden="true"></i>`;
  overlay.setAttribute("role", "status");
  document.body.append(overlay);
  requestAnimationFrame(() => overlay.dataset.open = "true");
  window.setTimeout(() => { location.href = href; }, 360);
}

export function installArcologyRail(active: ArcologyLocation): void {
  const boundary = currentBoundary(active, location.search);
  const nav = document.createElement("nav");
  nav.className = "arcology-rail";
  nav.setAttribute("aria-label", "NOCTILUCA arcology modes and truth boundaries");
  nav.innerHTML = `<a class="arcology-rail__hub" href="${HUB_HREF}" data-arcology-destination="hub"><b>⌂</b><span>ARCOLOGY MAP</span></a>
    <span class="arcology-rail__boundary" data-truth="${boundary.truthClass}">YOU ARE IN // ${boundary.label}</span>
    <div class="arcology-rail__modes">${ARCOLOGY_MODES.map((mode) => `<a href="${mode.href}" data-arcology-destination="${mode.id}" data-active="${active === mode.id}" data-truth="${mode.truthClass}"><kbd>${mode.key}</kbd><span>${mode.truth}</span></a>`).join("")}</div>`;
  document.body.prepend(nav);
  nav.querySelectorAll<HTMLAnchorElement>("a").forEach((link) => link.addEventListener("click", (event) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigateWithTransition(link.getAttribute("href")!, link.textContent?.trim() || "ARCOLOGY TRANSIT");
  }));
  window.addEventListener("keydown", (event) => {
    if (!event.altKey || event.metaKey || event.ctrlKey) return;
    const key = event.key.toLowerCase();
    if (key === "h") { event.preventDefault(); navigateWithTransition(HUB_HREF, "ARCOLOGY MAP"); }
    const mode = ARCOLOGY_MODES.find((item) => item.key.toLowerCase() === key);
    if (mode) { event.preventDefault(); navigateWithTransition(mode.href, mode.truth); }
  });
}
