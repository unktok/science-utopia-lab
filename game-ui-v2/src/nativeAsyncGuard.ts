export type ValidationTicket = Readonly<{ revision: number; body_json: string }>;

export type CompletedJobSnapshot = Readonly<{
  job_id: string;
  request_sha256: string;
  status: "complete";
  result: Readonly<{ native_loss: number }>;
  seed: number;
  years: number;
  source_commit: string;
}>;

const record = (value: unknown): value is Record<string, unknown> => Boolean(value) && typeof value === "object" && !Array.isArray(value);

// A deterministic, DOM-free guard for UI request lifetimes. It does not start work.
export class NativeAsyncGuard {
  private revision = 0;
  private submitting = false;

  changed(): void { this.revision += 1; }

  validationTicket(bodyJson: string): ValidationTicket {
    return Object.freeze({ revision: this.revision, body_json: bodyJson });
  }

  acceptsValidation(ticket: ValidationTicket, currentBodyJson: string): boolean {
    return ticket.revision === this.revision && ticket.body_json === currentBodyJson;
  }

  beginSubmission(): boolean {
    if (this.submitting) return false;
    this.submitting = true;
    return true;
  }

  finishSubmission(): void { this.submitting = false; }
  submissionInFlight(): boolean { return this.submitting; }

  acceptsPoll(expectedJobId: string, currentJobId: string, responseJobId: unknown): boolean {
    return Boolean(expectedJobId) && expectedJobId === currentJobId && expectedJobId === String(responseJobId);
  }
}

export function snapshotCompletedJob(value: unknown, expectedJobId: string): CompletedJobSnapshot {
  if (!record(value) || value.status !== "complete" || String(value.job_id) !== expectedJobId || !record(value.result)) throw new Error("Completed job metadata does not match the selected durable job");
  const nativeLoss = Number(value.result.native_loss), seed = Number(value.seed), years = Number(value.years);
  if (!Number.isFinite(nativeLoss) || !Number.isInteger(seed) || !Number.isInteger(years) || typeof value.request_sha256 !== "string" || !value.request_sha256 || typeof value.source_commit !== "string" || !value.source_commit) throw new Error("Completed job metadata is incomplete");
  return Object.freeze({
    job_id: expectedJobId,
    request_sha256: value.request_sha256,
    status: "complete",
    result: Object.freeze({ native_loss: nativeLoss }),
    seed,
    years,
    source_commit: value.source_commit,
  });
}
