import { describe, expect, it } from "vitest";
import {
  activateMissionContract, activeMission, emptyMissionBook, linkMissionJob, missionMatchesDraft,
  missionProgress, observeMissionJob, parseMissionBook, type MissionDraft, type MissionObservation,
} from "../src/nativeMission";

const loss = (id = "loss-a", direction: "minimize" | "maximize" = "minimize") => ({ schema: "scienceutopia.loss-spec.v1", id, direction });
const draft = (target = 0, limit = 3, id = "loss-a", direction: "minimize" | "maximize" = "minimize"): MissionDraft => ({ loss_spec: loss(id, direction), target_loss: target, trial_limit: limit });
const complete = (job = "job-1", score = -4): MissionObservation => ({ job_id: job, request_sha256: `sha-${job}`, status: "complete", native_loss: score, seed: 1301, years: 2, source_commit: "a".repeat(40), evidence_loaded: true });

describe("sandbox mission contracts", () => {
  it("creates a fresh contract when loss, target or trial limit changes", () => {
    let book = activateMissionContract(emptyMissionBook(), draft(0, 3));
    const first = activeMission(book)!.contract.contract_id;
    expect(missionMatchesDraft(book, draft(0, 3))).toBe(true);
    book = activateMissionContract(book, draft(-2, 3));
    expect(activeMission(book)!.contract.contract_id).not.toBe(first);
    expect(book.contracts).toHaveLength(2);
    expect(book.contracts[0]!.contract.target_loss).toBe(0);
    book = activateMissionContract(book, draft(-2, 3, "loss-b"));
    expect(book.contracts).toHaveLength(3);
  });

  it("binds each durable job to one contract and enforces the trial cap", () => {
    let book = activateMissionContract(emptyMissionBook(), draft(0, 1));
    const contract_id = activeMission(book)!.contract.contract_id;
    const link = { job_id: "job-1", request_sha256: "sha-job-1", contract_id };
    book = linkMissionJob(book, link);
    expect(linkMissionJob(book, link).jobs).toHaveLength(1);
    expect(() => linkMissionJob(book, { job_id: "job-2", request_sha256: "sha-job-2", contract_id })).toThrow("trial limit");
    expect(() => linkMissionJob(book, { ...link, contract_id: "other" })).toThrow("different design contract");
  });

  it("records actual completed evidence once and never gives failures a score", () => {
    let book = activateMissionContract(emptyMissionBook(), draft(-3, 2));
    const contract_id = activeMission(book)!.contract.contract_id;
    book = linkMissionJob(book, { job_id: "job-1", request_sha256: "sha-job-1", contract_id });
    book = observeMissionJob(book, complete());
    book = observeMissionJob(book, complete());
    expect(activeMission(book)!.observations).toHaveLength(1);
    expect(missionProgress(book, contract_id)).toMatchObject({ attempted: 1, observed: 1, best_loss: -4, target_achieved: true });
    book = linkMissionJob(book, { job_id: "job-2", request_sha256: "sha-job-2", contract_id });
    book = observeMissionJob(book, { ...complete("job-2", 0), status: "failed", native_loss: null, evidence_loaded: false });
    expect(missionProgress(book, contract_id).complete_scores).toEqual([-4]);
    expect(() => observeMissionJob(book, { ...complete("job-2", 7), status: "failed", evidence_loaded: false })).toThrow("cannot carry");
  });

  it("refuses predicted or unlinked scores and supports maximize objectives", () => {
    let book = activateMissionContract(emptyMissionBook(), draft(8, 2, "gain", "maximize"));
    const contract_id = activeMission(book)!.contract.contract_id;
    book = linkMissionJob(book, { job_id: "job-1", request_sha256: "sha-job-1", contract_id });
    expect(() => observeMissionJob(book, { ...complete("job-1", 9), evidence_loaded: false })).toThrow("loaded evidence");
    expect(() => observeMissionJob(book, complete("unknown", 9))).toThrow("does not match");
    book = observeMissionJob(book, complete("job-1", 9));
    expect(missionProgress(book, contract_id).target_achieved).toBe(true);
  });

  it("fails closed on corrupt persisted identity collections", () => {
    let book = activateMissionContract(emptyMissionBook(), draft());
    expect(parseMissionBook(JSON.parse(JSON.stringify(book)))).toEqual(book);
    expect(() => parseMissionBook({ ...book, jobs: [{ job_id: "x", request_sha256: "y", contract_id: "missing" }] })).toThrow("invalid");
    const contract_id = activeMission(book)!.contract.contract_id;
    book = linkMissionJob(book, { job_id: "job-1", request_sha256: "sha-job-1", contract_id });
    const forged = JSON.parse(JSON.stringify(book)); forged.contracts[0].observations.push({ ...complete(), request_sha256: "wrong" });
    expect(() => parseMissionBook(forged)).toThrow("not linked");
  });
});
