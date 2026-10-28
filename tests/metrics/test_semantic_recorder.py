from copy import deepcopy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from utopia.metrics.semantic_instrumentation import EVENT_TYPES, build_shadow_report
from utopia.metrics.semantic_recorder import (
    CONFIG_SCHEMA,
    DEFAULT_CONFIG,
    open_semantic_recorder,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "prospective-semantic-recorder-integration-v1.json"
RECORDER_SCHEMA = ROOT / "research" / "specs" / "semantic-recorder-v1.schema.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _integration_material():
    fixture = _load(FIXTURE)
    plan_path = ROOT / fixture["explicit_event_plan"]["path"]
    assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == (
        fixture["explicit_event_plan"]["file_sha256"]
    )
    source = _load(plan_path)
    recorder = fixture["recorder"]
    config = {
        "schema": CONFIG_SCHEMA,
        "enabled": True,
        "recorder_id": recorder["recorder_id"],
        "bundle_id": source["bundle_id"],
        "classification": source["classification"],
        "instrumentation_use": "report_only",
        "run_id": source["run_id"],
        "producer": recorder["producer"],
        "system_fingerprint": recorder["system_fingerprint"],
        "model_fingerprint": recorder["model_fingerprint"],
        "ground_truth": source["ground_truth"],
    }
    return fixture, source, config


def _emit(recorder, event):
    family = EVENT_TYPES[event["event_type"]]
    method = getattr(recorder, f"append_{family}")
    return method(
        event_type=event["event_type"],
        event_id=event["event_id"],
        step=event["step"],
        actor_id=event["actor_id"],
        institution_id=event["institution_id"],
        source_event_ids=event["provenance"]["source_event_ids"],
        payload=event["payload"],
    )


def _stream_records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_default_is_disabled_and_creates_no_files(tmp_path):
    stream = tmp_path / "must-not-exist.jsonl"
    recorder = open_semantic_recorder(stream_path=stream)

    receipt = recorder.append_claim(
        paper_text="There is deliberately no text interpretation API."
    )

    assert DEFAULT_CONFIG == {
        "schema": "scienceutopia.semantic-recorder-config.v1",
        "enabled": False,
    }
    assert receipt == {
        "recorded": False,
        "reason": "semantic_recorder_disabled",
        "optimization_input": False,
    }
    assert not stream.exists()
    assert not stream.with_suffix(".jsonl.checkpoint.json").exists()
    jsonschema.Draft202012Validator(_load(RECORDER_SCHEMA)).validate(DEFAULT_CONFIG)


def test_explicit_synthetic_producer_checkpoint_resume_and_schema(tmp_path):
    fixture, source, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    split = fixture["resume_after_event_count"]

    for event in source["events"][:split]:
        assert _emit(recorder, event)["recorded"] is True
    checkpoint = recorder.checkpoint()
    assert checkpoint["entry_count"] == split

    recorder = open_semantic_recorder(config, stream, resume=True)
    for event in source["events"][split:]:
        _emit(recorder, event)

    bundle = recorder.build_bundle()
    assert bundle == source
    report = build_shadow_report(bundle)
    assert report["authorization"]["optimization_input"] is False
    assert report["contract_coverage"]["events"] == fixture["expected"]["event_count"]

    schema = _load(RECORDER_SCHEMA)
    validator = jsonschema.Draft202012Validator(schema)
    jsonschema.Draft202012Validator.check_schema(schema)
    validator.validate(config)
    records = _stream_records(stream)
    for record in records:
        validator.validate(record)
    validator.validate(_load(stream.with_suffix(".jsonl.checkpoint.json")))
    assert records[-1]["event"]["event_id"] == fixture["expected"]["last_event_id"]
    assert all(record.get("optimization_input") is not True for record in records)


def test_invalid_lineage_fails_before_append_without_changing_stream(tmp_path):
    _, source, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    _emit(recorder, source["events"][0])
    before_stream = stream.read_bytes()
    before_checkpoint = stream.with_suffix(".jsonl.checkpoint.json").read_bytes()
    invalid = deepcopy(source["events"][1])
    invalid["provenance"]["source_event_ids"] = ["unknown-future-event"]

    with pytest.raises(ValueError, match="forward or unknown source events"):
        _emit(recorder, invalid)

    assert stream.read_bytes() == before_stream
    assert stream.with_suffix(".jsonl.checkpoint.json").read_bytes() == before_checkpoint


def test_explicit_missingness_survives_recording_without_inference(tmp_path):
    _, source, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    for event in source["events"][:2]:
        event = deepcopy(event)
        if event["event_type"] == "evidence.attached":
            event["payload"]["lineage"]["model"] = {
                "status": "missing",
                "reason": "not_observed",
                "detail": "The producer did not observe a model identifier.",
            }
        _emit(recorder, event)

    bundle = recorder.build_bundle()
    model = bundle["events"][1]["payload"]["lineage"]["model"]
    assert model == {
        "status": "missing",
        "reason": "not_observed",
        "detail": "The producer did not observe a model identifier.",
    }
    assert "value" not in model


def test_enabled_recorder_has_no_document_inference_entry_point(tmp_path):
    _, _, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    before = stream.read_bytes()

    with pytest.raises(TypeError, match="paper_text"):
        recorder.append_claim(paper_text="Do not infer a claim from this sentence.")

    assert stream.read_bytes() == before


@pytest.mark.parametrize(
    ("identity_field", "changed_value"),
    [
        ("run_id", "different-run"),
        ("system_fingerprint", "c" * 64),
        ("model_fingerprint", "d" * 64),
    ],
)
def test_resume_refuses_run_system_or_model_mismatch(
    tmp_path, identity_field, changed_value
):
    _, source, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    _emit(recorder, source["events"][0])
    changed = deepcopy(config)
    changed[identity_field] = changed_value

    with pytest.raises(ValueError, match="persisted header"):
        open_semantic_recorder(changed, stream, resume=True)


def test_resume_refuses_entry_tampering_even_if_json_is_valid(tmp_path):
    _, source, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    _emit(recorder, source["events"][0])
    records = _stream_records(stream)
    records[1]["event"]["actor_id"] = "tampered-actor"
    stream.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="entry hash mismatch"):
        open_semantic_recorder(config, stream, resume=True)

    with pytest.raises(ValueError, match="entry hash mismatch"):
        _emit(recorder, source["events"][1])


def test_resume_refuses_truncation_and_stale_checkpoint(tmp_path):
    _, source, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    for event in source["events"][:2]:
        _emit(recorder, event)
    records = _stream_records(stream)
    stream.write_text(
        "\n".join(json.dumps(item) for item in records[:-1]) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checkpoint entry_count mismatch"):
        open_semantic_recorder(config, stream, resume=True)


def test_torn_record_and_tampered_checkpoint_fail_closed(tmp_path):
    _, source, config = _integration_material()
    stream = tmp_path / "semantic.jsonl"
    recorder = open_semantic_recorder(config, stream)
    _emit(recorder, source["events"][0])
    stream.write_bytes(stream.read_bytes().rstrip(b"\n"))
    with pytest.raises(ValueError, match="torn final record"):
        open_semantic_recorder(config, stream, resume=True)

    clean_stream = tmp_path / "clean.jsonl"
    recorder = open_semantic_recorder(config, clean_stream)
    _emit(recorder, source["events"][0])
    checkpoint_path = clean_stream.with_suffix(".jsonl.checkpoint.json")
    checkpoint = _load(checkpoint_path)
    checkpoint["entry_count"] = 99
    checkpoint_path.write_text(json.dumps(checkpoint) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint hash mismatch"):
        open_semantic_recorder(config, clean_stream, resume=True)
