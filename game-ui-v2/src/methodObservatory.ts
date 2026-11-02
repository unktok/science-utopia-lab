import { verifyMethodExport, type MethodObservatory, type MethodArm, type MethodStep } from './methodObservatoryContract';
import './objectiveStructure.css';
import './methodObservatory.css';

const el = (id: string): HTMLElement => { const value = document.getElementById(id); if (!value) throw new Error(`Missing #${id}`); return value; };
const esc = (v: unknown): string => String(v ?? '—').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const n = (v: number, digits = 6): string => Number.isInteger(v) ? String(v) : v.toFixed(digits).replace(/0+$/, '').replace(/\.$/, '');
let data: MethodObservatory;
let selectedMethod = 0;
let selectedStep = 2;

function chart(kind: 'coordinate' | 'loss'): string {
  const width = 640, height = 265, left = 69, right = 25, top = 22, bottom = 48;
  const historical = data.methods[0]!.historical_incumbent;
  const all = data.methods.flatMap((method) => [method.initial, historical, ...method.steps]);
  const value = (p: { coordinates: number[]; actual_loss: number }) => kind === 'loss' ? p.actual_loss : p.coordinates[0]!;
  const low = kind === 'loss' ? Math.min(...all.map(value)) - .016 : .45;
  const high = kind === 'loss' ? Math.max(...all.map(value)) + .016 : .84;
  const maxSteps = Math.max(...data.methods.map((method) => method.steps.length));
  const x = (step: number) => left + (width - left - right) * step / maxSteps;
  const y = (v: number) => top + (height - top - bottom) * (high - v) / (high - low);
  const grid = Array.from({ length: 4 }, (_, i) => {
    const tick = low + (high - low) * i / 3;
    return `<path class="plot-grid" d="M${left} ${y(tick)}H${width - right}"/><text x="${left - 12}" y="${y(tick) + 4}" text-anchor="end">${n(tick, 3)}</text>`;
  }).join('');
  const baseline = `<path class="historical-line" d="M${left} ${y(value(historical))}H${width - right}"/><text class="historical-label" x="${width - right}" y="${y(value(historical)) - 8}" text-anchor="end">HISTORICAL ${kind === 'loss' ? 'BEST' : 'BEST θ'} ${n(value(historical), 4)}</text>`;
  const paths = data.methods.map((method, index) => {
    const points = [method.initial, ...method.steps];
    return `<g class="method-plot" data-method="${index}"><path d="${points.map((p, i) => `${i ? 'L' : 'M'}${x(i)} ${y(value(p))}`).join(' ')}"/>${points.map((p, i) => {
      const px = x(i), py = y(value(p));
      return index === 0 ? `<circle cx="${px}" cy="${py}" r="${selectedMethod === index && selectedStep + 1 === i ? 7 : 4}"/>` : `<path class="plot-diamond" d="M${px} ${py - 6}l6 6-6 6-6-6z"/>`;
    }).join('')}</g>`;
  }).join('');
  const ticks = Array.from({ length: maxSteps + 1 }, (_, i) => `<text x="${x(i)}" y="${height - 21}" text-anchor="middle">${i === 0 ? 'START' : `DRAW ${i}`}</text>`).join('');
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${kind === 'loss' ? 'Actual native loss' : 'Institution parameter'} paths, including the distinct shared historical incumbent">${grid}${baseline}${paths}${ticks}</svg>`;
}
function renderPaths(): void {
  el('coordinate-chart').innerHTML = chart('coordinate'); el('loss-chart').innerHTML = chart('loss');
  el('method-paths').innerHTML = data.methods.map((method, index) => `<article class="mo-method" data-method="${index}"><div class="mo-method-label"><span>0${index + 1} / ${esc(method.gradient_kind.toUpperCase())}</span><h3>${esc(method.label)}</h3><small>${esc(method.oracle)}</small><b>INCUMBENT θ ${n(method.final_incumbent.coordinates[0]!)} · L ${n(method.final_incumbent.actual_loss)}</b></div><div class="mo-stations">${method.steps.map((step, stepIndex) => `<button class="mo-station" data-method="${index}" data-step="${stepIndex}" aria-pressed="${selectedMethod === index && selectedStep === stepIndex}"><span>DRAW ${stepIndex + 1} · COMPLETED</span><strong>θ ${n(step.coordinates[0]!)}</strong><b>ACTUAL L ${n(step.actual_loss)}</b><small>${step.actual_loss === method.historical_incumbent.actual_loss ? 'TIES HISTORICAL BEST · NOT A NEW BEST' : 'ABOVE HISTORICAL BEST'}</small></button>`).join('')}</div></article>`).join('');
  for (const button of el('method-paths').querySelectorAll<HTMLButtonElement>('button')) button.addEventListener('click', () => { selectedMethod = Number(button.dataset.method); selectedStep = Number(button.dataset.step); renderPaths(); renderDetail(); });
}
function renderDetail(): void {
  const method: MethodArm = data.methods[selectedMethod]!;
  const step: MethodStep = method.steps[selectedStep]!;
  el('detail-title').textContent = `${method.label} / DRAW ${selectedStep + 1}`;
  el('detail-kind').textContent = `ACTUAL NATIVE ENDPOINT // ${step.id}`;
  const backward = step.backward;
  el('endpoint-detail').innerHTML = `<article class="actual-pane"><span>ORIGINAL WORLD · OBSERVED</span><h3>L = ${n(step.actual_loss)}</h3><p>Candidate θ = ${n(step.coordinates[0]!)}</p><dl>${Object.entries(step.measurements).map(([key, value]) => `<div><dt>${esc(key.replace('native.', ''))}</dt><dd>${n(value)}</dd></div>`).join('')}</dl><b>${step.fresh_replies} FRESH + ${step.replayed_replies} PREFIX REPLAYS · ${n(step.elapsed_seconds, 1)}s</b></article><article class="gradient-pane"><span>PROPOSAL SIGNAL · ${backward ? 'REPRESENTED, NOT NATIVE DERIVATIVE' : 'NO GRADIENT CONSUMED'}</span><h3>${backward ? `g = ${n(backward.gradient[0]!)}` : 'SCALAR LOSS ONLY'}</h3>${backward ? `<p>Computed BEFORE this draw at θ = ${n(backward.coordinates[0]!)}; temperature τ = ${n(backward.temperature)}.</p><p>Soft represented loss there: ${n(backward.represented_loss)}. This is not a prediction at the evaluated candidate.</p><small>${esc(backward.scope)}</small>` : '<p>The bisection arm proposes from its own scalar-loss history. It receives neither review-response traces nor represented backward values.</p>'}</article><article class="binding-pane"><span>EXACT ENDPOINT BINDING</span><dl><div><dt>SYSTEM FINGERPRINT</dt><dd>${esc(step.system_fingerprint)}</dd></div><div><dt>NATIVE COMPLETION RECEIPT</dt><dd>${esc(step.native_receipt_sha256)}</dd></div><div><dt>PORTABLE CHECKPOINT</dt><dd>${esc(step.checkpoint_sha256)}</dd></div></dl></article>`;
  el('raw-row').textContent = JSON.stringify(step, null, 2);
}
function render(): void {
  el('truth-badge').textContent = data.execution_kind === 'actual-native-qwen' ? 'AUDITED ACTUAL DEVELOPMENT' : 'LABELLED SCRIPTED FIXTURE'; el('truth-badge').dataset.mode = data.execution_kind === 'actual-native-qwen' ? 'actual' : 'fixture';
  el('campaign-summary').textContent = `${data.status.toUpperCase()} / ${data.methods.reduce((sum, method) => sum + method.steps.length, 0)} NATIVE DRAWS / NO ACTIVE JOBS`;
  const facts = [['OPTIMIZATION LOSS', data.objective.formula, 'fixed engineering proxy · not a science-quality law'], ['RESEARCHER WORLD', `${data.world.researchers} RESEARCHERS · ${data.world.years} YEARS`, `${data.world.model} · fixed weights · seed ${data.world.seed}`], ['FRESH BUDGET', `${data.methods[0]!.steps.length} WORLDS PER METHOD`, 'equal draw count · unequal oracle information'], ['OBSERVED OUTCOME', 'BOTH MOVE · NO NEW BEST', 'historical incumbent remains selected']];
  el('identity-strip').innerHTML = facts.map(([label, value, note]) => `<div><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
  const c = data.cost_accounting;
  const provenance = [['CAMPAIGN', data.campaign_id], ['EXPERIMENT SOURCE', data.source_binding.source_commit], ['SOURCE AUDIT FILE SHA256', data.source_binding.report_file_sha256], ['SOURCE AUDIT CONTENT SHA256', data.source_binding.report_content_sha256], ['FRESH MODEL REPLIES', `${c.new_fresh_physical_replies} total · ${data.methods.map((m) => `${m.cost.fresh_physical_replies} ${m.id}`).join(' / ')}`], ['ACTUAL SUPPORT INCLUDING HISTORY', `${c.total_unique_actual_calls_supporting_paths} unique replies = ${c.new_fresh_physical_replies} new + ${c.shared_historical_unique_actual_support} historical support`], ['NATIVE FORWARD TIME', `${n(c.native_world_elapsed_seconds, 2)} seconds · excludes implementation / analysis`], ['RAW INVENTORY', `${data.raw_binding.file_count} files · ${data.raw_binding.inventory_sha256}`]];
  el('provenance').innerHTML = provenance.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('');
  el('limitations').innerHTML = data.limitations.map((text) => `<p>${esc(text)}</p>`).join('');
  el('footer-source').textContent = `${data.source_binding.report_path} // SHA-256 VERIFIED EXPORT`;
  renderPaths(); renderDetail(); el('evidence').hidden = false;
}
async function boot(): Promise<void> {
  try {
    const [payload, receipt] = await Promise.all([fetch('./data/native-method-paths-v10-observatory.json'), fetch('./data/native-method-paths-v10-observatory.receipt.json')]);
    if (!payload.ok || !receipt.ok) throw new Error('Immutable campaign export is missing.');
    data = await verifyMethodExport(await payload.text(), await receipt.json()); render();
    if (new URLSearchParams(location.search).get('focus') === 'paths') document.body.dataset.focus = 'paths';
  } catch (error) { el('truth-badge').textContent = 'EVIDENCE UNAVAILABLE'; el('unavailable').hidden = false; el('unavailable-message').textContent = error instanceof Error ? error.message : String(error); }
}
void boot();
