import { sha256Text } from './methodObservatoryContract';
import { stableStringify } from './hash';
import { decodeSearchEvidence, verifySearchProgress } from './nativeSearchContract';
export const SEARCH_AUDIT_ORDER = ['throughput-blackbox', 'efficiency-blackbox', 'efficiency-nested-lr'] as const;
export interface VerifiedSearchAudit { audit: Record<string, any>; raw: string; file_sha256: string; source_commit: string; integer_paths: string[]; scripted: boolean }
export async function verifyNativeSearchAudit(raw: string, fileHash: string, source: string, allowScripted = false): Promise<VerifiedSearchAudit> {
  if (!/^[a-f0-9]{64}$/.test(fileHash) || !/^[a-f0-9]{40}$/.test(source) || await sha256Text(raw) !== fileHash) throw new Error('Exact audit file SHA256 and source commit required; bytes differ or identity malformed');
  const decoded = decodeSearchEvidence(raw), audit = decoded.value, scripted = audit?.classification === 'scripted-fixture-not-native-results';
  if (audit?.schema !== 'scienceutopia.native-autonomous-search-audit.v14' || audit.source_commit !== source || !/^[a-f0-9]{64}$/.test(audit.content_sha256)
    || !(audit.classification === 'actual-native-qwen-autonomous-search-development-v14' || allowScripted && scripted)
    || !['complete', 'budget-complete-with-failures'].includes(audit.status) || stableStringify(audit.run_order) !== stableStringify(SEARCH_AUDIT_ORDER)) throw new Error('Expected terminal source-bound autonomous audit with all three requests');
  const proof = audit.audit;
  if (proof?.new_model_calls !== 0 || proof.new_container_executions !== 0 || proof.campaign_and_lineage_replayed !== true || proof.checkpoint_loss_reextracted !== true
    || proof.all_failures_and_exact_ties_retained !== true || proof.designer_requests_raw_replies_and_operations_joined !== true || proof.scientist_and_designer_costs_separate !== true
    || !scripted && proof.replay_source_proofs?.status !== 'verified-exact-replay-source-blobs') throw new Error('Independent read-only raw/source/replay audit proofs missing');
  for (const [index, id] of SEARCH_AUDIT_ORDER.entries()) {
    const run = audit.runs?.[id], progress = verifySearchProgress(run?.runtime_progress);
    if (run.terminal !== true || !['complete', 'failed'].includes(progress.status) || progress.source_commit !== source || !Array.isArray(run.designer?.proofs)
      || run.method !== (index === 2 ? 'nested-lr' : 'blackbox') || progress.native_budget !== (index === 2 ? 4 : 2)
      || stableStringify(progress.request) !== stableStringify(run.request) || stableStringify(progress.records) !== stableStringify(run.records)
      || stableStringify(progress.pending) !== stableStringify(run.pending) || stableStringify(progress.immutable_plan) !== stableStringify(run.runtime_plan)
      || stableStringify(run.loss_spec) !== stableStringify(run.request.loss_spec)) throw new Error(`Audited runtime projection differs: ${id}`);
    for (const row of run.observations ?? []) if (row.status !== 'complete' && (row.loss !== null || row.own_loss !== null)) throw new Error('Failed audited endpoint has a fabricated numeric loss');
  }
  return { audit, raw, file_sha256: fileHash, source_commit: source, integer_paths: decoded.integer_paths, scripted };
}
export function auditedDesignerAttempts(run: Record<string, any>): { label: string; value: unknown; authored_source?: string }[] {
  return (run.designer?.proofs ?? []).flatMap((proof: any, generation: number) => (proof.attempts ?? []).map((attempt: any, index: number) => ({
    label: `GENERATION ${generation} / ATTEMPT ${attempt.attempt ?? index} / ${proof.attempt_records?.[index]?.status ?? 'INTERRUPTED / RESPONSE UNKNOWN'} / ${proof.generation_status}`,
    authored_source: (proof.attempt_records?.[index]?.model_reply?.output?.operations ?? []).filter((op: any) => typeof op.value === 'string' && typeof op.path === 'string' && op.path.endsWith('/source')).map((op: any) => `ORIGINAL AUTHORED VALUE / ${op.path}\n${op.value}`).join('\n\n'),
    value: { scope: 'Original authored output / raw assistant content. A failed or unparsed draft is not a valid candidate, execution or adoption.',
      generation_request_sha256: proof.request_sha256, attempt, dispatch_intent: proof.started_records?.[index] ?? null,
      attempt_record: proof.attempt_records?.[index] ?? null, factual_address_diagnostic: proof.operation_diagnostics?.[index] ?? null,
      authored_payload_comparison: proof.authored_payload_comparisons?.[index] ?? null,
      generation_result: proof.result, definition_consumed: proof.definition_consumed }
  })));
}
