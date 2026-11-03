"""Scripted audit contracts only: no inference, native worlds or scientific data."""
from copy import deepcopy
import json
import sqlite3

import pytest

from scripts import analyze_native_autonomous_search_v14 as audit
from tests.optimization.test_native_adaptive_search import tiny_parent, tiny_definition, fail_factory
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic, file_sha256


def save(path,value):
    write_json_atomic(path,value,sort_keys=True,allow_nan=False)


def hashed(path,value,field='content_sha256'):
    value = deepcopy(value)
    value[field] = digest(value)
    save(path,value)
    return value


def failed_designer(authoring,request):
    """Durable two-draft malformed-output fixture, not a model call."""
    request_sha = digest(request)
    cell = authoring/('generation-'+request_sha)
    binding = hashed(cell/'request.json',{'schema':'scienceutopia.llm-vocabulary-request.v14',
        'request':request,'request_sha256':request_sha,'provider_binding':{'model':'scripted-qa'},
        'image_id':'scripted-qa','settings':{'max_attempts':2,'max_tokens':4096}},'binding_sha256')
    attempts = []
    for index in range(2):
        prompt = 'Explicit malformed-response scripted software QA; '+json.dumps(request,sort_keys=True)
        start_path = cell/f'attempt-{index:02d}.started.json'
        done_path = cell/f'attempt-{index:02d}.completed.json'
        save(start_path,{'schema':'scienceutopia.llm-vocabulary-attempt-start.v14',
            'attempt':index,'binding_sha256':binding['binding_sha256'],'dispatch_intent':True,
            'prompt':prompt,'prompt_sha256':digest(prompt),'response_schema':{'type':'object'},
            'started_utc':'2000-01-01T00:00:00Z'})
        hashed(done_path,{'schema':'scienceutopia.llm-vocabulary-attempt.v14',
            'binding_sha256':binding['binding_sha256'],'attempt':index,
            'started_file_sha256':file_sha256(start_path),'status':'invalid','definition':None,
            'errors':[{'type':'ValueError','message':'scripted malformed JSON'}],
            'model_reply':{'output':None,'messages':[{'role':'assistant','content':'not JSON'}],
                'transport':{'kind':'scripted-no-HTTP'}}})
        attempts.append({'attempt':index,'started_sha256':file_sha256(start_path),
            'completed_sha256':file_sha256(done_path),'status':'invalid'})
    definition = {'generation_failure':{'kind':'scripted-no-model-response'}}
    hashed(cell/'response.json',{'schema':'scienceutopia.llm-vocabulary-result.v14',
        'binding_sha256':binding['binding_sha256'],'request_sha256':request_sha,
        'status':'generation-failed','definition':definition,'selected_attempt':None,
        'attempts':attempts,'source_execution_on_host':False})
    return definition


def fixture(root,*,terminal=True,valid_definitions=False):
    initial = tiny_parent().to_dict()
    world = {'source_commit':'fixture-source','classification':audit.FIXTURE,
        'model_digest':'fixture-model','corpus_sha256':'fixture-corpus','years':2,'corpus_years':4,
        'experiment':audit.EXPERIMENT}
    loss_specs = list(audit.objective_specs().values())
    entries,controllers = [],[]
    for identity,loss,method,budget in [('throughput-blackbox',loss_specs[0],'blackbox',2),
            ('efficiency-blackbox',loss_specs[1],'blackbox',2),('efficiency-nested',loss_specs[1],'nested-lr',4)]:
        request = {'schema':'scienceutopia.native-search-request.v14','initial_system':initial,
            'loss_spec':loss,'method':method,'seed':42,'years':2,'native_budget':budget,
            'designer':{'model':'qwen3:8b','max_attempts':2,'max_tokens':4096}}
        directory = root/identity
        save(directory/'plan.json',{'schema':'scienceutopia.native-search-plan.v14',
            'request':request,'request_sha256':digest(request),'source_commit':'fixture-source'})
        entries.append({'id':identity,'request':request,'directory':identity})
        kwargs = dict(initial_system=tiny_parent(),loss_spec=loss,seeds=[42],world_binding=world,seed=42)
        if method == 'blackbox':
            controller = NativeAdaptiveDesignCampaign(directory/'campaign',**kwargs,
                strategies={'automatic':{'kind':'scripted-no-model'}},mode='blackbox')
        else:
            controller = NativeNestedDesignCampaign(directory/'campaign',**kwargs)
        controllers.append(controller)
        if terminal:
            for _ in range(budget if method == 'blackbox' else 3):
                generate = lambda req: failed_designer(directory/'authoring',req)
                if valid_definitions:
                    generate = lambda req: tiny_definition()
                if method == 'blackbox':
                    controller.advance(simulation_factory=fail_factory,generators={'automatic':generate},count=1)
                else:
                    controller.advance(simulation_factory=fail_factory,generator=generate)
    plan = {'schema':audit.RAW_SCHEMA,'source_commit':'fixture-source','classification':audit.FIXTURE,
        'experiment':audit.EXPERIMENT,'world':world,'initial_system':initial,'seed':42,
        'population':{'authors':5,'conference_setting':1},
        'designer_budget':{'generations':6,'max_attempts_per_generation':2,'max_http_attempts':12},'runs':entries}
    save(root/'plan.json',plan)
    return plan,controllers


def rehash_file(path):
    value = json.loads(path.read_text())
    value.pop('content_sha256',None)
    return hashed(path,value)


def test_failed_designer_consumes_all_slots_without_physical_worlds_and_is_repeatable(tmp_path):
    fixture(tmp_path)
    before = audit._inventory(tmp_path)
    first = audit.analyze(tmp_path,expected_source='fixture-source')
    second = audit.analyze(tmp_path,expected_source='fixture-source')
    assert first == second and before == audit._inventory(tmp_path)
    assert first['status'] == 'budget-complete-with-failures'
    assert first['consumed_native_slots'] == first['technical_failures'] == 8
    assert first['physical_native_worlds'] == first['physical_world_directory_count'] == 0
    assert first['physical_researcher_responses'] == 0
    assert first['designer_costs'] == {'generations':6,'dispatch_intents':12,'known_responses':12,
        'valid_drafts':0,'interrupted_response_unknown':0}
    assert all(proof['started_records'][0]['prompt_sha256'] == digest(proof['started_records'][0]['prompt'])
        for run in first['runs'].values() for proof in run['designer']['proofs'])
    assert first['claims']['scripted_researcher_HTTP'] and not first['claims']['live_fixed_Qwen_researchers']
    assert [r['scheduled_native_slots'] for r in first['runs']['efficiency-nested']['observations']] == [2,1,1]
    assert all(r['loss'] is None for run in first['runs'].values() for r in run['observations'])


def test_empty_incomplete_audit_does_not_charge_unstarted_generations(tmp_path):
    fixture(tmp_path,terminal=False)
    result = audit.analyze(tmp_path,expected_source='fixture-source',require_complete=False)
    assert result['status'] == 'in-progress' and result['consumed_native_slots'] == 0
    assert result['designer_costs']['dispatch_intents'] == 0
    with pytest.raises(ValueError,match='incomplete'):
        audit.analyze(tmp_path,expected_source='fixture-source')


def test_controller_native_failure_is_null_not_hidden_or_replaced(tmp_path):
    plan,controllers = fixture(tmp_path,valid_definitions=True)
    run = audit.audit_native_campaign(tmp_path/'efficiency-nested',method='nested-lr',world=plan['world'],
        classification=audit.FIXTURE,loss=plan['runs'][2]['request']['loss_spec'],
        initial_system=plan['initial_system'],expected_budget=4)
    assert run['terminal'] and run['consumed_native_slots'] == 4
    assert len(run['observations']) == 4 and run['physical_native_worlds'] == 0
    assert all(r['observation']['status'] == 'failed' and r['loss'] is None for r in run['observations'])
    assert run['conditional_update_proof']['updates'] == 0


@pytest.mark.parametrize('mutation',['hidden-attempt','raw-output','prompt','definition','request','status','source','budget'])
def test_rehashed_tampering_is_rejected(tmp_path,mutation):
    fixture(tmp_path)
    cells = sorted((tmp_path/'throughput-blackbox'/'authoring').glob('generation-*'))
    cell = cells[0]
    if mutation == 'hidden-attempt':
        response = json.loads((cell/'response.json').read_text())
        response['attempts'].pop()
        response.pop('content_sha256'); hashed(cell/'response.json',response)
    elif mutation == 'raw-output':
        path = cell/'attempt-00.completed.json'
        done = json.loads(path.read_text()); done['model_reply']['output'] = {'invented':'repair'}
        done.pop('content_sha256'); hashed(path,done)
    elif mutation == 'prompt':
        path = cell/'attempt-00.started.json'
        start = json.loads(path.read_text()); start['prompt'] += ' hidden veto'; save(path,start)
    elif mutation == 'definition':
        path = cell/'response.json'; result = json.loads(path.read_text())
        result['definition'] = tiny_definition(); result.pop('content_sha256'); hashed(path,result)
    elif mutation in ('request','status'):
        path = cell/'response.json'; result = json.loads(path.read_text())
        result['request_sha256' if mutation == 'request' else 'status'] = 'forged'
        result.pop('content_sha256'); hashed(path,result)
    else:
        plan = json.loads((tmp_path/'plan.json').read_text())
        if mutation == 'source': plan['source_commit'] = 'forged'
        if mutation == 'budget': plan['designer_budget']['max_http_attempts'] = 13
        save(tmp_path/'plan.json',plan)
    with pytest.raises(ValueError):
        audit.analyze(tmp_path,expected_source='fixture-source')


def test_orphan_physical_world_is_rejected(tmp_path):
    fixture(tmp_path)
    (tmp_path/'throughput-blackbox'/'worlds'/'undeclared').mkdir(parents=True)
    with pytest.raises(ValueError,match='undeclared'):
        audit.analyze(tmp_path,expected_source='fixture-source')


def test_controller_history_update_forgery_is_rejected(tmp_path):
    fixture(tmp_path)
    path = tmp_path/'efficiency-nested'/'campaign'/'native-nested-state.json'
    state = json.loads(path.read_text())
    state['records'][2]['request']['history'] = []
    save(path,state)
    with pytest.raises(ValueError):
        audit.analyze(tmp_path,expected_source='fixture-source')


def _real_adapter_fixture(root,values):
    """Actual adapter with a scripted trusted model; it performs no HTTP."""
    generator_module = pytest.importorskip('utopia.optimization.native_search_generator_v14')
    class Scripted:
        def __init__(self):
            self.values = iter(values)
            self.calls = 0
        def generate(self,**kwargs):
            self.calls += 1
            value = next(self.values)
            if isinstance(value,BaseException):
                raise value
            return value,[{'role':'assistant','content':json.dumps(value)}]
    initial = tiny_parent()
    world = {'source_commit':'fixture-source','model_digest':'fixture-model','corpus_sha256':'fixture-corpus'}
    controller = NativeAdaptiveDesignCampaign(root/'campaign',initial_system=initial,
        loss_spec=list(audit.objective_specs().values())[0],seeds=[42],world_binding=world,
        strategies={'automatic':{'kind':'scripted-software-QA'}},mode='blackbox',seed=42)
    model = Scripted()
    provider = {'model':'qwen3:8b','model_digest':'fixture-model','image_id':'sha256:'+'a'*64}
    adapter = generator_module.LLMVocabularyGenerator(model,root/'authoring',image_id=provider['image_id'],
        provider_binding=provider,max_attempts=2,max_tokens=4096)
    return controller,adapter,model,provider


def _authored_output():
    return {'operations':[{'op':'replace','path':'/initial_state/coordinate','value':1.25}],
        'factors':[],'continuous':[],'rationale':'Scripted audit contract, not model or scientific evidence'}


def test_successful_actual_adapter_keeps_exact_raw_model_operations_and_new_parent(tmp_path):
    controller,adapter,model,provider = _real_adapter_fixture(tmp_path,[_authored_output()])
    record = controller.advance(simulation_factory=fail_factory,generators={'automatic':adapter},count=1)
    proof = audit.audit_designer(tmp_path/'authoring',[record],{'max_attempts':2,'max_tokens':4096},
        provider_binding=provider)
    assert model.calls == proof['dispatch_intents'] == proof['known_responses'] == proof['valid_drafts'] == 1
    assert record['definition']['base_patch']['operations'] == _authored_output()['operations']
    assert record['draws'][0]['suggestion']['candidate']['initial_state']['coordinate'] == 1.25
    assert record['observations'][0]['loss'] is None


def test_actual_adapter_bounded_invalid_first_draft_and_second_valid_are_both_audited(tmp_path):
    controller,adapter,model,provider = _real_adapter_fixture(tmp_path,[{'malformed':'first'},_authored_output()])
    record = controller.advance(simulation_factory=fail_factory,generators={'automatic':adapter},count=1)
    proof = audit.audit_designer(tmp_path/'authoring',[record],{'max_attempts':2,'max_tokens':4096})
    assert proof['dispatch_intents'] == proof['known_responses'] == 2 and proof['valid_drafts'] == 1
    assert [a['status'] for a in proof['proofs'][0]['attempts']] == ['invalid','valid']


def test_actual_adapter_preflight_errors_are_not_invented_known_model_responses(tmp_path):
    controller,adapter,model,provider = _real_adapter_fixture(tmp_path,[RuntimeError('scripted preflight'),RuntimeError('scripted preflight')])
    record = controller.advance(simulation_factory=fail_factory,generators={'automatic':adapter},count=1)
    proof = audit.audit_designer(tmp_path/'authoring',[record],{'max_attempts':2,'max_tokens':4096})
    assert proof['dispatch_intents'] == 2 and proof['known_responses'] == 0
    assert record['generation_error'] and record['draws'] == []


def test_actual_adapter_interrupted_response_remains_unknown_and_is_not_redispatched(tmp_path):
    controller,adapter,model,provider = _real_adapter_fixture(tmp_path,[KeyboardInterrupt(),_authored_output()])
    with pytest.raises(KeyboardInterrupt):
        controller.advance(simulation_factory=fail_factory,generators={'automatic':adapter},count=1)
    record = controller.advance(simulation_factory=fail_factory,generators={'automatic':adapter},count=1)
    proof = audit.audit_designer(tmp_path/'authoring',[record],{'max_attempts':2,'max_tokens':4096})
    assert model.calls == 2 and proof['dispatch_intents'] == 2 and proof['known_responses'] == 1
    assert proof['interrupted_response_unknown'] == 1
    assert proof['proofs'][0]['attempt_records'][0] is None


def test_pending_interrupted_authoring_can_be_audited_without_charging_a_world(tmp_path):
    controller,adapter,model,provider = _real_adapter_fixture(tmp_path,[KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        controller.advance(simulation_factory=fail_factory,generators={'automatic':adapter},count=1)
    before = audit._inventory(tmp_path)
    proof = audit.audit_designer(tmp_path/'authoring',[],{'max_attempts':2,'max_tokens':4096},
        pending=controller.state['pending'])
    assert proof['dispatch_intents'] == proof['interrupted_response_unknown'] == 1
    assert proof['known_responses'] == 0 and proof['proofs'][0]['result'] is None
    assert proof['proofs'][0]['definition_consumed'] is False
    assert controller.state['records'] == [] and audit._inventory(tmp_path) == before


def test_duplicate_raw_durable_record_keys_are_not_silently_collapsed(tmp_path):
    fixture(tmp_path)
    path = tmp_path/'plan.json'
    text = path.read_text()
    # Deliberately corrupt a raw fixture without constructing a new outcome.
    path.write_text(text.replace('"seed": 42','"seed": 42, "seed": 42',1))
    with pytest.raises(ValueError,match='Duplicate JSON key'):
        audit.analyze(tmp_path,expected_source='fixture-source')


def test_zero_scientist_http_adapter_keeps_missing_wire_file_missing_and_raw_unchanged(tmp_path):
    binding = {'model':'scripted-no-model','fixture':True}
    path = tmp_path/'replies'/'responses.sqlite'
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE metadata (binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)',(json.dumps(binding),))
        db.execute('CREATE TABLE replies (identity TEXT)')
    before = audit._inventory(tmp_path)
    proof = audit.zero_http_response_proofs(tmp_path,binding,[0,0],complete=True,protocol={},classification=audit.FIXTURE)
    assert proof['researcher_responses'] == proof['wire_requests'] == 0
    assert proof['wire_sha256'] is None and not (tmp_path/'wire-requests.jsonl').exists()
    assert audit._inventory(tmp_path) == before
    assert audit.audit_native_run_v13.__globals__['response_proofs'] is audit.original_response_proofs
    assert audit.audit_native_run_v14.__globals__['response_proofs'] is audit.zero_http_response_proofs
    with pytest.raises(ValueError,match='missing wire'):
        audit.zero_http_response_proofs(tmp_path,binding,[1],complete=False,protocol={},classification=audit.FIXTURE)
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO replies VALUES (?)',('unmatched-response',))
    with pytest.raises(ValueError,match='missing wire'):
        audit.zero_http_response_proofs(tmp_path,binding,[],complete=False,protocol={},classification=audit.FIXTURE)


def test_full_runtime_plan_request_specific_world_and_progress_join_with_scripted_adapter(tmp_path):
    """Real runtime/adapter, scripted author and failed factory: no native worlds."""
    runtime = pytest.importorskip('utopia.optimization.native_search_v14')
    generator_module = pytest.importorskip('utopia.optimization.native_search_generator_v14')
    plan,_ = fixture(tmp_path/'seed-schema',terminal=False)
    source = 'a'*40
    provider = {'model':'qwen3:8b','model_digest':'b'*64,'corpus_sha256':'c'*64,
        'dataset_identity':{'kind':'scripted-contract-no-worlds'},'corpus_years':4,'image_id':'sha256:'+'d'*64}
    plan['source_commit'] = source
    plan['world'].update(provider,source_commit=source)
    root = tmp_path/'raw'
    class Scripted:
        def generate(self,**kwargs):
            value = _authored_output()
            return value,[{'role':'assistant','content':json.dumps(value)}]
    for entry in plan['runs']:
        directory = root/entry['directory']
        frozen = runtime.make_search_plan(entry['request'],source_commit=source,provider_binding=provider)
        controller = runtime.NativeSearchController(directory,plan=frozen,plan_sha256=digest(frozen))
        generator = generator_module.LLMVocabularyGenerator(Scripted(),directory/'authoring',
            image_id=provider['image_id'],provider_binding=provider,max_attempts=2,max_tokens=4096)
        while not controller.complete:
            controller.advance(simulation_factory=fail_factory,generator=generator)
        save(directory/'progress.json',controller.projection(search_id=entry['id'],status='complete'))
    save(root/'plan.json',plan)
    before = audit._inventory(root)
    first = audit.analyze(root,expected_source=source)
    second = audit.analyze(root,expected_source=source)
    assert first == second and before == audit._inventory(root)
    assert first['classification'] == audit.FIXTURE and first['consumed_native_slots'] == 8
    assert first['physical_native_worlds'] == 0 and first['designer_costs']['valid_drafts'] == 6
    for entry in plan['runs']:
        run = first['runs'][entry['id']]
        assert run['binding']['world']['request_sha256'] == digest(entry['request'])
        assert run['runtime_progress']['budget']['remaining'] == 0


def test_authored_pointer_diagnostics_follow_prior_edits_without_repairing_or_mutating():
    parent = {'items':[0,1,2]}
    operations = [{'op':'remove','path':'/items/0'},
        {'op':'replace','path':'/items/2','value':'def step(context): raise RuntimeError("NEVER_EXECUTE")'},
        {'op':'add','path':'/items/-','value':9}]
    before = deepcopy(parent),deepcopy(operations)
    proof = audit.operation_pointer_diagnostics(parent,operations)
    assert (parent,operations) == before
    assert proof['first_address_error'] == 1
    assert proof['operations'][1]['address_trace'][-1] == {'depth':1,'token':'2','owner_kind':'list','owner_length':2}
    assert proof['operations'][1]['error']['message'] == 'array path index out of range'
    assert proof['operations'][2]['status'] == 'not-replayed-after-first-address-error'
    operations[1]['path'] = '/items/1'
    assert audit.operation_pointer_diagnostics(parent,operations)['all_addresses_applicable'] is True


def test_authored_id_address_on_array_is_explicitly_a_noncanonical_index():
    proof = audit.operation_pointer_diagnostics({'mechanisms':[{'mechanism_id':'selection'}]},
        [{'op':'replace','path':'/mechanisms/selection','value':{}}])
    assert proof['operations'][0]['error']['message'] == 'array path requires a canonical nonnegative index'
    assert proof['operations'][0]['address_trace'][-1]['owner_length'] == 1


def test_literal_newline_and_ast_copy_proofs_do_not_claim_new_algorithm_or_repair():
    from utopia.system.native_open_examples import open_native_system
    parent = open_native_system('sha256:'+'a'*64).to_dict()
    body = parent['mechanisms'][7]['parameters']['code_artifact']['source']
    tensor = parent['mechanisms'][15]['parameters']['program']['nodes']
    output = {'operations':[{'op':'replace','path':'/mechanisms/17/parameters/code_artifact/source','value':body[:-1]},
        {'op':'replace','path':'/mechanisms/19/parameters/program/nodes','value':tensor}]}
    before = deepcopy(parent),deepcopy(output)
    proof = audit.authored_payload_comparisons(parent,output)
    assert (parent,output) == before and proof['operation_values_modified'] is False
    code = proof['operations'][0]['python_source_comparisons'][0]
    assert code['literal_initial_source_matches'] == []
    assert code['initial_source_minus_one_final_newline_matches'] == ['world.selection']
    assert code['same_python_AST_initial_source_matches'] == ['world.selection']
    assert proof['operations'][1]['literal_parent_value_locations'] == ['/mechanisms/15/parameters/program/nodes']
