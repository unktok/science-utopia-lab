"""Fail-closed compact publication of the generated-Python integration slice."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from utopia.system import SystemSpec, validate_system_spec
from utopia.system.code_mechanisms import sha, validate_code_artifact
from utopia.replay.events import EventEnvelope


def verify_run(report):
    if report.get("schema") != "scienceutopia.generated-code-lab.v1" or report["dirty_development"]:
        raise ValueError("publication requires the clean recorded code lab schema")
    if len(report["proposals"]) != 3 or len(report["rounds"]) != 2:
        raise ValueError("expected initial source and two objective-conditioned revisions")
    for proposal in report["proposals"]:
        artifact = proposal["artifact"]
        validate_code_artifact(artifact)
        attempts = proposal["attempts"]
        if not attempts or attempts[-1]["status"] != "complete":
            raise ValueError("missing successful generated source receipt")
        for attempt in attempts:
            receipt = attempt["receipt"]
            if (receipt["request_sha256"] != sha(attempt["request"])
                    or receipt["response_sha256"] != sha(attempt["response"])):
                raise ValueError("model request/response hash mismatch")
            history = json.loads(attempt["request"]["messages"][0]["content"].rsplit(
                "PREVIOUS ACTUAL OBSERVATIONS:\n", 1)[1])
            if receipt["history_sha256"] != sha(history):
                raise ValueError("result-conditioned history receipt mismatch")
        if proposal["receipt"] != attempts[-1]["receipt"]:
            raise ValueError("selected model receipt mismatch")
        content = attempts[-1]["response"]["message"]["content"].strip()
        if content.startswith("```json\n") and content.endswith("```"):
            content = content[8:-3].strip()
        generated = json.loads(content)
        if (generated["source"] != artifact["source"] or generated["label"] != artifact["label"]
                or generated["state_schema"] != artifact["state_schema"]
                or generated["rationale"] != proposal["rationale"]
                or any(artifact["outputs"].get(port) != schema for port, schema in generated["new_port_schemas"].items())):
            raise ValueError("executed artifact differs from actual model response")
        run = proposal["evidence"]
        spec = SystemSpec.from_dict(run["system"])
        validate_system_spec(spec)
        if spec.fingerprint != run["system_fingerprint"] or run["checkpoint"]["system_fingerprint"] != spec.fingerprint:
            raise ValueError("system/checkpoint fingerprint mismatch")
        node = next(n for n in spec.mechanisms if n.mechanism_id == "invented-institution")
        if node.parameters["code_artifact"] != artifact or node.parameters["runtime_image_id"] != report["image_id"]:
            raise ValueError("executed SystemSpec differs from code/image artifact")
        if sha(run["events"]) != run["event_stream_hash"]:
            raise ValueError("event stream hash mismatch")
        for event in run["events"]:
            rebuilt = EventEnvelope.create(**{key: event[key] for key in (
                "sequence", "year", "phase", "event_type", "actor_ids", "artifact_ids", "payload", "provenance")})
            if rebuilt.to_dict() != event:
                raise ValueError("canonical event id mismatch")
        records = [e["payload"] for e in run["events"] if e["event_type"] == "publication.recorded"]
        counts = {status: sum(r["status"] == status for r in records) for status in ("accept", "reject")}
        stored = run["checkpoint"]["mechanism_states"]["publication"]
        if counts != stored["status_counts"]:
            raise ValueError("production state/event counts differ")
        if (run["summary"]["accepted"] != counts["accept"] or run["summary"]["rejected"] != counts["reject"]
                or run["summary"]["publication_records"] != len(records)):
            raise ValueError("summary differs from independently counted production events")
        extra_events = [e for e in run["events"] if e["event_type"] == "generated.artifact_recorded"]
        if run["summary"]["invented_artifacts"] != len(extra_events):
            raise ValueError("invented artifact count mismatch")
        code_events = [e["payload"] for e in run["events"] if e["event_type"] == "generated.code_executed"]
        receipts = run["execution_receipts"]
        if len(code_events) != len(receipts) or len(receipts) != 2:
            raise ValueError("missing per-period execution receipts")
        for event, receipt in zip(code_events, receipts):
            expected = {key: receipt[key] for key in ("image_id", "artifact_sha256", "context_sha256", "result_sha256")}
            if event != expected or event["artifact_sha256"] != sha(artifact) or event["image_id"] != report["image_id"]:
                raise ValueError("code execution/source hash mismatch")
    for index, arm in enumerate(report["rounds"], start=1):
        if not arm["replay_passed"] or not arm["checkpoint_resume_passed"]:
            raise ValueError("replay/checkpoint verification failed")
        initial, revised = arm["observations"]
        for observation, proposal in zip((initial, revised), (report["proposals"][0], report["proposals"][index])):
            execution = proposal["evidence"]
            field = "accepted" if arm["objective"] == "accepted-record-count" else "rejected"
            if (observation["candidate"] != execution["system"] or observation["loss"] != -execution["summary"][field]
                    or observation["metadata"]["summary"] != execution["summary"]
                    or observation["metadata"]["event_stream_hash"] != execution["event_stream_hash"]):
                raise ValueError("objective/observation differs from actual execution")
        if arm["suggestions"][1]["based_on_observation_id"] != initial["observation_id"]:
            raise ValueError("missing result-dependent proposal lineage")
        history = json.loads(report["proposals"][index]["attempts"][0]["request"]["messages"][0]["content"].rsplit(
            "PREVIOUS ACTUAL OBSERVATIONS:\n", 1)[1])
        if history[0]["observation"] != initial or history[0]["artifact"] != report["proposals"][0]["artifact"]:
            raise ValueError("LLM revision did not receive the claimed actual observation")


def compact_result(original, repeated, original_path: Path, repeated_path: Path):
    verify_run(original)
    verify_run(repeated)
    if not repeated.get("frozen_reproduction_passed"):
        raise ValueError("frozen source reproduction is required")
    for key in ("source_commit", "source_sha256", "image_id", "rounds"):
        if original[key] != repeated[key]:
            raise ValueError("frozen reproduction mismatch: " + key)
    if repeated["frozen_input_sha256"] != hashlib.sha256(original_path.read_bytes()).hexdigest():
        raise ValueError("reproduction input file hash mismatch")
    for a, b in zip(original["proposals"], repeated["proposals"]):
        for key in ("artifact", "receipt"):
            if a[key] != b[key]:
                raise ValueError("frozen proposal mismatch")
        for key in ("checkpoint", "events", "summary", "system"):
            if a["evidence"][key] != b["evidence"][key]:
                raise ValueError("frozen execution mismatch")
    return {
        "schema": "scienceutopia.generated-code-compact-result.v1",
        "source_commit": original["source_commit"], "source_sha256": original["source_sha256"],
        "image_id": original["image_id"], "workload": original["workload"],
        "evidence_role": "engineering-integration-not-held-out-not-policy-validation",
        "wall_seconds": original["wall_seconds"], "reproduction_wall_seconds": repeated["wall_seconds"],
        "proposals": [{"artifact": proposal["artifact"], "rationale": proposal["rationale"],
                       "receipt": proposal["receipt"], "attempt_statuses": [
                           {"status": a["status"], "error": a.get("error"), "receipt": a["receipt"]}
                           for a in proposal["attempts"]],
                       "system_fingerprint": proposal["evidence"]["system_fingerprint"],
                       "summary": proposal["evidence"]["summary"]}
                      for proposal in original["proposals"]],
        "arms": [{"objective": arm["objective"], "loss_path": [o["loss"] for o in arm["observations"]],
                  "source_changed": arm["source_changed"], "selected_system_fingerprint": arm["selected_system_fingerprint"],
                  "replay_passed": arm["replay_passed"], "checkpoint_resume_passed": arm["checkpoint_resume_passed"]}
                 for arm in original["rounds"]],
        "raw_artifacts": [{"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                          for path in (original_path, repeated_path)],
        "frozen_reproduction": "exact source/system/events/checkpoint/observations; excludes timing",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--reproduction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compact_result(json.loads(args.original.read_text()), json.loads(args.reproduction.read_text()),
                            args.original, args.reproduction)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"verified": True, "output": str(args.output.resolve()), "arms": result["arms"]}))


if __name__ == "__main__":
    main()
