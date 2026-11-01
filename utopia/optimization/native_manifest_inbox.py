"""Hash-bound file inbox implementing the designer model's generate interface.

It makes no network/model calls and executes no manifest source. Author metadata
is a recorded external claim, not authenticated proof of provider identity.
"""
from __future__ import annotations

import json
from pathlib import Path

from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import clone
from utopia.utils.data_utils import write_json_atomic

SCHEMA = 'scienceutopia.external-manifest-request.v5'


class ExternalAuthoringPending(RuntimeError):
    def __init__(self, request_sha256, request_path, response_path):
        self.request_sha256 = request_sha256
        self.request_path, self.response_path = Path(request_path), Path(response_path)
        super().__init__('external authoring pending for request ' + request_sha256)

    def to_dict(self):
        return {'status': 'external-authoring-pending', 'request_sha256': self.request_sha256,
            'request_path': str(self.request_path), 'response_path': str(self.response_path),
            'loss': None, 'technical_failure': False}


class ManifestInbox:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.verify_consumed()

    def _path(self, section, digest):
        return self.directory / section / (digest + '.json')

    @staticmethod
    def _read(path):
        if path.is_symlink() or path.stat().st_size > 2_097_152:
            raise ValueError('external authoring file must be a bounded regular JSON file')
        value = json.loads(path.read_text())
        sha(value)  # Reject NaN/Infinity and non-JSON values before persistence.
        return value

    def _verify_request(self, digest):
        value = self._read(self._path('requests', digest))
        if not isinstance(value, dict) or value.get('schema') != SCHEMA or sha(value) != digest:
            raise ValueError('external authoring request identity changed')
        return value

    def _response(self, digest):
        response = self._read(self._path('responses', digest))
        if (not isinstance(response, dict)
                or set(response) != {'request_sha256', 'manifest', 'authoring'}
                or response['request_sha256'] != digest or not isinstance(response['manifest'], dict)
                or not isinstance(response['authoring'], dict)
                or response['authoring'].get('kind') not in {'codex-agent', 'external'}):
            raise ValueError('external authoring response requires exact request binding, manifest and explicit author kind')
        return response

    def verify_consumed(self):
        for path in sorted((self.directory / 'consumed').glob('*.json')):
            receipt = self._read(path)
            digest = path.stem
            self._verify_request(digest)
            response = self._response(digest)
            expected = {'schema': 'scienceutopia.external-manifest-consumed.v5',
                'request_sha256': digest, 'response_sha256': sha(response),
                'manifest_sha256': sha(response['manifest']), 'authoring': response['authoring']}
            if receipt != expected:
                raise ValueError('consumed external authoring response/manifest changed')

    def generate(self, **kwargs):
        # JSON roundtrip standardizes tuple seed_ctx to a JSON array, preserving
        # all supplied request fields without interpreting instructions in them.
        request = json.loads(json.dumps({'schema': SCHEMA, 'request': kwargs},
            ensure_ascii=False, allow_nan=False))
        digest = sha(request)
        request_path, response_path = self._path('requests', digest), self._path('responses', digest)
        if request_path.exists():
            if self._verify_request(digest) != request:
                raise ValueError('saved external authoring request differs')
        else:
            write_json_atomic(request_path, request, sort_keys=True, allow_nan=False)
        if not response_path.exists():
            raise ExternalAuthoringPending(digest, request_path, response_path)
        response = self._response(digest)
        receipt = {'schema': 'scienceutopia.external-manifest-consumed.v5',
            'request_sha256': digest, 'response_sha256': sha(response),
            'manifest_sha256': sha(response['manifest']), 'authoring': response['authoring']}
        consumed_path = self._path('consumed', digest)
        if consumed_path.exists() and self._read(consumed_path) != receipt:
            raise ValueError('consumed external authoring response/manifest changed')
        write_json_atomic(consumed_path, receipt, sort_keys=True, allow_nan=False)
        # Structural/code validity belongs to the existing proposer, so invalid
        # drafts still receive exact bounded technical receipts and null losses.
        return clone(response['manifest']), []


def audit_manifest_inbox(directory):
    """Read-only request/response provenance audit, not native-world validation."""
    inbox = ManifestInbox(directory)
    requests = []
    for path in sorted((inbox.directory / 'requests').glob('*.json')):
        digest = path.stem
        request = inbox._verify_request(digest)
        consumed = inbox._path('consumed', digest)
        requests.append({'request_sha256': digest,
            'prompt_sha256': sha(request['request'].get('prompt')),
            'status': 'consumed' if consumed.exists() else 'awaiting-consumption',
            'receipt': inbox._read(consumed) if consumed.exists() else None})
    return {'schema': 'scienceutopia.external-manifest-inbox-audit.v5', 'requests': requests,
        'scope': 'exact external request -> response -> manifest hashes; not provider authentication or native patch/execution validation',
        'model_calls': 0}
