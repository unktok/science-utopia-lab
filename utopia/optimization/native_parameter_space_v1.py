"""Black-box numeric search over literal fields of a native SystemSpec.

No surrogate world, source synthesis, scientific veto or parameter consumer is
introduced. The caller declares existing fields/bounds and supplies the real
native evaluator. Sampling is a trusted optimizer operation, not repair of an
untrusted model submission. Historical domain constructors stay unchanged.
"""
import math
import random

from utopia.system import SystemSpec, validate_system_spec
from utopia.system.design_patch import clone, digest
from .native_design_space import (
    SCHEMA as DOMAIN_SCHEMA, _get, _set, source_paths,
    validate_design_space, require_candidate_in_space,
)

SCHEMA = 'scienceutopia.native-parameter-space.v1'


def parameter_domain(anchor, coordinates, *, world_law_scope=None):
    """Explicit prospective coordinate list, not a change to old six-axis spaces."""
    validate_system_spec(anchor).require_valid()
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError('nonempty explicit existing numeric coordinates required')
    contract = {'schema': DOMAIN_SCHEMA, 'kind': 'parameters',
        'anchor_sha256': digest(anchor.to_dict()), 'numeric_coordinates': clone(coordinates),
        'code_paths': source_paths(anchor.to_dict()),
        'scope': 'Only the explicitly listed pre-existing numeric fields may change. '
            'Source, mechanisms, wires, schedules, seed and all other fields stay literal. '
            'A field declaration is not proof that a program consumes it or that loss changes.',
        'violation_policy': 'Technical null before world execution; never repair, project or refill.'}
    if world_law_scope is not None:
        contract['world_law_scope'] = world_law_scope
    try:
        return validate_design_space(anchor, contract)
    except (KeyError,IndexError,TypeError,AttributeError) as error:
        raise ValueError('coordinate must address an existing literal numeric field') from error


class NativeParameterSpace:
    """SearchSpace adapter for existing ask/tell optimizers and native worlds.

    Uniform initial sampling and bounded uniform mutation preserve every
    non-coordinate JSON value. NativeParameterOptimizer binds its saved state
    to this exact space; a full experiment must additionally bind its loss,
    model, corpus, source, measurements and world conditions.
    """
    def __init__(self, anchor, contract):
        if not isinstance(anchor, SystemSpec):
            anchor = SystemSpec.from_dict(clone(anchor))
        self._anchor = SystemSpec.from_dict(clone(anchor.to_dict()))
        validate_system_spec(self._anchor).require_valid()
        self._contract = validate_design_space(self._anchor, clone(contract))
        if self._contract['kind'] != 'parameters' or not self._contract['numeric_coordinates']:
            raise ValueError('explicit nonempty parameter-only domain required')
        if any(not math.isfinite(c['upper']-c['lower']) for c in self._contract['numeric_coordinates']):
            raise ValueError('finite representable numeric spans required')
        index = {node.mechanism_id:i for i,node in enumerate(self._anchor.mechanisms)}
        self._coordinates = [{**clone(c), 'id':'coordinate-'+str(i),
            'absolute_path':'/mechanisms/'+str(index[c['mechanism_id']])+c['path']}
            for i,c in enumerate(self._contract['numeric_coordinates'])]
        self._binding = {'schema':SCHEMA, 'anchor':self._anchor.to_dict(),
                         'design_space':clone(self._contract)}
        self._binding_sha256 = digest(self._binding)

    @property
    def binding(self):
        return clone(self._binding)

    @property
    def binding_sha256(self):
        return self._binding_sha256

    def validate(self, candidate):
        try:
            raw = clone(candidate)
            spec = SystemSpec.from_dict(raw)
            if digest(spec.to_dict()) != digest(raw):
                raise ValueError('complete literal SystemSpec required; no canonical repair')
            require_candidate_in_space(self._anchor, spec, self._contract)
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            raise ValueError('literal candidate must fit the declared native numeric space') from error

    def values(self, candidate):
        self.validate(candidate)
        return {c['id']:clone(_get(candidate,c['absolute_path'])) for c in self._coordinates}

    def candidate(self, values):
        if not isinstance(values, dict) or set(values) != {c['id'] for c in self._coordinates}:
            raise ValueError('exact complete coordinate values required')
        result = self._anchor.to_dict()
        for c in self._coordinates:
            value = values[c['id']]
            if (type(value) not in (int,float) or not math.isfinite(value)
                    or c['integer'] and type(value) is not int
                    or not c['lower'] <= value <= c['upper']):
                raise ValueError('literal value outside the declared numeric coordinate')
            _set(result,c['absolute_path'],value)
        self.validate(result)
        return result

    def _rng(self, seed, proposal_index, purpose):
        if type(seed) is not int or type(proposal_index) is not int or proposal_index < 0:
            raise ValueError('integer seed and nonnegative integer proposal index required')
        return random.Random(int(digest({'space':self._binding_sha256,'schema':SCHEMA,
            'seed':seed,'proposal_index':proposal_index,'purpose':purpose})[:16],16))

    def sample(self, *, seed, proposal_index):
        rng = self._rng(seed,proposal_index,'sample')
        return self.candidate({c['id']:(rng.randint(math.ceil(c['lower']),math.floor(c['upper']))
            if c['integer'] else rng.uniform(c['lower'],c['upper'])) for c in self._coordinates})

    def mutate(self, incumbent, *, seed, proposal_index, scale):
        values = self.values(incumbent)
        if type(scale) not in (int,float) or not math.isfinite(scale) or not 0 < scale <= 1:
            raise ValueError('finite mutation scale in (0,1] required')
        rng = self._rng(seed,proposal_index,'mutate')
        for c in self._coordinates:
            current = values[c['id']]
            radius = scale*(c['upper']-c['lower'])
            if c['integer']:
                radius = max(1,math.ceil(radius))
                lo = max(math.ceil(c['lower']),current-radius)
                hi = min(math.floor(c['upper']),current+radius)
                values[c['id']] = rng.randint(lo,hi)
            else:
                lo,hi = max(c['lower'],current-radius), min(c['upper'],current+radius)
                values[c['id']] = rng.uniform(lo,hi)
        return self.candidate(values)


class NativeParameterOptimizer:
    """Existing adaptive random search, with explicit numeric-space identity.

    This is not a new optimizer or a complete scientific campaign journal.
    Persist observations and the full evaluation contract separately; a state
    checksum alone is not an authenticated history or a cold native proof.
    """
    SCHEMA = SCHEMA+'.optimizer-state'

    def __init__(self, space, *, seed, initial_random=4, mutation_scale=.2):
        from .blackbox import AdaptiveRandomSearch
        if not isinstance(space, NativeParameterSpace):
            raise ValueError('explicit native numeric space required')
        if (type(mutation_scale) not in (int,float) or not math.isfinite(mutation_scale)
                or not 0 < mutation_scale <= 1):
            raise ValueError('finite mutation scale in (0,1] required')
        self._space = space
        self._optimizer = AdaptiveRandomSearch(space,seed=seed,initial_random=initial_random,
                                              mutation_scale=mutation_scale)

    def ask(self, count=1):
        return self._optimizer.ask(count)

    def tell(self, observations):
        self._optimizer.tell(observations)

    def state_dict(self):
        # Unsealed, so it can be passed once to the existing journal save API.
        return {'schema':self.SCHEMA, 'space_binding':self._space.binding,
                'space_binding_sha256':self._space.binding_sha256,
                'optimizer':self._optimizer.state_dict()}

    @classmethod
    def from_state(cls, space, state):
        from .blackbox import AdaptiveRandomSearch
        from .native_numeric_designer import checked
        if not isinstance(state,dict):
            raise ValueError('literal numeric optimizer state object required')
        value = clone(state)
        if 'content_sha256' in value:
            checked(value)
            value.pop('content_sha256')
        if (not isinstance(space,NativeParameterSpace)
                or set(value) != {'schema','space_binding','space_binding_sha256','optimizer'}
                or value['schema'] != cls.SCHEMA or value['space_binding'] != space.binding
                or value['space_binding_sha256'] != space.binding_sha256
                or not isinstance(value['optimizer'],dict)):
            raise ValueError('saved optimizer requires the exact expected native numeric space')
        restored = AdaptiveRandomSearch.from_state(space,value['optimizer'])
        if digest(restored.state_dict()) != digest(value['optimizer']):
            raise ValueError('saved optimizer is not its literal canonical state')
        instance = cls.__new__(cls)
        instance._space,instance._optimizer = space,restored
        return instance
