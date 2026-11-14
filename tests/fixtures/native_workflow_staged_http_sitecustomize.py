"""Owned-child-only SCRIPTED HTTP facade; never installed in real experiments.

Actual bounded worker/calibration/factory/compiler/containers remain production
implementations. Only local HTTP replies are prescribed. No sockets are opened.
"""
import json
import os
from pathlib import Path

import requests

FIXTURE = json.loads(Path(os.environ['SCIENCE_UTOPIA_STAGED_WORKFLOW_HTTP_FIXTURE']).read_text())


class Response:
    status_code = 200
    def __init__(self, value):
        self.value = value
        self.text = json.dumps(value, ensure_ascii=False)
    def raise_for_status(self): pass
    def json(self): return self.value


class Session:
    production_count = 0

    def get(self, url, **kwargs):
        provider = FIXTURE['provider']
        if url == 'http://127.0.0.1:11434/api/version':
            return Response({'version': 'SCRIPTED'})
        if url == 'http://127.0.0.1:11434/api/tags':
            return Response({'models': [{'name': provider['model'], 'digest': provider['model_digest']}]})
        if url == 'http://127.0.0.1:11434/api/ps':
            return Response({'models': [{'name': provider['model'], 'digest': provider['model_digest'], 'context_length': 40960}]})
        raise AssertionError('Unexpected child fixture GET: '+url)

    def post(self, url, **kwargs):
        provider = FIXTURE['provider']
        payload = json.loads(kwargs['data'])
        if url == 'http://127.0.0.1:11434/api/generate':
            assert payload['prompt'] == '' and payload['model'] == provider['model']
            return Response({'model': provider['model'], 'done': True, 'done_reason': 'load',
                'response': '', 'eval_count': 0, 'prompt_eval_count': 0})
        assert url == 'http://127.0.0.1:11434/api/chat' and kwargs['timeout'] == (10,900)
        assert payload['model'] == provider['model']
        system = payload['messages'][0]['content']
        if 'TRUSTED INTERFACE CALIBRATION TASK' in system:
            from utopia.optimization import native_designer_preflight as preflight
            target = system.split('nothing is executed or adopted.\n')[1]
            if target.startswith(preflight.CONTROL_JSON_BEGIN):
                target = target.removeprefix(preflight.CONTROL_JSON_BEGIN).split(preflight.CONTROL_JSON_END,1)[0]
            if target.startswith('<tool_call>'):
                function, _ = json.JSONDecoder().raw_decode(target.removeprefix('<tool_call>').lstrip())
                action = {'tool': function['name'], **function['arguments']}
            else:
                action, _ = json.JSONDecoder().raw_decode(target)
                if set(action) == {'name','arguments'}:
                    action = {'tool': action['name'], **action['arguments']}
        else:
            assert FIXTURE['purpose'] == 'proposal'
            index = type(self).production_count
            type(self).production_count += 1
            action = FIXTURE['actions'][index]
        from utopia.optimization.native_designer_tools_v25 import response_message_from_action
        message = response_message_from_action(action)
        if payload['think']:
            message['thinking'] = 'SCRIPTED reasoning evidence, not actual model reasoning'
        return Response({'model': provider['model'], 'done': True, 'done_reason': 'stop',
            'prompt_eval_count': 100, 'eval_count': 20, 'message': message})


requests.Session = Session
