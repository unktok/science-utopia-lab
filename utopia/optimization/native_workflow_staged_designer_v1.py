"""Explicit staged construction profile for the original open workflow.

Reuse the literal editor and bounded public worker; do not reinterpret prose,
repair code, change losses or replace a missing submission by the parent.
"""
from pathlib import Path
import json
from types import SimpleNamespace

from . import native_bounded_staged_designer as bounded
from .native_designer_preflight import require_certificate, EXECUTION_SCOPE
from .native_designer_roles_v38 import validate_designer_binding
from .native_designer_tools_v25 import BOUNDED_AUTHORING
from .native_numeric_designer import checked, save
from .native_post_edit_feedback_v1 import NativePostEditFeedback, OPTION
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

MODE = 'open-institutions-staged-tests-v1'
PROTOCOL = 'research/protocols/campaigns/native-open-workflow-staged-construction-v1.md'
SCHEMA = 'scienceutopia.local-staged-workflow-designer.v1'
ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return checked(json.loads(Path(path).read_text()))


def settings():
    return {'profile': MODE, 'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'conversation_profile': BOUNDED_AUTHORING, 'max_steps': 16, 'max_tokens': 8192,
        'proposal_maximum_posts': 16, 'calibration_maximum_posts': 40,
        'session_wall_seconds': 1800, 'maximum_component_probes': 64,
        'component_timeout_seconds': 15., 'source_repair': False, 'failure_veto_on_finish': False}


def require_bank(bank, evidence, anchor):
    """Reconstruct original native attribution, not just a self-hashed bank."""
    from scripts.reports.stage_native_component_fixtures_v1 import collect, WORKFLOW_SCOPE, TOPIC_SCOPE
    checked(bank)
    scope = evidence.get('staging_scope', WORKFLOW_SCOPE)
    expected_keys = {'run','source','audit','audit_file_sha256'}
    if 'staging_scope' in evidence:
        expected_keys.add('staging_scope')
        if scope != TOPIC_SCOPE:
            raise ValueError('explicit same-authority topic component staging scope required')
    if (set(evidence) != expected_keys
            or file_sha256(evidence['audit']) != evidence['audit_file_sha256']):
        raise ValueError('exact original component audit/source/run evidence required')
    original = collect(evidence['run'], evidence['audit'], scope=scope, source_root=evidence['source'])
    if bank != {**original, 'content_sha256': digest(original)}:
        raise ValueError('workflow component bank differs from original audited R7 inputs')
    spec = SystemSpec.from_dict(anchor)
    if {r['binding']['system_fingerprint'] for r in bank['records']} != {spec.fingerprint}:
        raise ValueError('workflow component fixtures are not the exact original R7 anchor')
    return clone(bank)


def component_feedback(bank, provider, source):
    # Contract reconstruction must not inspect Docker or execute source. The
    # actual bounded worker independently creates its real Docker executor.
    def forbidden(*args, **kwargs):
        raise AssertionError('workflow contract reconstruction cannot execute code')
    return NativePostEditFeedback(bank,
        executor=SimpleNamespace(image_id=provider['image_id'], timeout=settings()['component_timeout_seconds'], execute=forbidden),
        source_commit=source, maximum_probes=settings()['maximum_component_probes'])


def cold_certificate(path, *, request, provider, backend, contract):
    """No network or execution: reconstruct the certificate's recorded metadata."""
    cert = read(path)
    class Reply:
        def __init__(self, value): self.value = value
        def raise_for_status(self): pass
        def json(self): return self.value
    class RecordedBackend:
        def get(self, url, timeout):
            if url.endswith('/api/version'): return Reply({'version': backend['ollama_version']})
            if url.endswith('/api/tags'):
                return Reply({'models': [{'name': provider['model'], 'digest': provider['model_digest']}]})
            raise ValueError('offline staged workflow metadata cannot dispatch')
    proof = require_certificate(path, provider, protocol='staged-v15', session=RecordedBackend(),
        now=cert['completed_epoch'], scope=EXECUTION_SCOPE, conversation_profile=BOUNDED_AUTHORING)
    if (cert['plan']['request'] != request or cert['plan']['backend'] != backend
            or proof.get(OPTION) != contract):
        raise ValueError('staged workflow certificate request/backend/component contract differs')
    return cert


def replay(directory, *, request, provider, backend, source_commit, bank, purpose):
    root = Path(directory)
    binding, result = read(root/'binding.json'), read(root/'result.json')
    expected = {'schema': SCHEMA+'.binding', 'request': clone(request), 'provider': clone(provider),
        'backend': clone(backend), 'source_commit': source_commit, 'settings': settings(),
        'purpose': purpose, 'component_bank_sha256': bank['content_sha256']}
    if binding != {**expected, 'content_sha256': digest(expected)} or result['binding_sha256'] != binding['content_sha256']:
        raise ValueError('staged workflow binding/result differs from declared request/profile')
    session = root/('editor-readiness' if purpose=='calibration' else 'editor-session')
    value = bounded.replay(session)
    if digest(value) != result['public_return_sha256']:
        raise ValueError('staged workflow public bounded return differs')
    intent = read(session/'intent.json')
    expected_intent = {'kind': purpose, 'request': request, 'provider': provider, 'source_commit': source_commit,
        'seconds': settings()['session_wall_seconds'],
        'maximum_posts': settings()['calibration_maximum_posts' if purpose=='calibration' else 'proposal_maximum_posts'],
        'max_steps': settings()['max_steps'], 'max_tokens': settings()['max_tokens'],
        'conversation_profile': BOUNDED_AUTHORING}
    if any(intent.get(k) != v for k,v in expected_intent.items()):
        raise ValueError('staged workflow actual worker settings differ')
    if purpose == 'proposal':
        if intent.get('post_edit_component_bank') != bank:
            raise ValueError('staged workflow worker bank differs')
        expected_definition = value if value is not None else missing_definition(request)
        if result['definition'] != expected_definition:
            raise ValueError('staged workflow literal definition differs')
    elif purpose == 'calibration':
        if value.get('passed') is not True or result['definition'] is not None:
            raise ValueError('staged workflow readiness is not a passed directed control')
    else:
        raise ValueError('explicit staged workflow purpose required')
    if result['completion_unknown'] is not False:
        raise ValueError('closed staged workflow return cannot conceal unknown completion')
    return result


def missing_definition(request):
    return {'generation_failure': {'schema': SCHEMA+'.no-submission', 'request_sha256': digest(request),
        'reason': 'Finite staged session ended without an explicit valid submission; no fallback or refill'}}


class StagedWorkflowDesigner:
    def __init__(self, directory, *, provider, backend, inference_lock, source_commit, bank):
        validate_designer_binding(provider)
        if any(backend.get(k) != provider[k] for k in ('model','model_digest')):
            raise ValueError('staged workflow backend/model differs')
        self.directory, self.lock = Path(directory), Path(inference_lock)
        self.provider, self.backend, self.bank = clone(provider), clone(backend), clone(bank)
        self.source = source_commit
        self.feedback = component_feedback(bank, provider, source_commit)

    def execute(self, request, *, purpose, certificate=None):
        from .native_open_workflow_submission_v1 import bound_systems
        bound_systems(request)
        if (request.get('strategy_provenance') or {}).get(OPTION) != self.feedback.contract:
            raise ValueError('campaign request must already declare exact staged component contract')
        if purpose not in ('calibration','proposal'):
            raise ValueError('explicit staged workflow purpose required')
        root = self.directory/(purpose+'-'+digest(request))
        root.mkdir(parents=True, exist_ok=True)
        if (root/'binding.json').exists():
            return replay(root, request=request, provider=self.provider, backend=self.backend,
                source_commit=self.source, bank=self.bank, purpose=purpose)
        binding = save(root/'binding.json', {'schema': SCHEMA+'.binding', 'request': clone(request),
            'provider': self.provider, 'backend': self.backend, 'source_commit': self.source,
            'settings': settings(), 'purpose': purpose, 'component_bank_sha256': self.bank['content_sha256']})
        session = root/('editor-readiness' if purpose=='calibration' else 'editor-session')
        value = bounded.execute(session, kind=purpose, request=request, provider=self.provider,
            source_commit=self.source, certificate=certificate, inference_lock=self.lock,
            seconds=settings()['session_wall_seconds'],
            maximum_posts=settings()['calibration_maximum_posts' if purpose=='calibration' else 'proposal_maximum_posts'],
            **({'post_edit_bank': self.bank} if purpose=='proposal' else {}))
        definition = (value if value is not None else missing_definition(request)) if purpose=='proposal' else None
        save(root/'result.json', {'schema': SCHEMA+'.result', 'binding_sha256': binding['content_sha256'],
            'public_return_sha256': digest(value), 'definition': definition, 'completion_unknown': False})
        return replay(root, request=request, provider=self.provider, backend=self.backend,
            source_commit=self.source, bank=self.bank, purpose=purpose)

    def calibrate(self, request):
        self.execute(request, purpose='calibration')
        path = self.directory/('calibration-'+digest(request))/'editor-readiness/calibration/certificate.json'
        cold_certificate(path, request=request, provider=self.provider, backend=self.backend, contract=self.feedback.contract)
        return path
