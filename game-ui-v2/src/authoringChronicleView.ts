import { AUTHOR_TOOLS, authorStepChanges, authorStepSource, decodeAuthorTrace, type AuthorGeneration, type AuthorStep } from './authoringChronicle';
import './authoringChronicle.css';

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls = '', text = ''): HTMLElementTagNameMap[K] => { const n = document.createElement(tag); n.className = cls; n.textContent = text; return n; };
const short = (hash: string | null | undefined) => hash ? hash.slice(0, 12) : 'UNAVAILABLE';
const pretty = (value: unknown) => JSON.stringify(value, null, 2) ?? 'Unavailable';
export function mountAuthoringChronicle(parent: Element): (value: unknown) => void {
  const section = el('section', 'author-chronicle'); section.id = 'author-chronicle'; section.setAttribute('aria-labelledby', 'author-title');
  const heading = el('header', 'author-heading'), title = el('div'); title.append(el('span', 'section-label', '15 / INSTITUTION FORGE'), el('h3', '', 'Inside the designer’s workshop')); title.querySelector('h3')!.id = 'author-title';
  const badge = el('span', 'author-scope', 'OBSERVED JOURNALS / READ ONLY'); heading.append(title, badge);
  const note = el('p', 'author-note', 'A draft is not a world. Follow recorded tools, rejected edits and repairs; native outcomes remain in the mission receipts below.');
  const rail = el('div', 'forge-tool-rail'); rail.setAttribute('aria-label', 'Tool vocabulary, not an inferred execution sequence');
  const pixels = ['01111000/11001100/10000100/10000100/11001100/01111000/00001100/00000110', '00000110/00001111/00011110/00111100/01111000/11110000/11100000/11000000', '11000011/01100110/00111100/00011000/00111100/01100110/11000011/00000000', '00100000/11111111/00100000/00001000/11111111/00001000/01000000/11111111', '00011000/00111100/01100110/11000011/10010101/11011011/01100110/00111100', '00011000/00111100/01111110/11011011/00011000/00011000/00011000/11111111'];
  for (const [i, tool] of AUTHOR_TOOLS.entries()) { const cell = el('div', 'author-tool'); cell.dataset.tool = tool; const icon = el('span', 'author-tool-icon'); icon.setAttribute('aria-hidden', 'true'); pixels[i]!.split('/').forEach((row, y) => [...row].forEach((bit, x) => { if (bit === '1') { const pixel = el('i'); pixel.style.left = `${x * 3}px`; pixel.style.top = `${y * 3}px`; icon.append(pixel); } })); cell.append(icon, el('small', '', tool.toUpperCase())); rail.append(cell); }
  const summary = el('p', 'author-summary'); summary.setAttribute('role', 'status');
  const body = el('div', 'author-layout'), list = el('ol', 'author-events'), inspector = el('article', 'author-inspector'); list.setAttribute('aria-label', 'Recorded tool dispatches');
  const focus = el('h4'), lineage = el('p', 'author-lineage'), chips = el('div', 'author-change-list'), errors = el('div', 'author-errors'), authored = el('div', 'author-literal-source'), raw = el('pre'), details = el('details'), disclosure = el('summary', '', 'EXACT TOOL INPUT / RESULT / DIAGNOSTICS'); details.append(disclosure, raw); inspector.append(focus, lineage, chips, errors, authored, details); body.append(list, inspector); section.append(heading, note, rail, summary, body); parent.append(section);
  let selected = '', steps: { key: string; generation: AuthorGeneration; item: AuthorStep }[] = [];
  const select = (key: string) => {
    const found = steps.find(x => x.key === key); if (!found) return; selected = key;
    for (const button of list.querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.key === key));
    const { item, generation } = found;
    focus.textContent = `${item.tool?.toUpperCase() ?? 'TOOL UNKNOWN'} / ${item.status.toUpperCase()} / STEP ${item.step}`;
    lineage.textContent = `DRAFT ${short(item.draft_before_sha256)} → ${short(item.draft_after_sha256)} / GENERATION ${short(generation.request_sha256)}`;
    chips.replaceChildren(...authorStepChanges(item).map(change => el('span', 'author-change', change)));
    if (!chips.childElementCount) chips.append(el('p', '', !item.completed ? 'Dispatch intent observed. No reply, tool or cost inferred.' : 'No literal edit operations supplied by this step.'));
    errors.replaceChildren(...item.errors.map(error => el('p', '', error)));
    if (!errors.childElementCount) errors.append(el('p', '', item.status === 'finished' ? 'Authoring finished. Native execution and loss still require separate receipts.' : 'No technical error recorded for this step.'));
    authored.replaceChildren(...authorStepSource(item).map(source => { const detail = el('details'), label = el('summary', '', item.tool === 'splice' ? 'LITERAL AUTHORED SPLICE FRAGMENT / NOT EXECUTION' : 'LITERAL REQUESTED SOURCE / NOT EXECUTION'), pre = el('pre', '', source); detail.append(label, pre); return detail; }));
    raw.textContent = pretty({ request_sha256: generation.request_sha256, definition_sha256: generation.definition_sha256 ?? null, ...item });
    for (const cell of rail.children) { const tool = (cell as HTMLElement).dataset.tool; cell.classList.toggle('selected', item.tool === tool); }
  };
  return value => {
    for (const cell of rail.children) cell.classList.remove('selected');
    let trace; try { trace = decodeAuthorTrace(value); } catch (error) { summary.textContent = String(error); summary.dataset.invalid = 'true'; body.hidden = true; return; }
    delete summary.dataset.invalid; body.hidden = !trace?.generations.some(g => g.steps.length);
    if (!trace) { summary.textContent = 'NO STAGED JOURNAL SUPPLIED / Older search records remain available below. No authoring activity inferred.'; return; }
    steps = trace.generations.flatMap(g => g.steps.map(item => ({ key: `${g.request_sha256}:${item.step}`, generation: g, item })));
    const finished = steps.filter(x => x.item.status === 'finished').length, rejected = steps.filter(x => x.item.status === 'rejected').length, unknown = steps.filter(x => !x.item.completed).length;
    summary.textContent = `${trace.generations.length} GENERATIONS / ${steps.length} DISPATCH RECEIPTS / ${rejected} REJECTED TOOLS / ${finished} FINISH RECEIPTS / ${unknown} PENDING OR UNKNOWN REPLIES${trace.warnings.length ? ` / WARNINGS: ${trace.warnings.join('; ')}` : ''}`;
    if (!steps.length) summary.textContent += ' / NO TOOL ACTIVITY OBSERVED';
    list.replaceChildren(...steps.map(({ key, item, generation }) => {
      const row = el('li'), button = el('button', `author-event author-${item.status}`); button.type = 'button'; button.dataset.key = key; button.setAttribute('aria-pressed', 'false');
      button.append(el('span', 'author-index', String(item.step).padStart(2, '0')), el('b', '', item.tool?.toUpperCase() ?? 'AWAITING REPLY'), el('span', 'author-outcome', item.status.toUpperCase()), el('small', '', `G ${short(generation.request_sha256)} / ${item.model_call_seconds === null ? 'COST UNKNOWN' : `${item.model_call_seconds.toFixed(2)}s ADAPTER`}`));
      button.addEventListener('click', () => select(key)); row.append(button); return row;
    }));
    if (steps.length) select(steps.some(x => x.key === selected) ? selected : steps.at(-1)!.key);
  };
}
