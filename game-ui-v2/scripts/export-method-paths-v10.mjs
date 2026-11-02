import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ui = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(ui, '..');
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const sourcePath = 'research/results/native-method-paths-v10-a1.json';
const bytes = await readFile(resolve(root, sourcePath));
const audit = JSON.parse(bytes);
if (audit.schema !== 'scienceutopia.native-method-paths-audit.v10' || audit.status !== 'complete'
  || audit.classification !== 'actual-native-qwen-method-paths-development-v10'
  || audit.technical_validity.completed_worlds !== 6) throw new Error('Expected completed actual v10 audit');
const source_binding = { report_path: sourcePath, report_file_sha256: sha(bytes), report_content_sha256: audit.content_sha256, source_commit: audit.source_commit };
const methods = ['gradient', 'blackbox'].map((id) => {
  const arm = audit.arms[id];
  return {
    id, label: id === 'gradient' ? 'RESPONSE-AWARE GRADIENT' : 'BLACK-BOX BISECTION',
    gradient_kind: id === 'gradient' ? 'represented-pathwise' : 'none',
    oracle: audit.comparison[`${id}_oracle`], initial: { coordinates: [0.5], actual_loss: 0.9 },
    historical_incumbent: { ...arm.final_incumbent, coordinates: [arm.final_incumbent.theta], actual_loss: arm.final_incumbent.loss },
    final_incumbent: { ...arm.final_incumbent, coordinates: [arm.final_incumbent.theta], actual_loss: arm.final_incumbent.loss },
    cost: audit.cost_accounting.arms[id],
    steps: arm.current_path.map((point, step) => {
      const endpoint = audit.endpoints.find((item) => item.name === point.name);
      const operator = audit.operators.find((item) => item.name === point.name);
      if (!endpoint || endpoint.native_loss !== point.loss || endpoint.theta !== point.theta) throw new Error('Audit endpoint join differs');
      return { id: point.name, step, coordinates: [point.theta], actual_loss: point.loss,
        hard_represented_loss: endpoint.hard_represented_loss,
        backward: operator ? { ...operator.backward, operator_file_sha256: operator.file_sha256 } : null,
        native_receipt_sha256: endpoint.completion_receipt_sha256, checkpoint_sha256: endpoint.checkpoint_sha256,
        system_fingerprint: endpoint.system_fingerprint, measurements: endpoint.objective_measurements,
        fresh_replies: endpoint.fresh_physical_reply_count, replayed_replies: endpoint.replayed_response_count,
        elapsed_seconds: endpoint.elapsed_seconds,
      };
    }),
  };
});
const data = {
  schema: 'scienceutopia.method-observatory.v1', campaign_id: 'native-method-paths-v10-a1',
  classification: audit.classification, status: 'complete', execution_kind: 'actual-native-qwen',
  source_binding, objective: { id: audit.objective.loss_spec.id, formula: 'L = 3.25A − Q + 0.05R', direction: 'minimize' },
  coordinate_labels: ['Review-charter evidence weight'],
  world: { model: 'Qwen3:8B', seed: 42, researchers: 5, years: 2, corpus_years: 4, weights: 'fixed' },
  methods, cost_accounting: audit.cost_accounting, comparison: audit.comparison,
  claims: { ...audit.claims, ongoing_jobs: false, viewing_starts_jobs: false },
  raw_binding: { file_count: audit.raw_hashes.file_count, inventory_sha256: audit.raw_hashes.inventory_sha256 },
  limitations: ['One scalar institutional parameter, not free structural invention.', 'Single common-prefix-coupled development path; no held-out replication.', 'Equal fresh-world budgets, unequal oracle information.', 'Represented response gradients are not verified derivatives of the native world.', 'Neither method discovers a new best beyond the shared historical incumbent.'],
};
await mkdir(resolve(ui, 'public/data'), { recursive: true });
const output = `${JSON.stringify(data, null, 2)}\n`;
const receipt = { schema: 'scienceutopia.method-observatory-export.v1', payload_file: 'native-method-paths-v10-observatory.json', payload_sha256: sha(output), source_binding, no_inference: true, no_job_dispatch: true };
await writeFile(resolve(ui, 'public/data', receipt.payload_file), output);
await writeFile(resolve(ui, 'public/data/native-method-paths-v10-observatory.receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`);
console.log(JSON.stringify(receipt));
