"""Durable deterministic one-coordinate optimization policies, not simulators.

The caller supplies actual native observations and represented backwards. These
policies neither execute a world nor equate a represented derivative with the
native/Qwen Jacobian. Historical evidence is explicitly charged to each arm.
"""
from copy import deepcopy
import math
from pathlib import Path
import re

from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, write_json_atomic


SCHEMA = 'scienceutopia.native-path-policy.v10'
DOMAIN = [.2, .8]


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite numeric value required')
    return value


def _hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value)


def _seal(value):
    result = deepcopy(value)
    result.pop('content_sha256', None)
    result['content_sha256'] = digest(result)
    return result


def _observed(state):
    return state['historical'] + [event['observation'] for event in state['events']
                                  if event['observation']['status'] == 'complete']


def _incumbent(state):
    # Python min is stable: a tie retains the earliest observation, never moves
    # the incumbent merely to manufacture a different trajectory.
    return deepcopy(min(_observed(state), key=lambda row: row['loss']))


def _current(state):
    complete = [event['observation'] for event in state['events']
                if event['observation']['status'] == 'complete']
    return complete[-1]['theta'] if complete else state['initial_current_theta']


def _backward(state, backward):
    rule = state['gradient_rule']
    if (not isinstance(backward, dict)
            or backward.get('coordinates') != [_current(state)]
            or not isinstance(backward.get('gradient'), list)
            or len(backward['gradient']) != 1
            or not _hash(backward.get('representation_sha256'))
            or backward.get('temperature') != rule['temperature_schedule'][len(state['events'])]
            or backward.get('native_derivative_verified') is not False
            or backward.get('full_native_world_autograd') is not False):
        raise ValueError('current-coordinate fixed-temperature represented backward required')
    _finite(backward['gradient'][0])
    return deepcopy(backward)


def _proposal(state, backward=None):
    current = _current(state)
    incumbent = _incumbent(state)
    if state['method'] == 'blackbox':
        if backward is not None:
            raise ValueError('blackbox policy cannot consume represented gradients')
        points = sorted(set(row['theta'] for row in _observed(state)))
        anchor = incumbent['theta']
        index = points.index(anchor)
        intervals = []
        if index:
            intervals.append((points[index-1], anchor))
        if index+1 < len(points):
            intervals.append((anchor, points[index+1]))
        lo, hi = min(intervals, key=lambda pair: (-(pair[1]-pair[0]), pair[0]))
        candidate = lo + (hi-lo)/2
        detail = {'rule': 'bisect widest observed interval adjacent to incumbent; lower interval breaks ties',
                  'interval': [lo, hi], 'requested': candidate}
    else:
        backward = _backward(state, backward)
        rule = state['gradient_rule']
        gradient = backward['gradient'][0]
        requested_step = -rule['learning_rate']*gradient
        _finite(requested_step)
        displacement = min(rule['trust_radius'], max(-rule['trust_radius'], requested_step))
        requested = current + displacement
        candidate = min(DOMAIN[1], max(DOMAIN[0], requested))
        detail = {'rule': 'declared represented gradient step, trust clipped, then domain projected',
                  'requested_step': requested_step, 'trust_clipped_step': displacement,
                  'requested': requested, 'backward': backward,
                  'gradient_rule': deepcopy(rule)}
    parent = deepcopy(state)
    parent['pending'] = None
    parent = _seal(parent)
    return _seal({'schema': SCHEMA+'.proposal', 'parent_state_sha256': parent['content_sha256'],
        'method': state['method'], 'sequence': len(state['events']),
        'loss_spec_sha256': state['loss_spec_sha256'],
        'world_binding_sha256': digest(state['world_binding']),
        'observed_evidence_sha256': digest(_observed(state)),
        'current_theta': current, 'incumbent_before': incumbent,
        'candidate_theta': candidate, 'unchanged': candidate == current, **detail})


def validate_state(state):
    if (state.get('schema') != SCHEMA
            or state.get('content_sha256') != _seal(state)['content_sha256']
            or state.get('method') not in ('blackbox', 'represented-gradient')
            or state.get('domain') != DOMAIN
            or state.get('initial_current_theta') != .5
            or not _hash(state.get('loss_spec_sha256'))
            or not isinstance(state.get('world_binding'), dict) or not state['world_binding']
            or type(state.get('fresh_budget')) is not int or state['fresh_budget'] < 1):
        raise ValueError('policy identity/configuration/hash mismatch')
    history = state.get('historical', [])
    if len(history) != 3 or [row.get('theta') for row in history] != [.2, .5, .8]:
        raise ValueError('exact shared three calibration endpoints required, charged to each arm')
    for row in history:
        _finite(row.get('loss'))
        if not isinstance(row.get('provenance'), dict) or not row['provenance']:
            raise ValueError('historical endpoint provenance required')
    rule = state.get('gradient_rule')
    if state['method'] == 'represented-gradient':
        if (not isinstance(rule, dict) or set(rule) != {'learning_rate','trust_radius','temperature_schedule'}
                or any(_finite(rule[key]) <= 0 for key in ('learning_rate','trust_radius'))
                or not isinstance(rule['temperature_schedule'], list)
                or len(rule['temperature_schedule']) != state['fresh_budget']
                or any(_finite(value) <= 0 for value in rule['temperature_schedule'])):
            raise ValueError('explicit fixed positive gradient hyperparameters required')
    elif rule is not None:
        raise ValueError('blackbox policy has no gradient hyperparameters')
    events = state.get('events')
    if not isinstance(events, list) or len(events) > state['fresh_budget']:
        raise ValueError('declared fresh proposal budget exceeded')
    # Replay policy decisions from their exact progressively available evidence.
    replay = {**deepcopy(state), 'events': [], 'pending': None}
    for event in events:
        proposal = event['proposal']
        expected = _proposal(replay, proposal.get('backward'))
        if proposal != expected:
            raise ValueError('historical policy proposal changed or used unavailable evidence')
        _validate_observation(replay, proposal, event['observation'])
        if any(e['observation']['status'] != 'complete' for e in replay['events']):
            raise ValueError('technical failure is terminal, not an additional numeric observation')
        replay['events'].append(deepcopy(event))
    pending = state.get('pending')
    if pending is not None and (len(events) == state['fresh_budget'] or
            any(e['observation']['status'] != 'complete' for e in events)):
        raise ValueError('terminal policy cannot contain another pending proposal')
    if pending is not None and pending != _proposal(replay, pending.get('backward')):
        raise ValueError('pending policy decision is stale or changed')
    return state


def _validate_observation(state, proposal, observation):
    if (observation.get('theta') != proposal['candidate_theta']
            or observation.get('loss_spec_sha256') != state['loss_spec_sha256']
            or observation.get('world_binding_sha256') != digest(state['world_binding'])
            or not isinstance(observation.get('provenance'), dict) or not observation['provenance']):
        raise ValueError('observation coordinate/objective/world/provenance mismatch')
    if observation.get('status') == 'complete':
        _finite(observation.get('loss'))
        if (observation.get('error') is not None
                or not _hash(observation['provenance'].get('endpoint_record_sha256'))):
            raise ValueError('successful observation requires endpoint record hash and no technical error')
    elif (observation.get('status') != 'technical-failure' or observation.get('loss') is not None
          or not isinstance(observation.get('error'), dict) or not observation['error']):
        raise ValueError('technical failure requires null loss and explicit error, never a penalty')


class NativePathPolicy:
    """Single-writer atomic JSON ask/tell state, independently replayable.

    No-op proposals still require their declared fresh native evaluation. A
    technical failure terminates the arm honestly; it is not budget completion.
    The runner verifies checkpoints; this component binds receipts but does not
    authenticate caller-supplied provenance or representativeness of gradients.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.state = validate_state(decode_json(self.path.read_text(), strict=True, finite_floats=True))

    @classmethod
    def create(cls, path, *, method, historical, loss_spec_sha256, world_binding,
               fresh_budget=3, gradient_rule=None, initial_theta=.5):
        path = Path(path)
        if path.exists():
            raise ValueError('existing policy state must be reopened, never overwritten')
        state = _seal({'schema': SCHEMA, 'method': method, 'domain': DOMAIN,
            'historical': deepcopy(historical), 'loss_spec_sha256': loss_spec_sha256,
            'world_binding': deepcopy(world_binding), 'fresh_budget': fresh_budget,
            'initial_current_theta': initial_theta,
            'gradient_rule': deepcopy(gradient_rule), 'events': [], 'pending': None})
        validate_state(state)
        write_json_atomic(path, state, sort_keys=True, allow_nan=False)
        return cls(path)

    def _fresh(self):
        state = validate_state(decode_json(self.path.read_text(), strict=True, finite_floats=True))
        if state != self.state:
            raise ValueError('stale policy writer; reopen exact committed state')
        return state

    def _save(self, state):
        state = _seal(state)
        validate_state(state)
        write_json_atomic(self.path, state, sort_keys=True, allow_nan=False)
        self.state = state

    def summary(self):
        state = self._fresh()
        failures = [e for e in state['events'] if e['observation']['status'] != 'complete']
        successful = len(state['events'])-len(failures)
        return {'current_theta': _current(state), 'incumbent': _incumbent(state),
            'historical_observations_charged': 3, 'fresh_native_evaluations': successful,
            'fresh_proposals_consumed': len(state['events']),
            'total_observations_charged': 3+successful,
            'status': 'terminal-technical-failure' if failures else
                      'budget-complete' if len(state['events']) == state['fresh_budget'] else 'open'}

    def ask(self, *, backward=None):
        state = self._fresh()
        if state['pending'] is not None:
            if backward is not None and backward != state['pending'].get('backward'):
                raise ValueError('pending gradient cannot be replaced after ask')
            return deepcopy(state['pending'])
        if self.summary()['status'] != 'open':
            raise ValueError('policy is terminal or declared fresh budget is complete')
        proposal = _proposal(state, backward)
        state['pending'] = proposal
        self._save(state)
        return deepcopy(proposal)

    def tell(self, proposal_sha256, observation):
        state = self._fresh()
        for event in state['events']:
            if event['proposal']['content_sha256'] == proposal_sha256:
                if event['observation'] != observation:
                    raise ValueError('completed proposal cannot receive a different observation')
                return self.summary()
        proposal = state['pending']
        if proposal is None or proposal['content_sha256'] != proposal_sha256:
            raise ValueError('observation does not match the pending exact proposal')
        _validate_observation(state, proposal, observation)
        state['events'].append({'proposal': proposal, 'observation': deepcopy(observation)})
        state['pending'] = None
        self._save(state)
        return self.summary()
