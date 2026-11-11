"""Finite component tests on exact recorded native inputs, not a loss oracle.

The trusted caller supplies verified developer fixtures and the existing
container executor. Code is never evaluated in this process. This API alone
does not wire a new tool into a designer or certify a whole institution.
"""
import fcntl
import json
import math
from pathlib import Path

from utopia.optimization.native_code_trace import validate_record
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.code_mechanisms import sha, validate_code_artifact, validate_context, validate_code_result
from utopia.system.design_patch import clone

SCHEMA = 'scienceutopia.native-component-lab.v1'


class ComponentProbePending(BaseException):
    """An intent without a terminal record must not dispatch another probe."""


def fixture_bank(records):
    """Validate literal container bundles; native attribution is a caller duty.

    A bundle is not itself an original-source audit. The caller must bind its
    dataset to original-source physical evidence before labelling it native.
    This function never guesses absent failed-call inputs or invents fixtures.
    """
    result = {}
    for value in records:
        row = validate_record(clone(value)); identity = 'fixture-'+row['bundle_sha256']
        result[identity] = row
    if not result: raise ValueError('explicit nonempty recorded component fixtures required')
    return result


LEGACY_PROBE_SCOPE='legacy-eight-v1'
EXTENDED_PROBE_SCOPE='declared-sixtyfour-v2'


def validate_probe_budget(maximum_probes,scope=LEGACY_PROBE_SCOPE):
    bounds={LEGACY_PROBE_SCOPE:8,EXTENDED_PROBE_SCOPE:64}
    if not isinstance(scope,str) or scope not in bounds or type(maximum_probes) is not int or not 1<=maximum_probes<=bounds[scope]:
        raise ValueError('finite component budget differs from explicit scope; no refills')


class NativeComponentLab:
    def __init__(self, directory, *, records, provenance, executor, source_commit, maximum_probes=8,
                 budget_scope=LEGACY_PROBE_SCOPE):
        if (not isinstance(source_commit, str) or len(source_commit) != 40
                or any(c not in '0123456789abcdef' for c in source_commit)):
            raise ValueError('full component-lab source required')
        validate_probe_budget(maximum_probes,budget_scope)
        if not isinstance(provenance, dict) or not provenance:
            raise ValueError('explicit fixture provenance required')
        if (type(executor.timeout) not in (int,float) or not math.isfinite(executor.timeout)
                or not .1 <= executor.timeout <= 60):
            raise ValueError('explicit bounded component executor time required')
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.fixtures = fixture_bank(records); self.executor = executor
        core = {'schema':SCHEMA+'.contract', 'source_commit':source_commit,
            'fixture_hashes':sorted(self.fixtures), 'fixture_provenance':clone(provenance),
            'image_id':executor.image_id, 'maximum_probes':maximum_probes,
            'executor_timeout_seconds':executor.timeout,
            'source_execution_on_host':False, 'new_native_worlds':0, 'new_model_calls':0,
            'scope':'single component on literal developer fixtures; no scientific loss or golden-output gate'}
        if budget_scope!=LEGACY_PROBE_SCOPE:core['budget_scope']=budget_scope
        path = self.directory/'contract.json'
        if path.exists():
            self.contract = checked(json.loads(path.read_text()))
            if {k:v for k,v in self.contract.items() if k != 'content_sha256'} != core:
                raise ValueError('component-lab source, fixtures, image or budget changed')
        else:
            self.contract = save(path, core)

    def probe(self, artifact, fixture_id):
        with (self.directory/'writer.lock').open('a') as owner:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            previous = self.replay()
            if (self.executor.image_id != self.contract['image_id']
                    or self.executor.timeout != self.contract['executor_timeout_seconds']):
                raise ValueError('component executor image/time bound changed')
            if any(v['terminal'] is None for v in previous):
                raise ComponentProbePending('unclosed component probe; no redispatch or next probe')
            index = len(previous)
            if index >= self.contract['maximum_probes']:
                raise ValueError('finite component budget exhausted')
            name = self.directory/f'probe-{index:03d}'
            intent = save(name.with_suffix('.intent.json'), {'schema':SCHEMA+'.intent',
                'contract_sha256':self.contract['content_sha256'], 'artifact':clone(artifact),
                'fixture_id':fixture_id})
            terminal = {'schema':SCHEMA+'.result', 'intent_sha256':intent['content_sha256'],
                'new_native_worlds':0, 'new_model_calls':0}
            try:
                if fixture_id not in self.fixtures: raise ValueError('unknown explicit component fixture')
                context = self.fixtures[fixture_id]['context']
                validate_code_artifact(artifact); validate_context(artifact, context)
                execution = self.executor.execute(clone(artifact), clone(context))
                validate_code_result(artifact, execution.result)
                if execution.receipt != {**execution.receipt, 'image_id':self.contract['image_id'],
                        'artifact_sha256':sha(artifact), 'context_sha256':sha(context),
                        'result_sha256':sha(execution.result)}:
                    raise ValueError('component executor receipt differs from literal request')
                terminal.update(status='returned', result=clone(execution.result), receipt=clone(execution.receipt))
            except Exception as error:
                terminal.update(status='raised', error_type=type(error).__name__, error=str(error),
                    remote_completion_inferred=False)
            # A BaseException deliberately leaves an intent with no terminal.
            return save(name.with_suffix('.result.json'), terminal)

    def replay(self):
        result = []; expected = {'contract.json','writer.lock'}
        for index, path in enumerate(sorted(self.directory.glob('probe-*.intent.json'))):
            if path.name != f'probe-{index:03d}.intent.json': raise ValueError('component probe sequence differs')
            expected.add(path.name)
            intent = checked(json.loads(path.read_text()))
            if intent['schema'] != SCHEMA+'.intent' or intent['contract_sha256'] != self.contract['content_sha256']:
                raise ValueError('component probe intent differs from contract')
            reply_path = self.directory/f'probe-{index:03d}.result.json'
            terminal = checked(json.loads(reply_path.read_text())) if reply_path.exists() else None
            if terminal is not None:
                expected.add(reply_path.name)
                if (terminal['schema'] != SCHEMA+'.result' or terminal['intent_sha256'] != intent['content_sha256']
                        or terminal['new_native_worlds'] != 0 or terminal['new_model_calls'] != 0):
                    raise ValueError('component probe terminal differs from intent')
                if terminal['status'] == 'returned':
                    artifact = intent['artifact']; context = self.fixtures[intent['fixture_id']]['context']
                    validate_code_artifact(artifact); validate_context(artifact, context)
                    validate_code_result(artifact, terminal['result'])
                    expected_receipt = {'image_id':self.contract['image_id'], 'artifact_sha256':sha(artifact),
                        'context_sha256':sha(context), 'result_sha256':sha(terminal['result'])}
                    if any(terminal['receipt'].get(k) != v for k,v in expected_receipt.items()):
                        raise ValueError('component replay receipt differs')
                elif (terminal['status'] != 'raised' or terminal.get('remote_completion_inferred') is not False
                        or not isinstance(terminal.get('error'),str) or not isinstance(terminal.get('error_type'),str)):
                    raise ValueError('component probe failure status differs')
            result.append({'intent':intent, 'terminal':terminal})
        if (len(result) > self.contract['maximum_probes'] or
                {p.name for p in self.directory.iterdir() if p.is_file()} - expected):
            raise ValueError('unaccounted component dispatch, reply or budget')
        return result
