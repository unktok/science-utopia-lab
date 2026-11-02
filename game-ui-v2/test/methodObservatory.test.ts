import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { parseMethodObservatory, verifyMethodExport } from '../src/methodObservatoryContract';

const root = new URL('../', import.meta.url);
const text = readFileSync(new URL('public/data/native-method-paths-v10-observatory.json', root), 'utf8');
const receipt = JSON.parse(readFileSync(new URL('public/data/native-method-paths-v10-observatory.receipt.json', root), 'utf8'));
const auditBytes = readFileSync(new URL('../research/results/native-method-paths-v10-a1.json', root));
const audit = JSON.parse(auditBytes.toString('utf8'));
const sha = (bytes: string | Buffer) => createHash('sha256').update(bytes).digest('hex');
const fresh = () => JSON.parse(text);

describe('immutable native method observatory', () => {
  it('binds payload bytes and original tracked audit bytes', async () => {
    const d = await verifyMethodExport(text, receipt);
    expect(d.source_binding.report_file_sha256).toBe(sha(auditBytes));
    expect(d.source_binding.report_content_sha256).toBe(audit.content_sha256);
    expect(d.source_binding.source_commit).toBe(audit.source_commit);
    expect(d.execution_kind).toBe('actual-native-qwen');
    expect(d.status).toBe('complete');
  });
  it('preserves every actual coordinate, loss, native receipt, cost and backward provenance', () => {
    const d = parseMethodObservatory(fresh());
    for (const method of d.methods) {
      expect(method.final_incumbent.actual_loss).toBe(audit.arms[method.id].final_incumbent.loss);
      expect(method.final_incumbent.coordinates).toEqual([.8]);
      expect(method.cost).toEqual(audit.cost_accounting.arms[method.id]);
      for (const step of method.steps) {
        const source = audit.endpoints.find((endpoint: any) => endpoint.name === step.id);
        expect(step.actual_loss).toBe(source.native_loss);
        expect(step.coordinates).toEqual([source.theta]);
        expect(step.native_receipt_sha256).toBe(source.completion_receipt_sha256);
        const operator = audit.operators.find((item: any) => item.name === step.id);
        expect(step.backward).toEqual(operator ? { ...operator.backward, operator_file_sha256: operator.file_sha256 } : null);
      }
    }
    expect(d.cost_accounting.new_fresh_physical_replies).toBe(186);
    expect(d.cost_accounting.total_unique_actual_calls_supporting_paths).toBe(332);
  });
  it('rejects changed payload and swapped source receipt', async () => {
    await expect(verifyMethodExport(`${text} `, receipt)).rejects.toThrow('export receipt');
    await expect(verifyMethodExport(text, { ...receipt, source_binding: { ...receipt.source_binding, source_commit: '0'.repeat(40) } })).rejects.toThrow('source mismatch');
  });
  it.each(['ongoing_jobs', 'viewing_starts_jobs', 'optimizer_superiority'])('rejects unsupported %s', (claim) => {
    const d = fresh(); d.claims[claim] = true;
    expect(() => parseMethodObservatory(d)).toThrow('unsupported');
  });
  it('rejects unlabeled fixture and fabricated actual attribution', () => {
    const d = fresh(); d.execution_kind = 'scripted-fixture';
    expect(() => parseMethodObservatory(d)).toThrow('fixture attribution');
    d.execution_kind = 'actual-native-qwen'; d.classification = 'scripted-fixture';
    expect(() => parseMethodObservatory(d)).toThrow('actual attribution');
  });
  it('rejects missing actual loss, unbound endpoints and blackbox gradient leakage', () => {
    const d = fresh(); d.methods[0].steps[0].actual_loss = null;
    expect(() => parseMethodObservatory(d)).toThrow('endpoint');
    const unbound = fresh(); unbound.methods[0].steps[0].native_receipt_sha256 = 'missing';
    expect(() => parseMethodObservatory(unbound)).toThrow('endpoint');
    const leaked = fresh(); leaked.methods[1].steps[0].backward = leaked.methods[0].steps[0].backward;
    expect(() => parseMethodObservatory(leaked)).toThrow('gradient leakage');
  });
  it('does not confuse represented pre-proposal loss with candidate native loss', () => {
    const d = parseMethodObservatory(fresh()); const step = d.methods[0]!.steps[0]!;
    expect(step.backward!.coordinates).toEqual([.5]);
    expect(step.coordinates).toEqual([.6]);
    expect(step.backward!.represented_loss).not.toBe(step.actual_loss);
    const ui = readFileSync(new URL('src/methodObservatory.ts', root), 'utf8');
    expect(ui).toContain('Computed BEFORE this draw');
    expect(ui).toContain('not a prediction at the evaluated candidate');
    expect(ui).not.toMatch(/method:\s*['"]POST|\/api\/|setInterval/);
  });
  it('keeps interface English and structurally linked without changing historical data', () => {
    const html = readFileSync(new URL('method-observatory.html', root), 'utf8');
    expect(html).toContain('<html lang="en">');
    expect(html).not.toMatch(/[\u3040-\u30ff\u3400-\u9fff]/u);
    expect(html).toContain('WORLD-WIDE DIFFERENTIABILITY IS NOT A REQUIREMENT');
    expect(html).toContain('not a mandatory completion gate');
    expect(html).toContain('SCHEMATIC ART / NOT LIVE SIMULATION STATE');
    expect(html).toContain('review-charter evidence weight');
    expect(readFileSync(new URL('objective-structure.html', root), 'utf8')).toContain('method-observatory.html');
  });
  it('binds reviewed screenshots and UI source to the passing browser receipt', () => {
    const prefix = 'screenshots/method-observatory-v10-qa/';
    const qa = JSON.parse(readFileSync(new URL(`${prefix}method-observatory-v10-browser-qa.json`, root), 'utf8'));
    expect(qa.payload_sha256).toBe(sha(text));
    for (const [file, expected] of Object.entries(qa.ui_source_sha256s)) expect(sha(readFileSync(new URL(file, root))), file).toBe(expected);
    for (const artifact of Object.values(qa.artifacts) as { file: string; sha256: string }[]) expect(sha(readFileSync(new URL(`${prefix}${artifact.file}`, root)))).toBe(artifact.sha256);
    expect(qa.browser_errors + qa.failed_http_responses + qa.non_get_requests + qa.external_requests).toBe(0);
    expect(qa.interactions).toHaveLength(2);
  });
});
