import { describe, expect, it } from "vitest";
import { NativeAsyncGuard, snapshotCompletedJob } from "../src/nativeAsyncGuard";

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
};

describe("native UI async request guards", () => {
  it("rejects a validation response after the edited request changes", async () => {
    const guard = new NativeAsyncGuard(), response = deferred<string>();
    const ticket = guard.validationTicket('{"loss":"old"}');
    const accepted = response.promise.then(() => guard.acceptsValidation(ticket, '{"loss":"new"}'));
    guard.changed();
    response.resolve("valid");
    expect(await accepted).toBe(false);
  });

  it("holds an exclusive submission lease until the original request finishes", async () => {
    const guard = new NativeAsyncGuard(), response = deferred<void>();
    expect(guard.beginSubmission()).toBe(true);
    expect(guard.beginSubmission()).toBe(false);
    const finished = response.promise.then(() => guard.finishSubmission());
    expect(guard.submissionInFlight()).toBe(true);
    response.resolve(); await finished;
    expect(guard.beginSubmission()).toBe(true);
  });

  it("rejects a delayed poll for a job that is no longer selected", async () => {
    const guard = new NativeAsyncGuard(), response = deferred<{ job_id: string }>();
    let currentJobId = "job-a";
    const accepted = response.promise.then(job => guard.acceptsPoll("job-a", currentJobId, job.job_id));
    currentJobId = "job-b";
    response.resolve({ job_id: "job-a" });
    expect(await accepted).toBe(false);
  });

  it("freezes completed metadata before evidence loading changes the selected job", async () => {
    const response = deferred<void>();
    let current: any = { job_id: "job-a", request_sha256: "sha-a", status: "complete", result: { native_loss: -3 }, seed: 7, years: 2, source_commit: "a".repeat(40) };
    const snapshot = snapshotCompletedJob(current, "job-a");
    const observed = response.promise.then(() => snapshot);
    current = { ...current, job_id: "job-b", request_sha256: "sha-b", result: { native_loss: 100 } };
    response.resolve();
    expect(await observed).toMatchObject({ job_id: "job-a", request_sha256: "sha-a", result: { native_loss: -3 } });
  });
});
