"""Trusted child-only HTTP fixture, never installed in an experiment/runtime.

Copied as sitecustomize.py by one explicit software test. No sockets are opened;
unexpected URLs fail. This lets the real bounded Python/worker/receipt path run
without borrowing the busy actual Qwen endpoint or inventing worker returns.
"""
import json
import os
from pathlib import Path

import requests


class _Response:
    status_code = 200
    def __init__(self, value): self.value = value; self.text = json.dumps(value, ensure_ascii=False)
    def raise_for_status(self): pass
    def json(self): return self.value


class _Session:
    def __init__(self):
        self.fixture = json.loads(Path(os.environ['SCIENCE_UTOPIA_WORKFLOW_HTTP_FIXTURE']).read_text())
    def get(self, url, **kwargs):
        if url == 'http://127.0.0.1:11434/api/version':
            return _Response({'version': 'SCRIPTED'})
        if url == 'http://127.0.0.1:11434/api/tags':
            return _Response({'models': [{'name': self.fixture['provider']['model'],
                'digest': self.fixture['provider']['model_digest']}]})
        raise AssertionError('Unexpected HTTP URL in owned child fixture: ' + url)
    def post(self, url, **kwargs):
        assert url == 'http://127.0.0.1:11434/api/chat'
        assert kwargs['timeout'] == (10, 900)
        assert kwargs['data'].decode() == self.fixture['expected_request_wire_utf8']
        return _Response({'model': self.fixture['provider']['model'], 'done': True, 'done_reason': 'stop',
            'prompt_eval_count': 100, 'eval_count': 20,
            'message': {'role': 'assistant', 'content': json.dumps(self.fixture['literal_submission'], ensure_ascii=False)}})


requests.Session = _Session
