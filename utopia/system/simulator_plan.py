"""Compile a validated ``SystemSpec`` into a sealed simulator campaign plan.

This module is intentionally narrower than the generic mechanism graph.  It
maps only implementations that the current monolithic ScienceUtopia simulator
can execute exactly.  Unsupported families, implementations, graph mutations,
and parameters fail closed instead of being dropped from an experiment plan.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from utopia.arguments import parse_arguments

from .legacy import LEGACY_ADAPTER, LegacyCompilationError, compile_legacy_system
from .model import MechanismFamily, MechanismSpec, SystemSpec
from .production.communication import KNOWLEDGE_BROADCAST, KNOWLEDGE_DIGEST
from .validation import validate_system_spec


PLAN_SCHEMA = "scienceutopia.system-spec-simulator-experiment-plan.v1"
COMPILER_ID = "scienceutopia.system-spec-to-simulator-plan"
COMPILER_REVISION = "1.1.0"
SEAL_ALGORITHM = "sha256"
NATIVE_COMMUNICATION_SOURCE = "native.communication.accepted-output-source-v1"
NATIVE_COMMUNICATION_RECEIVER = "native.communication.researcher-receiver-v1"

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class SimulatorPlanCompilationError(ValueError):
    """The candidate cannot be represented by the current simulator."""


class SimulatorPlanValidationError(ValueError):
    """A serialized plan is malformed, unsealed, or no longer reproducible."""


@dataclass(frozen=True)
class SimulatorModelSpec:
    model: str
    api_backend: str
    endpoint: str
    batch_size: int
    model_revision: str | None = None
    dataset_revision: str = "f80fb38a034b2f763dfcbdd2cd187f5b42ddcce6"


@dataclass(frozen=True)
class SimulatorFidelitySpec:
    fidelity_id: str
    experiment_stage: str
    num_years: int
    num_institutions: int
    num_conferences: int


@dataclass(frozen=True)
class SimulatorPlanRequest:
    campaign_id: str
    seed_role: str
    seeds: tuple[int, ...]
    model: SimulatorModelSpec
    fidelity: SimulatorFidelitySpec
    output_root: str
    data_cache_dir: str
    compiler_source_commit: str
    compiler_tree_dirty: bool
    source_locator: str


@dataclass(frozen=True)
class ParameterBinding:
    parameter: str
    cli_flag: str | None
    encoding: str
    value: Any


@dataclass(frozen=True)
class MechanismMapping:
    mechanism_id: str
    family: str
    implementation: str
    implementation_version: int
    execution_surface: str
    parameter_bindings: tuple[ParameterBinding, ...]
    mapping_sha256: str


@dataclass(frozen=True)
class SimulatorRunPlan:
    run_id: str
    seed: int
    simulator_argv: tuple[str, ...]
    argv_sha256: str


@dataclass(frozen=True)
class SealedSimulatorExperimentPlan:
    """Self-contained, content-sealed plan; it does not execute a campaign."""

    source_system_spec: Mapping[str, Any]
    source_system_fingerprint: str
    request: SimulatorPlanRequest
    mechanism_mappings: tuple[MechanismMapping, ...]
    runs: tuple[SimulatorRunPlan, ...]
    payload_sha256: str

    @property
    def plan_fingerprint(self) -> str:
        return self.payload_sha256

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "schema": PLAN_SCHEMA,
            "compiler": {
                "id": COMPILER_ID,
                "revision": COMPILER_REVISION,
            },
            "source_system": {
                "system_id": self.source_system_spec["system_id"],
                "version": self.source_system_spec["version"],
                "fingerprint": self.source_system_fingerprint,
                "spec": _json_value(self.source_system_spec),
            },
            "campaign": _request_dict(self.request),
            "mechanism_mappings": [
                _mechanism_mapping_dict(item) for item in self.mechanism_mappings
            ],
            "runs": [_run_dict(item) for item in self.runs],
            "claim_boundary": (
                "execution-plan-only; no scientific ranking, objective, or policy claim"
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload_dict(),
            "seal": {
                "algorithm": SEAL_ALGORITHM,
                "payload_sha256": self.payload_sha256,
            },
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SealedSimulatorExperimentPlan":
        """Strictly parse a serialized plan before semantic validation."""

        _exact_keys(
            value,
            {
                "schema",
                "compiler",
                "source_system",
                "campaign",
                "mechanism_mappings",
                "runs",
                "claim_boundary",
                "seal",
            },
            "$",
        )
        if value["schema"] != PLAN_SCHEMA:
            raise SimulatorPlanValidationError("unsupported plan schema")
        compiler = _object(value["compiler"], "compiler")
        _exact_keys(compiler, {"id", "revision"}, "compiler")
        if compiler != {"id": COMPILER_ID, "revision": COMPILER_REVISION}:
            raise SimulatorPlanValidationError("unsupported compiler identity or revision")
        if value["claim_boundary"] != (
            "execution-plan-only; no scientific ranking, objective, or policy claim"
        ):
            raise SimulatorPlanValidationError("claim_boundary changed")

        source = _object(value["source_system"], "source_system")
        _exact_keys(source, {"system_id", "version", "fingerprint", "spec"}, "source_system")
        spec = _object(source["spec"], "source_system.spec")
        if (
            source["system_id"] != spec.get("system_id")
            or source["version"] != spec.get("version")
        ):
            raise SimulatorPlanValidationError("source_system identity differs from embedded spec")
        request = _request_from_dict(_object(value["campaign"], "campaign"))
        mappings = _sequence(value["mechanism_mappings"], "mechanism_mappings")
        runs = _sequence(value["runs"], "runs")
        seal = _object(value["seal"], "seal")
        _exact_keys(seal, {"algorithm", "payload_sha256"}, "seal")
        if seal["algorithm"] != SEAL_ALGORITHM:
            raise SimulatorPlanValidationError("unsupported seal algorithm")
        return cls(
            source_system_spec=spec,
            source_system_fingerprint=_string(source["fingerprint"], "source_system.fingerprint"),
            request=request,
            mechanism_mappings=tuple(
                _mechanism_mapping_from_dict(
                    _object(item, f"mechanism_mappings[{index}]")
                )
                for index, item in enumerate(mappings)
            ),
            runs=tuple(
                _run_from_dict(_object(item, f"runs[{index}]"))
                for index, item in enumerate(runs)
            ),
            payload_sha256=_string(seal["payload_sha256"], "seal.payload_sha256"),
        )


@dataclass(frozen=True)
class _ImplementationContract:
    family: MechanismFamily
    parameters: tuple[tuple[str, str | None, str], ...]
    execution_surface: str = "cli"


_IMPLEMENTATIONS: Mapping[str, _ImplementationContract] = {
    "legacy.population.university-only-v1": _ImplementationContract(
        MechanismFamily.POPULATION,
        (
            ("mode", "--population_mode", "scalar"),
            ("researchers_per_institution", "--researchers_per_institution", "scalar"),
            ("resource_profile", "--population_resource_profile", "optional-scalar"),
        ),
    ),
    "legacy.research.llm-project-cycle-v1": _ImplementationContract(
        MechanismFamily.RESEARCH,
        (("funding_application_cost", "--funding_application_cost", "scalar"),),
    ),
    "legacy.evaluation.peer-review-v1": _ImplementationContract(
        MechanismFamily.EVALUATION,
        (
            ("acceptance_rate", "--acceptance_rate_schedule", "repeat-per-year"),
            ("reviews_per_paper", "--reviews_per_paper", "scalar"),
            ("reviewer_capacity", "--reviewer_capacity", "scalar"),
            ("reviewer_matching", "--reviewer_matching", "scalar"),
            ("review_policy", "--review_policy", "scalar"),
            ("acceptance_tiebreak", "--acceptance_tiebreak", "scalar"),
            ("acceptance_mode", "--acceptance_mode", "scalar"),
        ),
    ),
    "legacy.publication.conference-v1": _ImplementationContract(
        MechanismFamily.PUBLICATION,
        (("resubmission_cost", "--resubmission_cost", "scalar"),),
    ),
    "legacy.communication.citation-v1": _ImplementationContract(
        MechanismFamily.COMMUNICATION,
        (),
        "simulator-built-in",
    ),
    "legacy.funding.fixed-budget-v1": _ImplementationContract(
        MechanismFamily.FUNDING,
        (
            ("allocation_mode", "--funding_allocation_mode", "scalar"),
            ("budget_mode", "--funding_budget_mode", "scalar"),
            ("budget_slots_fraction", "--funding_budget_slots_frac", "scalar"),
        ),
    ),
    NATIVE_COMMUNICATION_SOURCE: _ImplementationContract(
        MechanismFamily.COMMUNICATION,
        (),
        "simulator-built-in",
    ),
    KNOWLEDGE_BROADCAST: _ImplementationContract(
        MechanismFamily.COMMUNICATION,
        (
            ("mode", "--communication-broker-mode", "scalar"),
            ("digest_size", "--communication-digest-size", "scalar"),
            ("delivery_latency", "--communication-latency", "scalar"),
        ),
    ),
    KNOWLEDGE_DIGEST: _ImplementationContract(
        MechanismFamily.COMMUNICATION,
        (
            ("mode", "--communication-broker-mode", "scalar"),
            ("digest_size", "--communication-digest-size", "scalar"),
            ("delivery_latency", "--communication-latency", "scalar"),
        ),
    ),
    NATIVE_COMMUNICATION_RECEIVER: _ImplementationContract(
        MechanismFamily.RESEARCH,
        (("receiver_role", "--communication-receiver-role", "scalar"),),
    ),
}

_RUNTIME_PARAMETERS = {
    "experiment_name",
    "rag_device",
    "log_funding_applications",
    "log_resource_ledger",
}


def compile_system_spec_experiment_plan(
    spec: SystemSpec,
    request: SimulatorPlanRequest,
) -> SealedSimulatorExperimentPlan:
    """Compile the current simulator's exact executable SystemSpec subset.

    The result is a dry-run plan only.  This function never creates output
    directories, opens a model endpoint, registers jobs, or starts simulation.
    """

    validate_system_spec(spec).require_valid()
    _validate_request(request)
    mappings = _compile_mechanism_mappings(spec, request.fidelity.num_years)
    runtime = spec.metadata.get("runtime")
    if not isinstance(runtime, Mapping):
        raise SimulatorPlanCompilationError("metadata.runtime must be an object")
    extra_runtime = sorted(set(runtime) - _RUNTIME_PARAMETERS)
    missing_runtime = sorted(_RUNTIME_PARAMETERS - set(runtime))
    if missing_runtime or extra_runtime:
        raise SimulatorPlanCompilationError(
            "metadata.runtime must map exactly the supported runtime surface; "
            f"missing={missing_runtime}, unsupported={extra_runtime}"
        )
    if spec.metadata.get("compiler") != LEGACY_ADAPTER:
        raise SimulatorPlanCompilationError(
            f"SystemSpec is not bound to supported adapter {LEGACY_ADAPTER!r}"
        )
    try:
        from utopia.communication.native import split_native_communication_system_spec
        base_spec, native_config = split_native_communication_system_spec(spec)
        legacy = compile_legacy_system(base_spec, years=request.fidelity.num_years)
    except (LegacyCompilationError, ValueError) as error:
        raise SimulatorPlanCompilationError(str(error)) from error
    cli_args = legacy.cli_args + _native_communication_args(native_config)
    _validate_mapping_arguments(mappings, cli_args)

    runs = tuple(
        _compile_run(spec, request, cli_args, seed) for seed in request.seeds
    )
    provisional = SealedSimulatorExperimentPlan(
        source_system_spec=spec.to_dict(),
        source_system_fingerprint=spec.fingerprint,
        request=request,
        mechanism_mappings=mappings,
        runs=runs,
        payload_sha256="",
    )
    seal = _sha256(provisional._payload_dict())
    plan = SealedSimulatorExperimentPlan(
        source_system_spec=provisional.source_system_spec,
        source_system_fingerprint=provisional.source_system_fingerprint,
        request=request,
        mechanism_mappings=mappings,
        runs=runs,
        payload_sha256=seal,
    )
    validate_simulator_experiment_plan(plan, dry_run=True)
    return plan


def validate_simulator_experiment_plan(
    plan: SealedSimulatorExperimentPlan,
    *,
    dry_run: bool = True,
) -> None:
    """Verify seal, provenance, exact recompilation, and optional CLI parsing."""

    if not re.fullmatch(r"[0-9a-f]{64}", plan.payload_sha256):
        raise SimulatorPlanValidationError("seal.payload_sha256 must be lowercase SHA-256")
    if _sha256(plan._payload_dict()) != plan.payload_sha256:
        raise SimulatorPlanValidationError("plan seal does not match payload")
    try:
        spec = SystemSpec.from_dict(plan.source_system_spec)
    except (KeyError, TypeError, ValueError) as error:
        raise SimulatorPlanValidationError("source SystemSpec cannot be parsed") from error
    if spec.to_dict() != plan.source_system_spec:
        raise SimulatorPlanValidationError(
            "source SystemSpec is not canonical or has unknown fields"
        )
    try:
        validate_system_spec(spec).require_valid()
        _validate_request(plan.request)
    except ValueError as error:
        raise SimulatorPlanValidationError(str(error)) from error
    if spec.fingerprint != plan.source_system_fingerprint:
        raise SimulatorPlanValidationError("source SystemSpec fingerprint mismatch")
    if (
        plan.source_system_spec["system_id"] != spec.system_id
        or plan.source_system_spec["version"] != spec.version
    ):
        raise SimulatorPlanValidationError("source SystemSpec identity mismatch")

    try:
        expected = _compile_system_spec_experiment_plan_unvalidated(spec, plan.request)
    except SimulatorPlanCompilationError as error:
        raise SimulatorPlanValidationError(str(error)) from error
    if plan.mechanism_mappings != expected.mechanism_mappings:
        raise SimulatorPlanValidationError("mechanism mapping differs from exact compiler output")
    if plan.runs != expected.runs:
        raise SimulatorPlanValidationError("run plan differs from exact compiler output")
    if dry_run:
        for run in plan.runs:
            _dry_run_validate(run, plan.request)


def _compile_system_spec_experiment_plan_unvalidated(
    spec: SystemSpec,
    request: SimulatorPlanRequest,
) -> SealedSimulatorExperimentPlan:
    """Internal exact recompilation without recursive public validation."""

    mappings = _compile_mechanism_mappings(spec, request.fidelity.num_years)
    runtime = spec.metadata.get("runtime")
    if not isinstance(runtime, Mapping):
        raise SimulatorPlanCompilationError("metadata.runtime must be an object")
    if set(runtime) != _RUNTIME_PARAMETERS:
        raise SimulatorPlanCompilationError("metadata.runtime has unsupported or missing keys")
    if spec.metadata.get("compiler") != LEGACY_ADAPTER:
        raise SimulatorPlanCompilationError("source SystemSpec adapter is unsupported")
    try:
        from utopia.communication.native import split_native_communication_system_spec
        base_spec, native_config = split_native_communication_system_spec(spec)
        legacy = compile_legacy_system(base_spec, years=request.fidelity.num_years)
    except (LegacyCompilationError, ValueError) as error:
        raise SimulatorPlanCompilationError(str(error)) from error
    cli_args = legacy.cli_args + _native_communication_args(native_config)
    _validate_mapping_arguments(mappings, cli_args)
    runs = tuple(
        _compile_run(spec, request, cli_args, seed) for seed in request.seeds
    )
    provisional = SealedSimulatorExperimentPlan(
        spec.to_dict(), spec.fingerprint, request, mappings, runs, ""
    )
    return SealedSimulatorExperimentPlan(
        spec.to_dict(), spec.fingerprint, request, mappings, runs,
        _sha256(provisional._payload_dict()),
    )


def _compile_mechanism_mappings(
    spec: SystemSpec,
    years: int,
) -> tuple[MechanismMapping, ...]:
    mappings: list[MechanismMapping] = []
    for mechanism in spec.mechanisms:
        contract = _IMPLEMENTATIONS.get(mechanism.implementation)
        if contract is None:
            raise SimulatorPlanCompilationError(
                "unsupported simulator mechanism: "
                f"{mechanism.mechanism_id} family={mechanism.family.value!r} "
                f"implementation={mechanism.implementation!r}"
            )
        if mechanism.family != contract.family:
            raise SimulatorPlanCompilationError(
                f"{mechanism.mechanism_id} family does not match implementation contract"
            )
        if mechanism.version != 1:
            raise SimulatorPlanCompilationError(
                f"{mechanism.mechanism_id} implementation version is unsupported"
            )
        expected = {name for name, _, _ in contract.parameters}
        actual = set(mechanism.parameters)
        if expected != actual:
            raise SimulatorPlanCompilationError(
                f"{mechanism.mechanism_id} parameters must map exactly; "
                f"missing={sorted(expected - actual)}, unsupported={sorted(actual - expected)}"
            )
        bindings = tuple(
            ParameterBinding(
                parameter=name,
                cli_flag=flag,
                encoding=encoding,
                value=(
                    [mechanism.parameters[name]] * years
                    if encoding == "repeat-per-year"
                    else mechanism.parameters[name]
                ),
            )
            for name, flag, encoding in contract.parameters
        )
        mapping_payload = {
            "mechanism_id": mechanism.mechanism_id,
            "family": mechanism.family.value,
            "implementation": mechanism.implementation,
            "implementation_version": mechanism.version,
            "execution_surface": contract.execution_surface,
            "parameter_bindings": [_binding_dict(item) for item in bindings],
        }
        mappings.append(
            MechanismMapping(
                mechanism.mechanism_id,
                mechanism.family.value,
                mechanism.implementation,
                mechanism.version,
                contract.execution_surface,
                bindings,
                _sha256(mapping_payload),
            )
        )
    return tuple(mappings)


def _validate_mapping_arguments(
    mappings: Sequence[MechanismMapping],
    argv: Sequence[str],
) -> None:
    """Prove every typed parameter binding agrees with the emitted CLI."""

    for mapping in mappings:
        for binding in mapping.parameter_bindings:
            flag = binding.cli_flag
            if flag is None:
                continue
            positions = [index for index, item in enumerate(argv) if item == flag]
            if binding.encoding == "optional-scalar" and binding.value is None:
                if positions:
                    raise SimulatorPlanCompilationError(
                        f"{mapping.mechanism_id}.{binding.parameter} unexpectedly emitted {flag}"
                    )
                continue
            if len(positions) != 1 or positions[0] + 1 >= len(argv):
                raise SimulatorPlanCompilationError(
                    f"{mapping.mechanism_id}.{binding.parameter} did not map exactly to {flag}"
                )
            if binding.encoding == "repeat-per-year":
                expected = ",".join(str(item) for item in binding.value)
            else:
                expected = str(binding.value)
            if argv[positions[0] + 1] != expected:
                raise SimulatorPlanCompilationError(
                    f"{mapping.mechanism_id}.{binding.parameter} value differs from {flag}"
                )


def _native_communication_args(config: Any) -> tuple[str, ...]:
    if config is None:
        return ()
    return (
        "--communication-broker-mode", config.mode,
        "--communication-digest-size", str(config.digest_size),
        "--communication-latency", str(config.latency),
        "--communication-receiver-role", config.receiver_role,
        "--communication-system-fingerprint", config.system_fingerprint,
    )


def _compile_run(
    spec: SystemSpec,
    request: SimulatorPlanRequest,
    legacy_args: Sequence[str],
    seed: int,
) -> SimulatorRunPlan:
    fidelity = request.fidelity
    run_id = f"{request.campaign_id}-{spec.fingerprint[:12]}-s{seed}"
    if not _SAFE_ID.fullmatch(run_id):
        raise SimulatorPlanCompilationError(f"compiled run id is unsafe: {run_id!r}")
    argv = [
        "--model", request.model.model,
        "--vllm_url", request.model.endpoint,
        "--api-backend", request.model.api_backend,
        "--batch_size", str(request.model.batch_size),
        "--experiment_stage", fidelity.experiment_stage,
        "--run-id", run_id,
        "--output-dir", request.output_root,
        "--data-cache-dir", request.data_cache_dir,
        "--dataset-revision", request.model.dataset_revision,
        "--seed", str(seed),
        "--num_years", str(fidelity.num_years),
        "--num_institutions", str(fidelity.num_institutions),
        "--num_conferences", str(fidelity.num_conferences),
    ]
    if request.model.model_revision is not None:
        argv.extend(["--model_revision", request.model.model_revision])
    argv.extend(legacy_args)
    encoded = tuple(argv)
    return SimulatorRunPlan(run_id, seed, encoded, _sha256(list(encoded)))


def _dry_run_validate(run: SimulatorRunPlan, request: SimulatorPlanRequest) -> None:
    if _sha256(list(run.simulator_argv)) != run.argv_sha256:
        raise SimulatorPlanValidationError(f"argv hash mismatch for {run.run_id}")
    try:
        parsed = parse_arguments(list(run.simulator_argv), create_dirs=False)
    except (SystemExit, ValueError, AssertionError) as error:
        raise SimulatorPlanValidationError(
            f"simulator rejected dry-run arguments for {run.run_id}"
        ) from error
    fidelity = request.fidelity
    expected = {
        "run_id": run.run_id,
        "seed": run.seed,
        "model": request.model.model,
        "api_backend": request.model.api_backend,
        "vllm_url": request.model.endpoint,
        "batch_size": request.model.batch_size,
        "experiment_stage": fidelity.experiment_stage,
        "num_years": fidelity.num_years,
        "num_institutions": fidelity.num_institutions,
        "num_conferences": fidelity.num_conferences,
        "dataset_revision": request.model.dataset_revision,
    }
    for field, value in expected.items():
        if getattr(parsed, field) != value:
            raise SimulatorPlanValidationError(
                f"dry-run parser changed {field} for {run.run_id}"
            )


def _validate_request(request: SimulatorPlanRequest) -> None:
    if not _SAFE_ID.fullmatch(request.campaign_id):
        raise SimulatorPlanCompilationError("campaign_id must be a safe run identifier")
    if not request.seed_role or not isinstance(request.seed_role, str):
        raise SimulatorPlanCompilationError("seed_role must be non-empty")
    if (
        not request.seeds
        or any(type(seed) is not int for seed in request.seeds)
        or len(set(request.seeds)) != len(request.seeds)
    ):
        raise SimulatorPlanCompilationError("seeds must contain unique integers")
    model = request.model
    if not all(isinstance(value, str) and value for value in (model.model, model.endpoint)):
        raise SimulatorPlanCompilationError("model and endpoint must be non-empty")
    if model.api_backend not in {"ollama", "vllm"}:
        raise SimulatorPlanCompilationError("api_backend must be ollama or vllm")
    if type(model.batch_size) is not int or model.batch_size < 1:
        raise SimulatorPlanCompilationError("batch_size must be positive")
    if model.model_revision is not None and not model.model_revision:
        raise SimulatorPlanCompilationError("model_revision cannot be empty")
    if not isinstance(model.dataset_revision, str) or not model.dataset_revision:
        raise SimulatorPlanCompilationError("dataset_revision must be non-empty")
    fidelity = request.fidelity
    if not fidelity.fidelity_id:
        raise SimulatorPlanCompilationError("fidelity_id must be non-empty")
    if fidelity.experiment_stage not in {
        "smoke", "pilot", "scalecheck", "calibration", "confirmatory",
        "manyworld", "mechanism", "funding_cutoff", "funding_cutoff_cost", "scale",
    }:
        raise SimulatorPlanCompilationError("unsupported experiment_stage")
    for name in ("num_years", "num_institutions", "num_conferences"):
        value = getattr(fidelity, name)
        if type(value) is not int or value < 1:
            raise SimulatorPlanCompilationError(f"{name} must be positive")
    for name in ("output_root", "data_cache_dir", "source_locator"):
        value = getattr(request, name)
        if not isinstance(value, str) or not value:
            raise SimulatorPlanCompilationError(f"{name} must be non-empty")
    if not _COMMIT.fullmatch(request.compiler_source_commit):
        raise SimulatorPlanCompilationError(
            "compiler_source_commit must be a lowercase 40-character commit"
        )
    if type(request.compiler_tree_dirty) is not bool:
        raise SimulatorPlanCompilationError("compiler_tree_dirty must be boolean")
    if request.compiler_tree_dirty:
        raise SimulatorPlanCompilationError("sealed campaign plans require a clean compiler tree")


def _request_dict(request: SimulatorPlanRequest) -> dict[str, Any]:
    return {
        "campaign_id": request.campaign_id,
        "seed_role": request.seed_role,
        "seeds": list(request.seeds),
        "model": asdict(request.model),
        "fidelity": asdict(request.fidelity),
        "output_root": request.output_root,
        "data_cache_dir": request.data_cache_dir,
        "provenance": {
            "compiler_source_commit": request.compiler_source_commit,
            "compiler_tree_dirty": request.compiler_tree_dirty,
            "source_locator": request.source_locator,
        },
    }


def _request_from_dict(value: Mapping[str, Any]) -> SimulatorPlanRequest:
    _exact_keys(
        value,
        {
            "campaign_id", "seed_role", "seeds", "model", "fidelity",
            "output_root", "data_cache_dir", "provenance",
        },
        "campaign",
    )
    model = _object(value["model"], "campaign.model")
    _exact_keys(
        model,
        {"model", "api_backend", "endpoint", "batch_size", "model_revision", "dataset_revision"},
        "campaign.model",
    )
    fidelity = _object(value["fidelity"], "campaign.fidelity")
    _exact_keys(
        fidelity,
        {"fidelity_id", "experiment_stage", "num_years", "num_institutions", "num_conferences"},
        "campaign.fidelity",
    )
    provenance = _object(value["provenance"], "campaign.provenance")
    _exact_keys(
        provenance,
        {"compiler_source_commit", "compiler_tree_dirty", "source_locator"},
        "campaign.provenance",
    )
    return SimulatorPlanRequest(
        campaign_id=_string(value["campaign_id"], "campaign.campaign_id"),
        seed_role=_string(value["seed_role"], "campaign.seed_role"),
        seeds=tuple(_sequence(value["seeds"], "campaign.seeds")),
        model=SimulatorModelSpec(**model),
        fidelity=SimulatorFidelitySpec(**fidelity),
        output_root=_string(value["output_root"], "campaign.output_root"),
        data_cache_dir=_string(value["data_cache_dir"], "campaign.data_cache_dir"),
        compiler_source_commit=_string(
            provenance["compiler_source_commit"],
            "campaign.provenance.compiler_source_commit",
        ),
        compiler_tree_dirty=provenance["compiler_tree_dirty"],
        source_locator=_string(
            provenance["source_locator"], "campaign.provenance.source_locator"
        ),
    )


def _binding_dict(binding: ParameterBinding) -> dict[str, Any]:
    return {
        "parameter": binding.parameter,
        "cli_flag": binding.cli_flag,
        "encoding": binding.encoding,
        "value": _json_value(binding.value),
    }


def _mechanism_mapping_dict(mapping: MechanismMapping) -> dict[str, Any]:
    return {
        "mechanism_id": mapping.mechanism_id,
        "family": mapping.family,
        "implementation": mapping.implementation,
        "implementation_version": mapping.implementation_version,
        "execution_surface": mapping.execution_surface,
        "parameter_bindings": [_binding_dict(item) for item in mapping.parameter_bindings],
        "mapping_sha256": mapping.mapping_sha256,
    }


def _mechanism_mapping_from_dict(value: Mapping[str, Any]) -> MechanismMapping:
    _exact_keys(
        value,
        {
            "mechanism_id", "family", "implementation", "implementation_version",
            "execution_surface", "parameter_bindings", "mapping_sha256",
        },
        "mechanism_mapping",
    )
    bindings = _sequence(value["parameter_bindings"], "parameter_bindings")
    parsed: list[ParameterBinding] = []
    for index, item in enumerate(bindings):
        binding = _object(item, f"parameter_bindings[{index}]")
        _exact_keys(binding, {"parameter", "cli_flag", "encoding", "value"}, "binding")
        if binding["cli_flag"] is not None and not isinstance(binding["cli_flag"], str):
            raise SimulatorPlanValidationError("binding.cli_flag must be string or null")
        parsed.append(ParameterBinding(**binding))
    return MechanismMapping(
        mechanism_id=_string(value["mechanism_id"], "mechanism_id"),
        family=_string(value["family"], "family"),
        implementation=_string(value["implementation"], "implementation"),
        implementation_version=value["implementation_version"],
        execution_surface=_string(value["execution_surface"], "execution_surface"),
        parameter_bindings=tuple(parsed),
        mapping_sha256=_string(value["mapping_sha256"], "mapping_sha256"),
    )


def _run_dict(run: SimulatorRunPlan) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "seed": run.seed,
        "simulator_argv": list(run.simulator_argv),
        "argv_sha256": run.argv_sha256,
    }


def _run_from_dict(value: Mapping[str, Any]) -> SimulatorRunPlan:
    _exact_keys(value, {"run_id", "seed", "simulator_argv", "argv_sha256"}, "run")
    argv = _sequence(value["simulator_argv"], "run.simulator_argv")
    if any(not isinstance(item, str) for item in argv):
        raise SimulatorPlanValidationError("run.simulator_argv must contain strings")
    return SimulatorRunPlan(
        _string(value["run_id"], "run.run_id"),
        value["seed"],
        tuple(argv),
        _string(value["argv_sha256"], "run.argv_sha256"),
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _json_value(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    if actual != expected:
        raise SimulatorPlanValidationError(
            f"{path} keys differ: missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SimulatorPlanValidationError(f"{path} must be an object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise SimulatorPlanValidationError(f"{path} must be an array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise SimulatorPlanValidationError(f"{path} must be a non-empty string")
    return value
