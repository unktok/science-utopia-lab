"""V10 historical data reuse and explicitly source-equivalent online response fit.

Old endpoint source identities are never rewritten. Existing v9/native modules
stay untouched; the strict same-source fitter retains its original default.
"""
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import subprocess

import torch

from utopia.system.design_patch import digest
from utopia.system.native_response_examples import DECLARATIONS, TERMS
from utopia.utils.data_utils import decode_json, file_sha256
from .native_qwen_response import require_same_control
from .native_response_fidelity import (NativeResponseOperator, BoundaryUnsupported,
    binding, boundary_layout, raw_review_projection, verify_endpoint, DTYPE)

SCHEMA = 'scienceutopia.native-method-paths.v10'
ACTUAL = 'actual-native-qwen-method-paths-development-v10'
HISTORICAL_SOURCE = 'fb2d1b6f07aadba39148bd5871dac2fd0595b618'
HISTORICAL_CLASSIFICATION = 'actual-native-qwen-response-gradient-development-v9'
HISTORICAL_AUDIT = '92d6a9b630d9bcd44e379ec48833aed2de71490b85907068fed740361826abbf'
EXPERIMENT = {'protocol': 'native-method-paths-v10', 'role': 'development-engineering',
    'review_task_identity_recording': True, 'public_payload_only_review_context': True}
GRADIENT_RULE = {'learning_rate': .5, 'trust_radius': .1,
    'temperature_schedule': [1., .2, .05]}
SCHEDULE = [{'arm': arm, 'step': step, 'name': f'{arm}-{step}'}
    for step in range(3) for arm in ('gradient', 'blackbox')]


def read(path):
    value = decode_json(Path(path).read_text(), strict=True, finite_floats=True)
    if 'content_sha256' in value and value['content_sha256'] != digest(
            {k: v for k, v in value.items() if k != 'content_sha256'}):
        raise ValueError('content hash differs: '+str(path))
    return value


def load_shared_historical(audit_path):
    """Only the committed, previously independently audited v9 calibration."""
    path = Path(audit_path).resolve()
    report = read(path)
    if (report.get('content_sha256') != HISTORICAL_AUDIT
            or report.get('schema') != 'scienceutopia.native-qwen-response-audit.v9'
            or report.get('classification') != HISTORICAL_CLASSIFICATION
            or report.get('source_commit') != HISTORICAL_SOURCE
            or report.get('status') != 'complete'):
        raise ValueError('exact source-bound actual v9 audit required')
    raw_root = Path(report['raw_output_root']).resolve()
    paths = list(raw_root.rglob('*'))
    if any(p.is_symlink() for p in paths) or {str(p.relative_to(raw_root)) for p in paths if p.is_file()} != set(report['raw_hashes']['files']):
        raise ValueError('historical raw inventory coverage differs')
    for relative, entry in report['raw_hashes']['files'].items():
        target = raw_root / relative
        if (target.is_symlink() or not target.is_file()
                or file_sha256(target) != entry['sha256'] or target.stat().st_size != entry['bytes']):
            raise ValueError('historical raw inventory changed')
    raw = read(raw_root/'evidence.json')
    if (file_sha256(raw_root/'evidence.json') != report['raw_hashes']['evidence_file_sha256']
            or raw['content_sha256'] != report['raw_hashes']['evidence_content_sha256']):
        raise ValueError('historical evidence bytes differ from the committed audit')
    rows = raw['endpoints'][:3]
    if ([r['name'] for r in rows] != ['calibration-0', 'calibration-1', 'calibration-2']
            or [r['theta'] for r in rows] != [.2, .5, .8]
            or [r['endpoint']['checkpoint_sha256'] for r in rows] !=
                [r['checkpoint_sha256'] for r in report['endpoints'][:3]]):
        raise ValueError('exact historical calibration identities differ')
    return {'audit_path': str(path), 'audit_file_sha256': file_sha256(path),
        'audit_content_sha256': report['content_sha256'], 'source_commit': HISTORICAL_SOURCE,
        'raw_root': str(raw_root), 'raw_inventory_sha256': report['raw_hashes']['inventory_sha256'],
        'raw_file_count': report['raw_hashes']['file_count'], 'rows': rows,
        'anchor_world_dir': raw['plan']['response_coupling']['prepared']['anchor_world_dir'],
        'anchor_endpoint': raw['plan']['response_coupling']['prepared']['anchor_endpoint'],
        'historical_observations_charged_per_arm': 3,
        'historical_calibration_fresh_calls': sum(r['fresh_physical_replies'] for r in rows),
        'unique_anchor_origin_calls': report['response_coupling']['unique_anchor_prefix_calls']}


def historical_observations(shared):
    return [{'theta': row['theta'], 'loss': row['endpoint']['native_loss'],
        'provenance': {'historical_name': row['name'],
            'endpoint_record_sha256': digest(row['endpoint']),
            'checkpoint_sha256': row['endpoint']['checkpoint_sha256'],
            'source_commit': row['endpoint']['world']['source_commit'],
            'audit_content_sha256': shared['audit_content_sha256']}}
        for row in shared['rows']]


def runtime_source_equivalence(source_root, sources):
    """Compare every original utopia blob; new optimizer files may be additions."""
    root = Path(source_root)
    manifests = {}
    for source in sorted(set(sources)):
        lines = subprocess.check_output(['git', 'ls-tree', '-r', source, '--', 'utopia/'],
            cwd=root, text=True).splitlines()
        if not lines:
            raise ValueError('source contains no original runtime files')
        files = {}
        for line in lines:
            metadata, relative = line.split('\t', 1)
            mode, kind, expected = metadata.split()
            path = root/relative
            if kind != 'blob' or mode not in ('100644', '100755') or path.is_symlink() or not path.is_file():
                raise ValueError('original runtime file absent or not an ordinary blob')
            data = path.read_bytes()
            actual = hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
            if actual != expected:
                raise ValueError('historical/current original runtime differs: '+relative)
            files[relative] = hashlib.sha256(data).hexdigest()
        manifests[source] = {'file_count': len(files), 'files_sha256': files,
            'manifest_sha256': digest(files)}
    return {'rule': 'Every pre-existing utopia/ blob is byte-identical; new v10 files are explicit additions.',
        'sources': manifests, 'world_metadata_exceptions':
            ['source_commit', 'classification', 'experiment.protocol']}


def _scientific_binding(endpoint):
    value = deepcopy(binding(endpoint))
    world = value['world']
    source = world.pop('source_commit')
    classification = world.pop('classification')
    protocol = world['experiment'].pop('protocol')
    if classification == HISTORICAL_CLASSIFICATION:
        if (source != HISTORICAL_SOURCE or protocol != 'native-qwen-response-gradient-v9'):
            raise ValueError('historical metadata differs from exact original campaign')
    elif classification != ACTUAL or protocol != EXPERIMENT['protocol']:
        raise ValueError('new endpoint metadata is not the declared v10 campaign')
    return value


def fit_path_operator(rows, objective, temperature, source_root):
    """Refit original raw-response equations without pretending sources match.

    The template and every saved endpoint retain their original source. This
    explicit v10 bridge allows ONLY campaign-metadata differences, after actual
    endpoint/control checks and a complete old-runtime source-byte comparison.
    """
    if len(rows) < 3 or [r['theta'] for r in rows[:3]] != [.2, .5, .8]:
        raise ValueError('shared historical calibration must precede online observations')
    endpoints = [r['endpoint'] for r in rows]
    if len({p['checkpoint_sha256'] for p in endpoints}) != len(endpoints):
        raise ValueError('duplicate physical calibration endpoint')
    bridge = runtime_source_equivalence(source_root, [p['world']['source_commit'] for p in endpoints])
    require_same_control([r['control_proof'] for r in rows])
    first = _scientific_binding(endpoints[0])
    if any(_scientific_binding(p) != first for p in endpoints):
        raise ValueError('source bridge cannot change scientific native bindings')
    evidence = {r['endpoint']['checkpoint_sha256']: r['numeric_response_evidence'] for r in rows}
    # Reuse strict original fit for the same-source initial three points. It
    # supplies unchanged parser/program/template semantics, not remapped sources.
    base = NativeResponseOperator.fit(endpoints[:3], DECLARATIONS, objective, TERMS,
        temperatures=[temperature], numeric_response_evidence={p['checkpoint_sha256']:
            evidence[p['checkpoint_sha256']] for p in endpoints[:3]})
    raw_values, projections = [], []
    for endpoint in endpoints:
        verify_endpoint(endpoint, DECLARATIONS, objective)
        layout, numeric, signature = boundary_layout(endpoint)
        if signature != base.state['layout_sha256']:
            raise BoundaryUnsupported('online native record shape/routing changed; no padding')
        raw, projection = raw_review_projection(endpoint, layout, numeric,
            **evidence[endpoint['checkpoint_sha256']])
        if {k: projection[k] for k in ('kind', 'indices', 'contract')} != {
                k: base.state['projection'][k] for k in ('kind', 'indices', 'contract')}:
            raise BoundaryUnsupported('online raw parser correspondence changed')
        raw_values.append(raw)
        projections.append(projection)
    controls = torch.tensor([[p['coordinate_values']['evidence-weight']] for p in endpoints], dtype=DTYPE)
    center = controls.mean(0)
    design = torch.cat((controls.new_ones(len(endpoints), 1), controls-center), 1)
    targets = torch.stack(raw_values)
    weights = torch.linalg.lstsq(design, targets, driver='gelsd').solution
    state = deepcopy(base.state)
    state.update(calibration=deepcopy(endpoints), center=center.tolist(), weights=weights.tolist(),
        calibration_controls=controls.tolist(), numeric_response_evidence=deepcopy(evidence),
        raw_response_proofs=projections, raw_fit_rmse=float((design@weights-targets).square().mean().sqrt()),
        source_equivalence=bridge, temperature_selection=None)
    operator = NativeResponseOperator(state)
    predicted = [float(operator.value(c)[0].detach()) for c in controls]
    errors = [value-p['native_loss'] for value, p in zip(predicted, endpoints)]
    state['temperature_selection'] = {'rule': 'single preregistered continuation temperature; no outcome-based choice',
        'candidates': [{'temperature': temperature, 'native_calibration_losses': [p['native_loss'] for p in endpoints],
            'predicted_calibration_losses': predicted, 'rmse': math.sqrt(math.fsum(e*e for e in errors)/len(errors))}],
        'selected_index': 0, 'calibration_checkpoint_sha256s': [p['checkpoint_sha256'] for p in endpoints],
        'unused_endpoints_seen': 0}
    return NativeResponseOperator(state)
