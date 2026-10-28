"""Prospective, append-only producer boundary for semantic instrumentation.

The recorder accepts only explicit typed events emitted by a simulator
mechanism at event occurrence.  It does not inspect papers, reviews, prompts,
or other free text.  Recorded data remains report-only and is not an
optimization input.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Mapping, Sequence

from utopia.metrics.semantic_instrumentation import (
    BUNDLE_SCHEMA,
    CLASSIFICATIONS,
    EVENT_SCHEMAS,
    EVENT_TYPES,
    _parse_ground_truth,
    validate_bundle,
)


CONFIG_SCHEMA = "scienceutopia.semantic-recorder-config.v1"
HEADER_SCHEMA = "scienceutopia.semantic-recorder-header.v1"
ENTRY_SCHEMA = "scienceutopia.semantic-recorder-entry.v1"
CHECKPOINT_SCHEMA = "scienceutopia.semantic-recorder-checkpoint.v1"
INTEGRITY_ALGORITHM = "sha256-canonical-json-chain-v1"
DEFAULT_CONFIG = {"schema": CONFIG_SCHEMA, "enabled": False}
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_fields(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{context} fields do not match the v1 contract")


def _nonempty(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _fingerprint(value: Any, context: str) -> str:
    if not isinstance(value, str) or _FINGERPRINT.fullmatch(value) is None:
        raise ValueError(f"{context} must be a lowercase sha256 fingerprint")
    return value


def _parse_config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    if config is None:
        return deepcopy(DEFAULT_CONFIG)
    if not isinstance(config, Mapping):
        raise ValueError("semantic recorder config must be an object")
    if config.get("enabled") is False:
        _exact_fields(config, {"schema", "enabled"}, "disabled recorder config")
        if config.get("schema") != CONFIG_SCHEMA:
            raise ValueError("semantic recorder config schema is unsupported")
        return deepcopy(dict(config))

    expected = {
        "schema",
        "enabled",
        "recorder_id",
        "bundle_id",
        "classification",
        "instrumentation_use",
        "run_id",
        "producer",
        "system_fingerprint",
        "model_fingerprint",
        "ground_truth",
    }
    _exact_fields(config, expected, "enabled recorder config")
    if config.get("schema") != CONFIG_SCHEMA or config.get("enabled") is not True:
        raise ValueError("enabled semantic recorder config is unsupported")
    if config.get("classification") not in CLASSIFICATIONS:
        raise ValueError("semantic recorder classification is unsupported")
    if config.get("instrumentation_use") != "report_only":
        raise ValueError("semantic recorder is report_only and cannot rank candidates")
    parsed = deepcopy(dict(config))
    for field in ("recorder_id", "bundle_id", "run_id", "producer"):
        parsed[field] = _nonempty(parsed[field], f"recorder config {field}")
    parsed["system_fingerprint"] = _fingerprint(
        parsed["system_fingerprint"], "system_fingerprint"
    )
    parsed["model_fingerprint"] = _fingerprint(
        parsed["model_fingerprint"], "model_fingerprint"
    )
    parsed["ground_truth"] = _parse_ground_truth(
        parsed["ground_truth"], parsed["classification"]
    )
    return parsed


class DisabledSemanticRecorder:
    """No-op returned by the default-disabled configuration.

    The receipt is explicit so a producer cannot confuse a disabled recorder
    with a durable append.
    """

    enabled = False

    @staticmethod
    def _disabled_receipt() -> dict[str, Any]:
        return {
            "recorded": False,
            "reason": "semantic_recorder_disabled",
            "optimization_input": False,
        }

    def append_claim(self, **_: Any) -> dict[str, Any]:
        return self._disabled_receipt()

    def append_evidence(self, **_: Any) -> dict[str, Any]:
        return self._disabled_receipt()

    def append_verification(self, **_: Any) -> dict[str, Any]:
        return self._disabled_receipt()

    def append_replication(self, **_: Any) -> dict[str, Any]:
        return self._disabled_receipt()

    def append_correction(self, **_: Any) -> dict[str, Any]:
        return self._disabled_receipt()

    def checkpoint(self) -> dict[str, Any]:
        return self._disabled_receipt()


class SemanticRecorder:
    """Single-writer append-only semantic event recorder."""

    enabled = True

    def __init__(
        self,
        config: Mapping[str, Any],
        stream_path: Path,
        *,
        resume: bool,
    ) -> None:
        self._config = _parse_config(config)
        if not self._config["enabled"]:
            raise ValueError("SemanticRecorder requires an enabled config")
        self.stream_path = Path(stream_path)
        self.checkpoint_path = self.stream_path.with_suffix(
            self.stream_path.suffix + ".checkpoint.json"
        )
        self._events: list[dict[str, Any]] = []
        self._header: dict[str, Any]
        self._tail_sha256 = ""
        self._lock = threading.Lock()
        if resume:
            self._resume()
        else:
            self._initialize()

    def _header_body(self) -> dict[str, Any]:
        return {
            "schema": HEADER_SCHEMA,
            "record_type": "header",
            "recorder_id": self._config["recorder_id"],
            "bundle_id": self._config["bundle_id"],
            "classification": self._config["classification"],
            "instrumentation_use": "report_only",
            "optimization_input": False,
            "run_id": self._config["run_id"],
            "producer": self._config["producer"],
            "system_fingerprint": self._config["system_fingerprint"],
            "model_fingerprint": self._config["model_fingerprint"],
            "ground_truth": deepcopy(self._config["ground_truth"]),
            "integrity_algorithm": INTEGRITY_ALGORITHM,
        }

    def _initialize(self) -> None:
        if self.stream_path.exists() or self.checkpoint_path.exists():
            raise FileExistsError("semantic recorder stream or checkpoint already exists")
        self.stream_path.parent.mkdir(parents=True, exist_ok=True)
        body = self._header_body()
        self._header = {**body, "header_sha256": _sha256(body)}
        line = _canonical_json(self._header) + "\n"
        try:
            with self.stream_path.open("x", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            self._tail_sha256 = self._header["header_sha256"]
            self._write_checkpoint()
        except Exception:
            # Do not silently reuse a partially initialized stream.
            raise

    def _read_stream(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        raw = self.stream_path.read_bytes()
        if not raw or not raw.endswith(b"\n"):
            raise ValueError("semantic recorder stream is empty or has a torn final record")
        try:
            lines = raw.decode("utf-8").splitlines()
            records = [json.loads(line) for line in lines]
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("semantic recorder stream is not valid UTF-8 JSONL") from error
        if not records or any(not isinstance(item, dict) for item in records):
            raise ValueError("semantic recorder stream has invalid records")
        return records[0], records[1:]

    def _verify_header(self, header: Mapping[str, Any]) -> dict[str, Any]:
        expected = set(self._header_body()) | {"header_sha256"}
        _exact_fields(header, expected, "semantic recorder header")
        if header.get("schema") != HEADER_SCHEMA or header.get("record_type") != "header":
            raise ValueError("semantic recorder header contract is unsupported")
        body = {key: deepcopy(value) for key, value in header.items() if key != "header_sha256"}
        if header.get("header_sha256") != _sha256(body):
            raise ValueError("semantic recorder header hash mismatch")
        expected_body = self._header_body()
        if body != expected_body:
            raise ValueError("semantic recorder config does not match the persisted header")
        return deepcopy(dict(header))

    def _verify_entries(
        self, records: Sequence[Mapping[str, Any]], header_sha256: str
    ) -> tuple[list[dict[str, Any]], str]:
        expected_fields = {
            "schema",
            "record_type",
            "entry_index",
            "run_id",
            "system_fingerprint",
            "model_fingerprint",
            "previous_entry_sha256",
            "event",
            "entry_sha256",
        }
        events: list[dict[str, Any]] = []
        previous = header_sha256
        for index, record in enumerate(records):
            _exact_fields(record, expected_fields, "semantic recorder entry")
            if record.get("schema") != ENTRY_SCHEMA or record.get("record_type") != "event":
                raise ValueError("semantic recorder entry contract is unsupported")
            if record.get("entry_index") != index:
                raise ValueError("semantic recorder entry index is not contiguous")
            if record.get("previous_entry_sha256") != previous:
                raise ValueError("semantic recorder hash chain is broken")
            if record.get("run_id") != self._config["run_id"]:
                raise ValueError("semantic recorder entry run fingerprint mismatch")
            if record.get("system_fingerprint") != self._config["system_fingerprint"]:
                raise ValueError("semantic recorder entry system fingerprint mismatch")
            if record.get("model_fingerprint") != self._config["model_fingerprint"]:
                raise ValueError("semantic recorder entry model fingerprint mismatch")
            body = {
                key: deepcopy(value)
                for key, value in record.items()
                if key != "entry_sha256"
            }
            expected_hash = _sha256(body)
            if record.get("entry_sha256") != expected_hash:
                raise ValueError("semantic recorder entry hash mismatch")
            event = record.get("event")
            if not isinstance(event, Mapping):
                raise ValueError("semantic recorder event must be an object")
            events.append(deepcopy(dict(event)))
            previous = expected_hash
        if events:
            validate_bundle(self._bundle(events))
        return events, previous

    def _read_checkpoint(self) -> dict[str, Any]:
        try:
            checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("semantic recorder checkpoint is missing or invalid") from error
        expected = {
            "schema",
            "recorder_id",
            "run_id",
            "header_sha256",
            "entry_count",
            "tail_entry_sha256",
            "last_event_id",
            "last_sequence",
            "stream_size_bytes",
            "stream_sha256",
            "checkpoint_sha256",
        }
        _exact_fields(checkpoint, expected, "semantic recorder checkpoint")
        if checkpoint.get("schema") != CHECKPOINT_SCHEMA:
            raise ValueError("semantic recorder checkpoint contract is unsupported")
        body = {
            key: deepcopy(value)
            for key, value in checkpoint.items()
            if key != "checkpoint_sha256"
        }
        if checkpoint.get("checkpoint_sha256") != _sha256(body):
            raise ValueError("semantic recorder checkpoint hash mismatch")
        return checkpoint

    def _resume(self) -> None:
        if not self.stream_path.exists():
            raise FileNotFoundError("semantic recorder stream does not exist for resume")
        header, records = self._read_stream()
        self._header = self._verify_header(header)
        events, tail = self._verify_entries(records, self._header["header_sha256"])
        self._verify_checkpoint(events, tail)
        self._events = events
        self._tail_sha256 = tail

    def _verify_checkpoint(
        self, events: Sequence[Mapping[str, Any]], tail: str
    ) -> dict[str, Any]:
        checkpoint = self._read_checkpoint()
        expected_last_event_id = events[-1]["event_id"] if events else None
        expected_last_sequence = events[-1]["sequence"] if events else None
        checks = {
            "recorder_id": self._config["recorder_id"],
            "run_id": self._config["run_id"],
            "header_sha256": self._header["header_sha256"],
            "entry_count": len(events),
            "tail_entry_sha256": tail,
            "last_event_id": expected_last_event_id,
            "last_sequence": expected_last_sequence,
            "stream_size_bytes": self.stream_path.stat().st_size,
            "stream_sha256": _file_sha256(self.stream_path),
        }
        for field, expected in checks.items():
            if checkpoint.get(field) != expected:
                raise ValueError(f"semantic recorder checkpoint {field} mismatch")
        return checkpoint

    def _verify_durable_state(self) -> None:
        """Reject any out-of-band change before another event is appended."""
        header, records = self._read_stream()
        verified_header = self._verify_header(header)
        events, tail = self._verify_entries(records, verified_header["header_sha256"])
        self._verify_checkpoint(events, tail)
        if events != self._events or tail != self._tail_sha256:
            raise ValueError("semantic recorder in-memory state differs from durable stream")

    def _bundle(self, events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "schema": BUNDLE_SCHEMA,
            "bundle_id": self._config["bundle_id"],
            "classification": self._config["classification"],
            "instrumentation_use": "report_only",
            "run_id": self._config["run_id"],
            "events": deepcopy(list(events)),
            "ground_truth": deepcopy(self._config["ground_truth"]),
        }

    def build_bundle(self) -> dict[str, Any]:
        """Return a validated report-only bundle for the recorded prefix."""
        if not self._events:
            raise ValueError("semantic recorder has no events to bundle")
        return validate_bundle(self._bundle(self._events))

    def _checkpoint_body(self) -> dict[str, Any]:
        last = self._events[-1] if self._events else None
        return {
            "schema": CHECKPOINT_SCHEMA,
            "recorder_id": self._config["recorder_id"],
            "run_id": self._config["run_id"],
            "header_sha256": self._header["header_sha256"],
            "entry_count": len(self._events),
            "tail_entry_sha256": self._tail_sha256,
            "last_event_id": last["event_id"] if last else None,
            "last_sequence": last["sequence"] if last else None,
            "stream_size_bytes": self.stream_path.stat().st_size,
            "stream_sha256": _file_sha256(self.stream_path),
        }

    def _write_checkpoint(self) -> dict[str, Any]:
        body = self._checkpoint_body()
        checkpoint = {**body, "checkpoint_sha256": _sha256(body)}
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.checkpoint_path.name}.",
            dir=self.checkpoint_path.parent,
            text=True,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(_canonical_json(checkpoint) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.checkpoint_path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
        return checkpoint

    def checkpoint(self) -> dict[str, Any]:
        """Re-verify the stream and atomically publish its current checkpoint."""
        with self._lock:
            self._verify_durable_state()
            return self._write_checkpoint()

    def _append(
        self,
        family: str,
        *,
        event_type: str,
        event_id: str,
        step: int,
        actor_id: str,
        institution_id: str,
        source_event_ids: Sequence[str],
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if EVENT_TYPES.get(event_type) != family:
            raise ValueError(f"{event_type!r} is not a {family} event")
        if isinstance(source_event_ids, (str, bytes)) or not isinstance(
            source_event_ids, Sequence
        ):
            raise ValueError("source_event_ids must be an explicit sequence")
        event = {
            "schema": EVENT_SCHEMAS[family],
            "event_id": _nonempty(event_id, "event_id"),
            "sequence": len(self._events),
            "step": step,
            "event_type": event_type,
            "actor_id": _nonempty(actor_id, "actor_id"),
            "institution_id": _nonempty(institution_id, "institution_id"),
            "provenance": {
                "run_id": self._config["run_id"],
                "producer": self._config["producer"],
                "source_event_ids": list(source_event_ids),
            },
            "payload": deepcopy(dict(payload)),
        }
        with self._lock:
            self._verify_durable_state()
            # Validate the full prospective prefix before any durable write.
            parsed_bundle = validate_bundle(self._bundle([*self._events, event]))
            parsed_event = parsed_bundle["events"][-1]
            body = {
                "schema": ENTRY_SCHEMA,
                "record_type": "event",
                "entry_index": len(self._events),
                "run_id": self._config["run_id"],
                "system_fingerprint": self._config["system_fingerprint"],
                "model_fingerprint": self._config["model_fingerprint"],
                "previous_entry_sha256": self._tail_sha256,
                "event": parsed_event,
            }
            entry_hash = _sha256(body)
            entry = {**body, "entry_sha256": entry_hash}
            with self.stream_path.open("a", encoding="utf-8") as handle:
                handle.write(_canonical_json(entry) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._events.append(parsed_event)
            self._tail_sha256 = entry_hash
            checkpoint = self._write_checkpoint()
            return {
                "recorded": True,
                "event_id": parsed_event["event_id"],
                "sequence": parsed_event["sequence"],
                "entry_sha256": entry_hash,
                "checkpoint_sha256": checkpoint["checkpoint_sha256"],
                "optimization_input": False,
            }

    def append_claim(self, **event: Any) -> dict[str, Any]:
        return self._append("claim", **event)

    def append_evidence(self, **event: Any) -> dict[str, Any]:
        return self._append("evidence", **event)

    def append_verification(self, **event: Any) -> dict[str, Any]:
        return self._append("verification", **event)

    def append_replication(self, **event: Any) -> dict[str, Any]:
        return self._append("replication", **event)

    def append_correction(self, **event: Any) -> dict[str, Any]:
        return self._append("correction", **event)


def open_semantic_recorder(
    config: Mapping[str, Any] | None = None,
    stream_path: Path | str | None = None,
    *,
    resume: bool = False,
) -> DisabledSemanticRecorder | SemanticRecorder:
    """Open an explicit semantic producer boundary.

    With no config, or the exact v1 disabled config, no path is created.  An
    enabled config requires a caller-selected stream path.  Resume always
    verifies header identity, every hash-chain entry, semantic lifecycle, and
    the separate checkpoint before allowing another append.
    """

    parsed = _parse_config(config)
    if not parsed["enabled"]:
        if resume:
            raise ValueError("a disabled semantic recorder cannot resume")
        return DisabledSemanticRecorder()
    if stream_path is None:
        raise ValueError("an enabled semantic recorder requires stream_path")
    return SemanticRecorder(parsed, Path(stream_path), resume=resume)
