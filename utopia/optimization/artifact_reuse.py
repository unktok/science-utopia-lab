"""Content-addressed, read-only reuse of completed simulation trajectories.

The optimizer has arm-specific logical run ids, while a simulator trajectory is
identified by its producer inputs.  This module keeps those identities
separate.  Raw artifacts are sealed once, adopted by explicit registry
lineage, and verified on every resolution; derived evaluations are never part
of the sealed physical bundle.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


RECEIPT_SCHEMA = "scienceutopia.raw-artifact-bundle-receipt.v1"
IDENTITY_SCHEMA = "scienceutopia.simulation-execution-identity.v1"
RECEIPT_NAME = "raw_artifact_bundle_receipt.json"
DERIVED_DOC_FILES = {
    "objective_evaluation.json",
    RECEIPT_NAME,
    RECEIPT_NAME + ".tmp",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def object_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode())


def command_option(command: list[str], option: str) -> str | None:
    try:
        index = command.index(option)
    except ValueError:
        return None
    if index + 1 >= len(command):
        raise ValueError(f"{option} is missing its value")
    return command[index + 1]


def normalized_producer_command(command: Iterable[str]) -> list[str]:
    """Remove only logical naming/location from a simulator command."""
    result = list(command)
    for option, replacement in (
        ("--run-id", "<logical-run-id>"),
        ("--output-dir", "<logical-output-root>"),
    ):
        try:
            index = result.index(option)
        except ValueError as error:
            raise ValueError(f"producer command requires {option}") from error
        if index + 1 >= len(result):
            raise ValueError(f"{option} is missing its value")
        result[index + 1] = replacement
    return result


def execution_identity(record: Mapping[str, Any], source_commit: str) -> dict[str, Any]:
    if (
        not isinstance(source_commit, str)
        or len(source_commit) != 40
        or any(character not in "0123456789abcdef" for character in source_commit)
    ):
        raise ValueError("execution identity requires a full source commit")
    command = json.loads(record["command_json"])
    if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
        raise ValueError("command_json must contain a string array")
    design = json.loads(record["design_json"])
    return {
        "schema": IDENTITY_SCHEMA,
        "producer_source_commit": source_commit,
        "normalized_command": normalized_producer_command(command),
        "design": design,
        "design_id": record["design_id"],
        "fidelity": record["fidelity"],
        "seed_role": record["seed_role"],
        "seed": int(record["seed"]),
        "model": command_option(command, "--model"),
        "model_revision": command_option(command, "--model_revision"),
        "api_backend": command_option(command, "--api-backend"),
        "dataset_revision": command_option(command, "--dataset-revision"),
    }


def _walk_admitted(root: Path, run_id: str) -> list[Path]:
    admitted: list[Path] = []
    for category in ("docs", "checkpoints", "logs", "registry-logs"):
        directory = root / category / run_id
        if category in {"docs", "checkpoints"} and not directory.is_dir():
            raise ValueError(f"required artifact directory is missing: {directory}")
        if not directory.exists():
            continue
        if directory.is_symlink():
            raise ValueError(f"symlink is forbidden in raw artifact bundle: {directory}")
        for current, directories, files in os.walk(directory, followlinks=False):
            current_path = Path(current)
            for name in list(directories):
                child = current_path / name
                if child.is_symlink():
                    raise ValueError(
                        f"symlink is forbidden in raw artifact bundle: {child}"
                    )
            for name in files:
                child = current_path / name
                if child.is_symlink():
                    raise ValueError(
                        f"symlink is forbidden in raw artifact bundle: {child}"
                    )
                if category == "docs" and name in DERIVED_DOC_FILES:
                    continue
                if not child.is_file():
                    raise ValueError(f"non-regular artifact is forbidden: {child}")
                admitted.append(child)
    return sorted(admitted, key=lambda path: str(path.relative_to(root)))


def raw_file_records(root: Path, run_id: str) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(root)),
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in _walk_admitted(root, run_id)
    ]


def receipt_path(output_root: Path, run_id: str) -> Path:
    return output_root / "docs" / run_id / RECEIPT_NAME


def write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_receipt(
    path: Path,
    *,
    expected_sha256: str | None = None,
    expected_run_id: str | None = None,
    expected_identity_sha256: str | None = None,
) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"artifact receipt is missing or symlinked: {path}")
    actual_receipt_sha = file_sha256(path)
    if expected_sha256 is not None and actual_receipt_sha != expected_sha256:
        raise ValueError("artifact receipt hash mismatch")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("unsupported artifact receipt schema")
    if expected_run_id is not None and receipt.get("physical_run_id") != expected_run_id:
        raise ValueError("artifact receipt physical run id mismatch")
    if (
        expected_identity_sha256 is not None
        and receipt.get("execution_identity_sha256") != expected_identity_sha256
    ):
        raise ValueError("artifact receipt execution identity mismatch")
    if object_sha256(receipt.get("execution_identity")) != receipt.get(
        "execution_identity_sha256"
    ):
        raise ValueError("artifact receipt execution identity hash is invalid")
    if object_sha256(receipt.get("source_attempt_provenance")) != receipt.get(
        "source_attempt_provenance_sha256"
    ):
        raise ValueError("artifact receipt attempt provenance hash is invalid")
    output_root = Path(receipt["physical_output_root"])
    run_id = receipt["physical_run_id"]
    declared = receipt.get("raw_files")
    if not isinstance(declared, list) or not declared:
        raise ValueError("artifact receipt contains no raw files")
    current = raw_file_records(output_root, run_id)
    if canonical_json(current) != canonical_json(declared):
        raise ValueError("sealed raw artifact bundle is missing, changed, or has extra files")
    return receipt


@dataclass(frozen=True)
class ResolvedArtifact:
    logical_run_id: str
    physical_run_id: str
    physical_output_root: Path
    mode: str
    execution_identity_sha256: str | None = None
    bundle_receipt_sha256: str | None = None
    source_registry_path: Path | None = None

    @property
    def docs_dir(self) -> Path:
        return self.physical_output_root / "docs" / self.physical_run_id

    @property
    def checkpoints_dir(self) -> Path:
        return self.physical_output_root / "checkpoints" / self.physical_run_id

    @property
    def logs_dir(self) -> Path:
        return self.physical_output_root / "logs" / self.physical_run_id
