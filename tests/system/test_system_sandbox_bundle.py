import copy
import hashlib
import json

from utopia.system import SystemSpec, validate_system_spec
from utopia.system.sandbox import SANDBOX_SCHEMA_VERSION, build_system_sandbox_bundle


def test_system_sandbox_bundle_is_synthetic_and_python_authoritative() -> None:
    bundle = build_system_sandbox_bundle()
    assert bundle["schema_version"] == SANDBOX_SCHEMA_VERSION
    assert bundle["truth_status"] == "synthetic"
    assert bundle["source_kind"] == "synthetic_system_design_sandbox"
    assert "No simulation has run" in bundle["disclosure"]
    assert {node["mechanism_id"] for node in bundle["node_catalog"]} == {
        "evaluation", "publication", "funding", "government", "communication",
    }
    assert len(bundle["edge_catalog"]) == 6

    base = bundle["authoritative_fixtures"][0]
    spec = SystemSpec.from_dict(base["spec"])
    assert validate_system_spec(spec).valid
    assert base["fingerprint"] == spec.fingerprint
    assert base["validation"] == {"valid": True, "issues": []}

    invalid = bundle["authoritative_fixtures"][1]
    report = validate_system_spec(SystemSpec.from_dict(invalid["spec"]))
    assert not report.valid
    assert "unconnected_required_input" in {issue.code for issue in report.errors}
    assert invalid["validation"]["valid"] is False

    claimed_hash = bundle["bundle_hash"]
    unhashed = copy.deepcopy(bundle)
    del unhashed["bundle_hash"]
    canonical = json.dumps(unhashed, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    assert hashlib.sha256(canonical.encode()).hexdigest() == claimed_hash
