"""Fresh-file, numeric-type-preserving preflight for external design authors.

No inbox is consumed, file is written, authored source executed, model called or
native world run. This is optional author tooling, never an automatic rebase or
repair in the experiment runner. Imports resolve against the caller's source pin.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path

from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.optimization.native_factorized_gradient import NativeFactorizedDesignSearch
from utopia.optimization.native_manifest_inbox import SCHEMA
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import validate_code_artifact
from utopia.system.design_patch import apply_design_patch, digest
from utopia.system.native_migration import native_execution_nodes
from utopia.utils.data_utils import decode_json


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_097_152:
        raise ValueError('author validation requires bounded regular JSON files')
    raw = path.read_bytes()
    # Python's decoder preserves 1.0 as float and 1 as int. Do not round-trip via
    # JavaScript or normalize numbers: canonical identities distinguish them.
    value = decode_json(raw.decode('utf-8'), strict=True, finite_floats=True)
    return path, raw, value


def _sources(system):
    result = {}
    for node in native_execution_nodes(system):
        if node.implementation == 'code.python.v1':
            artifact = node.parameters['code_artifact']
            validate_code_artifact(artifact)
            ast.parse(artifact['source'])  # Parse only. Never exec/import source.
            if (set(artifact['inputs']) != {p.port_id for p in node.inputs}
                    or set(artifact['outputs']) != {p.port_id for p in node.outputs}):
                raise ValueError('authored source payload-schema keys differ from its actual ports')
            result[node.mechanism_id] = hashlib.sha256(artifact['source'].encode()).hexdigest()
    return result


def validate_saved_generated_response(request_path, response_path, *, learning_rate=.1):
    """Validate EXACT saved files with actual frozen loss, seed and draw count.

    A wrong parent raises, never gets rebound. All conditional reachable factor
    assignments compile, then exactly the declared count of in-memory design
    draws are checked (no replacements). Numeric/runtime scientific effects are
    NOT measured. Draw-time technical failures are reported with null loss and
    a non-passing status. Unknown generator-source probabilities are not inferred.
    """
    request_path, request_raw, envelope = _read(request_path)
    response_path, response_raw, response = _read(response_path)
    identity = digest(envelope)
    if envelope.get('schema') != SCHEMA or request_path.stem != identity:
        raise ValueError('exact saved external request identity/schema mismatch')
    if (set(response) != {'request_sha256', 'manifest', 'authoring'}
            or response['request_sha256'] != identity or response_path.stem != identity
            or not isinstance(response['authoring'], dict)
            or response['authoring'].get('kind') not in {'codex-agent', 'external'}):
        raise ValueError('exact saved response identity/authoring mismatch')
    request = envelope['request']['authoring_input']
    definition = response['manifest']
    parent = SystemSpec.from_dict(request['parent_system'])
    mixed = GeneratedMixedDesign(parent, definition, loss_spec=request['loss_spec'],
        seed=request['rng_seed'], learning_rate=learning_rate)
    assignments = mixed.policy.assignments if mixed.policy else [{}]
    combinations = []
    for assignment in assignments:
        system = mixed.policy.compile_assignment(assignment)[0] if mixed.policy else mixed.base
        combinations.append({'assignment': assignment, 'fingerprint': system.fingerprint,
            'nodes': len(system.mechanisms), 'edges': len(system.connections),
            'source_utf8_sha256': _sources(system)})
    version = digest({'request': digest(request), 'definition': definition})
    draws = mixed.draw(request['count'], version_sha256=version,
        proposal_start=sum(len(r['draws']) for r in request['history']),
        based_on=request['based_on_observation_id'])
    summaries = []
    for draw in draws:
        system = (SystemSpec.from_dict(draw['suggestion']['candidate'])
                  if draw['suggestion'] is not None else None)
        summaries.append({'assignment': draw['assignment'], 'latent': draw['latent'],
            'conditional_latent_log_probability': draw['conditional_latent_log_probability'],
            'continuous_operations': draw['continuous_operations'],
            'suggestion_id': draw['suggestion']['suggestion_id'] if system else None,
            'candidate_fingerprint': system.fingerprint if system else None,
            'source_utf8_sha256': _sources(system) if system else None,
            'technical_error': draw['technical_error'], 'loss': None})
    # Detect either file changing during preflight, rather than blessing an old
    # in-memory object while a different response is consumed later.
    if request_path.read_bytes() != request_raw or response_path.read_bytes() != response_raw:
        raise ValueError('external authoring file changed during fresh-file validation')
    files = {}
    for obj in (GeneratedMixedDesign, NativeFactorizedDesignSearch, SystemSpec,
                apply_design_patch, native_execution_nodes, validate_code_artifact):
        path = Path(inspect.getfile(obj)).resolve()
        files[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'schema': 'scienceutopia.saved-external-design-validation.v1',
        'status': 'passed' if all(d['technical_error'] is None for d in summaries) else 'invalid-drawn-design',
        'request_file_sha256': hashlib.sha256(request_raw).hexdigest(),
        'response_file_sha256': hashlib.sha256(response_raw).hexdigest(),
        'request_sha256': identity, 'response_sha256': digest(response),
        'manifest_sha256': digest(definition), 'parent_fingerprint': parent.fingerprint,
        'loss_spec_sha256': digest(request['loss_spec']), 'rng_seed': request['rng_seed'],
        'declared_draw_count': request['count'], 'learning_rate': learning_rate,
        'version_sha256': version, 'reachable_assignments': combinations, 'draws': summaries,
        'compiler_files_sha256': files,
        'scope': 'exact saved request/response numeric-type-preserving structural/source-syntax preflight; no source/native execution or scientific loss',
        'calls': {'authored_source': 0, 'native_world': 0, 'model': 0, 'docker': 0},
        'inbox_consumed': False, 'files_written': False, 'parent_rebased': False}
