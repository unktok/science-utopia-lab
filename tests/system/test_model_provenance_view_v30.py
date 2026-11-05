"""SCRIPTED alpha-reference invariance, not scientific institution invention."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest

from utopia.system.model_provenance_view import FIELDS, provenance_view, render_provenance_view
from utopia.system.native_kernel import institutional_context_prompt
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


def messages(a='audit-A', b='audit-B', m='message-X'):
    return [{'message_id': m, 'input_event_ids': [a, b, a],
        'previous_receipt_sha256': None, 'domain_content_sha256': 'opaque-state-hash',
        'source': 'real-institution', 'received_year': 1, 'emitted_year': 1,
        'payload': {'scientific_content': ['new result', 9007199254740993, False],
            'timestamp': 'deliberately authored scientific content'},
        'artifact_ids': ['paper-A'], 'unknown_future_field': {'loss': None}},
        {'message_id': 'message-Y', 'input_event_ids': [b], 'source': 'real-institution',
         'payload': {'finding': 2}, 'received_year': 2}]


def test_bijective_audit_identifier_renaming_changes_no_model_view_or_payload():
    original = messages(); saved = deepcopy(original)
    renamed = messages('renamed-A', 'renamed-B', 'renamed-message-X')
    first, inverse = provenance_view(original)
    second, changed_inverse = provenance_view(renamed)
    assert first == second and inverse != changed_inverse
    assert original == saved
    assert first['messages'][0]['payload'] == original[0]['payload']
    assert first['messages'][0]['unknown_future_field'] == {'loss': None}
    assert first['messages'][0]['artifact_ids'] == ['paper-A']
    restored = deepcopy(first['messages'])
    for item in restored:
        for key in FIELDS:
            value = item.get(key)
            if isinstance(value, str) and value in inverse:
                item[key] = inverse[value]
            elif key == 'input_event_ids' and isinstance(value, list):
                item[key] = [inverse.get(v, v) for v in value]
    assert restored == original


def test_reference_equality_multiplicity_order_and_real_content_changes_are_not_hidden():
    original = messages(); view = provenance_view(original)[0]
    refs = view['messages'][0]['input_event_ids']
    assert refs[0] == refs[2] != refs[1]
    assert refs[1] == view['messages'][1]['input_event_ids'][0]
    for key, value in [('payload', {'finding': 'actually changed'}), ('source', 'new producer'), ('received_year', 3)]:
        changed = deepcopy(original); changed[0][key] = value
        assert provenance_view(changed)[0] != view
    changed = deepcopy(original); changed[1]['input_event_ids'] = ['a different causal reference']
    assert provenance_view(changed)[0] != view


def test_intentionally_exposed_hashes_and_cross_references_remain_literal_and_resolvable():
    original = messages()
    original[0]['payload']['explicit_reference'] = original[0]['input_event_ids'][0]
    view, inverse = provenance_view(original)
    assert view['messages'][0]['payload'] == original[0]['payload']
    alias = view['messages'][0]['input_event_ids'][0]
    assert view['explicit_reference_values'][alias] == inverse[alias] == 'audit-A'


def test_default_researcher_prompt_changes_no_raw_record_and_normalizes_only_opaque_metadata():
    original = messages(); saved = deepcopy(original)
    left, right = SimpleNamespace(institutional_context=original), SimpleNamespace(
        institutional_context=messages('different-A', 'different-B', 'different-message'))
    assert institutional_context_prompt(left) == institutional_context_prompt(right)
    assert 'new result' in institutional_context_prompt(left)
    assert 'audit-A' not in institutional_context_prompt(left)
    assert original == saved
    assert institutional_context_prompt(SimpleNamespace()) == ''


def test_records_without_audit_identifiers_keep_exact_original_renderer_bytes():
    records = [{'payload': {'linefeeds': 'a\nb', 'quotation': '"', 'number': 9007199254740993}}]
    assert render_provenance_view(records) == json.dumps(records[0], ensure_ascii=False, sort_keys=True)


def test_unknown_fields_and_non_identifier_metadata_values_are_never_repaired():
    records = [{'input_event_ids': [None, 4], 'message_id': None,
        'payload': {'hash': 'an actual scientific value'}, 'new_metadata': ['must remain', None]}]
    view, mapping = provenance_view(records)
    assert not mapping and view['messages'] == records


def test_work_snapshot_keeps_raw_audit_records_and_legacy_renderer_but_projects_new_model_view():
    from utopia.system.model_provenance_view import SCHEMA
    from utopia.system.native_researcher_work import render_work_prompt
    from utopia.system.runtime import GraphRuntimeError
    request = {'instruction': 'SCRIPTED custom scientific work', 'content': {'question': 'unchanged'}}
    old = {'persona_prompt': 'SCRIPTED same persona', 'memory_prompt': 'SCRIPTED same memory',
        'institutional_context': messages(), 'artifact_records': [{'id': 'actual-scientific-artifact'}]}
    renamed = deepcopy(old); renamed['institutional_context'] = messages('other-A', 'other-B', 'other-message')
    saved = deepcopy(old)
    # Old stored receipts reconstruct their original literal snapshot bytes.
    assert render_work_prompt(request, old) != render_work_prompt(request, renamed)
    assert 'audit-A' in render_work_prompt(request, old)
    left, right = {**old, 'model_provenance_view': SCHEMA}, {**renamed, 'model_provenance_view': SCHEMA}
    assert render_work_prompt(request, left) == render_work_prompt(request, right)
    assert 'audit-A' not in render_work_prompt(request, left)
    assert 'actual-scientific-artifact' in render_work_prompt(request, left)
    assert old == saved
    with pytest.raises(GraphRuntimeError, match='unknown'):
        render_work_prompt(request, {**old, 'model_provenance_view': 'unrecognized'})


@pytest.mark.parametrize('edit_kind', ['late-unused-version', 'v31-unused-adapter-parameters'])
@pytest.mark.parametrize('clock_mode', ['shared', 'independent'])
def test_original_19_node_world_inert_late_parameter_does_not_change_any_scientist_request(
        tmp_path, fixed_corpus, monkeypatch, edit_kind, clock_mode):
    """SCRIPTED backend/corpus, real native phases and pinned Docker; not science evidence."""
    from dataclasses import replace
    from tests.runtime.test_portable_checkpoint_integration import BINDING, DIRECTION, FakeHTTPModel, SmallRealSimulation, seed
    from utopia.agents.researcher_agents import UniversityResearcher
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.system.native_open_examples import open_native_system
    executor = DockerCodeExecutor(timeout=60.)
    parent = open_native_system(executor.image_id)
    nodes = list(parent.mechanisms)
    if edit_kind == 'late-unused-version':
        node = nodes[7]
        nodes[7] = replace(node, parameters={**node.parameters, 'version': 1})
    else:
        # Exact final V31 a2 efficiency G0 metadata, not an invented policy.
        authored = {'world.review': {'required_reviewers': 2},
                    'world.submission': {'pre_screening_enabled': True}}
        nodes = [replace(node, parameters=authored[node.mechanism_id])
                 if node.mechanism_id in authored else node for node in nodes]
    inert = replace(parent, mechanisms=tuple(nodes))
    assert parent.fingerprint != inert.fingerprint
    assert len(parent.mechanisms) == len(inert.mechanisms) == 19
    assert len(parent.connections) == len(inert.connections) == 27
    assert parent.mechanisms[7].parameters['code_artifact'] == inert.mechanisms[7].parameters['code_artifact']
    results = []
    for run_index, (label, spec) in enumerate([('original', parent), ('inert', inert)]):
        clock = 1234567890. + (run_index * 86400. if clock_mode == 'independent' else 0.)
        monkeypatch.setattr('time.time', lambda value=clock: value)
        seed(); calls = []; root = tmp_path / label
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        model = FakeHTTPModel(root, calls)
        class FiveResearcherSimulation(SmallRealSimulation):
            def initialize_agents(self):
                super().initialize_agents()
                self.ecosystem.add_agent(UniversityResearcher('researcher-4', 'university-4',
                    funding_level=1000, expertise=[DIRECTION], llm=self.llm))
                self._record_initial_university_count()
        sim = FiveResearcherSimulation(root, model)
        sim.args.expected_founders = 5
        sim.num_years = 2
        sim.native_system = NativeScienceKernel(spec, code_executor=executor)
        try:
            sim.run()
            results.append({'calls': deepcopy(calls), 'papers': sim.paper_tracker.to_dict()['papers'],
                'events': [event.to_dict() for event in sim.native_system.events],
                'raw_contexts': [deepcopy(getattr(a, 'institutional_context', []))
                    for a in sim.ecosystem.agent_population.values()]})
        finally:
            model.response_cache.close()
    assert len(results[0]['calls']) == len(results[1]['calls']) == 85
    assert results[0]['calls'] == results[1]['calls']
    if clock_mode == 'shared':
        assert results[0]['papers'] == results[1]['papers']
    else:
        # Raw host metadata MUST remain different, not be rewritten to pass.
        assert results[0]['papers'] != results[1]['papers']
        projected = []
        for result in results:
            papers = deepcopy(result['papers'])
            for paper in papers:
                for history in paper['review_history']:
                    for review in history.get('reviews', []):
                        review.pop('review_time', None)
            projected.append(papers)
        assert projected[0] == projected[1]
    # Audit identities stay cell-bound and are NOT rewritten to make this pass.
    assert results[0]['events'] != results[1]['events']
    assert results[0]['raw_contexts'] != results[1]['raw_contexts']
