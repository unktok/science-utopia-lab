"""Actual native phases; only corpus/retrieval/HTTP are scripted for exact QA."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from tests.runtime.test_portable_checkpoint_integration import (
    FakeHTTPModel, SmallRealSimulation, fixed_corpus, seed, science_snapshot,
)
from utopia.agents.research_direction import build_direction_prompt
from utopia.runtime.checkpointing import PortableStop, read_portable_checkpoint
from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
                           MechanismSpec, PortSpec, ScheduleSpec)
from utopia.system.native_kernel import (CONTEXT_RECEIVER, NativeScienceKernel,
    LLM_INSTITUTION, WORLD_ARTIFACT, add_context_receiver, legacy_world_system)
from utopia.system.runtime import GraphRuntimeError, MechanismEvent, MechanismResult, MechanismValue


def make_sim(root, *, native=None, model_class=FakeHTTPModel, after_effects=False):
    calls = []
    model = model_class(root, calls)
    sim = SmallRealSimulation(root, model, after_effects=after_effects)
    sim.native_system = native
    return sim, calls


def original_science(sim):
    state = science_snapshot(sim)
    state.pop("native_system", None)
    state["portable"]["contract"].pop("native_system", None)
    return state


def test_original_world_is_an_exact_instance(tmp_path, fixed_corpus, monkeypatch):
    # Native legacy resubmission prompts include operational review timestamps.
    # Freeze clocks in BOTH coordinators, rather than normalize away prompt differences.
    monkeypatch.setattr("time.time", lambda: 1234567890.0)
    reference, old_calls = make_sim(tmp_path / "old")
    reference.run()
    expected = original_science(reference)
    seed()
    native, new_calls = make_sim(tmp_path / "native", native=NativeScienceKernel(legacy_world_system()))
    native.run()
    assert original_science(native) == expected
    assert [payload for _, payload in old_calls] == [payload for _, payload in new_calls]
    assert native.native_system.last_year == 6
    assert len(native.native_system.events) == 13 * 6
    reference.llm.response_cache.close()
    native.llm.response_cache.close()


def test_long_projects_allow_empty_publication_years_in_both_coordinators(tmp_path, fixed_corpus, monkeypatch):
    from tests.runtime import test_portable_checkpoint_integration as fixture
    from utopia.simulation import Simulation
    from types import MethodType
    monkeypatch.setattr(fixture, 'DIRECTION', next(d for d in fixture.AVAILABLE_DIRECTIONS if d.years == 2))
    for label, kernel in [('original', None), ('native', NativeScienceKernel(legacy_world_system()))]:
        seed()
        sim, _ = make_sim(tmp_path / label, native=kernel)
        # Exercise original funding, not the fixture subclass's feedback overlay.
        sim._run_phase_5_update_funding = MethodType(Simulation._run_phase_5_update_funding, sim)
        sim.run_one_round = MethodType(Simulation.run_one_round, sim)
        sim.run()
        assert sim.yearly_results[0]['decisions'] == {'total_accepted': 0, 'total_rejected': 0}
        assert any(r['decisions']['total_accepted'] for r in sim.yearly_results[1:])
        sim.llm.response_cache.close()


def test_no_citation_candidates_means_no_model_request(tmp_path, fixed_corpus):
    sim, calls = make_sim(tmp_path / 'empty-citations')
    sim.initialize_agents()
    papers = [{'id': 'new-paper', 'author_id': 'researcher-0'}]
    result, fmt = sim._select_citations_batch(2, {}, papers, [0], [[]], 'regular', accepted_ids=set())
    assert result == {0: []} and fmt is None
    assert sim._select_citations_sequential(None, None, None, [], None) == []
    assert not calls
    sim.llm.response_cache.close()


def extension_spec(*, connected=True, latency=0):
    base = legacy_world_system()
    producer = MechanismSpec("replication-commons", MechanismFamily.CUSTOM, "test.native.replication.v1",
        inputs=(PortSpec("observations", ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec("plans", ChannelKind.ARTIFACT, "replication-plan"),))
    base = replace(base, artifact_types=(*base.artifact_types, ArtifactTypeSpec("replication-plan")),
        mechanisms=(*base.mechanisms, producer), schedules=(*base.schedules, ScheduleSpec(producer.mechanism_id, 190)),
        connections=(*base.connections, ConnectionSpec("world.publication", "world", producer.mechanism_id,
                       "observations", ChannelKind.ARTIFACT)))
    base = add_context_receiver(base, source=producer.mechanism_id, source_port="plans", latency=latency)
    if not connected:
        base = replace(base, connections=tuple(c for c in base.connections if c.target_mechanism != "researcher-context"))
    return base


def register_replication(kernel, registry):
    def producer(context):
        observation = context.inputs["observations"][0].payload
        # Native artifacts and authors, not fixed scores or invented paper IDs.
        papers = observation["papers"]["papers"]
        outputs = []
        for paper in papers:
            if paper["year"] != context.period:
                continue
            authors = paper["author_id"] if isinstance(paper["author_id"], list) else [paper["author_id"]]
            outputs.append(MechanismValue({"kind": "replication-plan", "paper_id": paper["id"],
                "abstract": paper["abstract"], "recommendation": "REPLICATION_COMMONS_NATIVE_TEST"},
                actor_ids=tuple(authors), artifact_ids=(paper["id"],)))
        return MechanismResult(outputs={"plans": tuple(outputs)}, next_state={
            "cycles": context.state.get("cycles", 0) + 1}, events=(MechanismEvent(
                "native.test.replication_created", payload={"count": len(outputs)}),))
    registry.register("test.native.replication.v1", 1, producer)


def test_new_protocol_reaches_actual_next_year_model_prompts(tmp_path, fixed_corpus):
    sim, calls = make_sim(tmp_path / "linked", native=NativeScienceKernel(extension_spec(), registry_extension=register_replication))
    sim.run()
    directions = {year: [payload for (ctx, _, _), payload in calls if ctx[:2] == ("phase1_directions", year)]
                  for year in (1, 2)}
    assert all("REPLICATION_COMMONS_NATIVE_TEST" not in json.dumps(p) for p in directions[1])
    assert any("REPLICATION_COMMONS_NATIVE_TEST" in json.dumps(p) for p in directions[2])
    events = [e for e in sim.native_system.events if e.event_type == "native.system.context_delivered"]
    assert events and all(e.provenance["input_event_ids"] for e in events)
    assert any(getattr(a, "institutional_context", None) for a in sim.ecosystem.get_available_authors())
    sim.llm.response_cache.close()


@pytest.mark.parametrize("connected,latency,first_year", [(False, 0, None), (True, 1, 3)])
def test_edge_removal_and_latency_have_real_input_consequences(tmp_path, fixed_corpus, connected, latency, first_year):
    sim, calls = make_sim(tmp_path / "world", native=NativeScienceKernel(
        extension_spec(connected=connected, latency=latency), registry_extension=register_replication))
    sim.run()
    years = [ctx[1] for (ctx, _, _), payload in calls if ctx[0] == "phase1_directions"
             and "REPLICATION_COMMONS_NATIVE_TEST" in json.dumps(payload)]
    assert (min(years) if years else None) == first_year
    sim.llm.response_cache.close()


def test_native_graph_context_and_delayed_queue_resume(tmp_path, fixed_corpus):
    spec = extension_spec(latency=1)
    reference, calls = make_sim(tmp_path / "reference", native=NativeScienceKernel(spec, registry_extension=register_replication))
    reference.run()
    expected = science_snapshot(reference)
    seed()
    stopped, _ = make_sim(tmp_path / "resume", native=NativeScienceKernel(spec, registry_extension=register_replication), after_effects=True)
    with pytest.raises(PortableStop):
        stopped.run()
    stopped.llm.response_cache.close()
    resumed, _ = make_sim(tmp_path / "resume", native=NativeScienceKernel(spec, registry_extension=register_replication))
    resumed.run()
    assert science_snapshot(resumed) == expected
    assert resumed.native_system.to_dict() == reference.native_system.to_dict()
    resumed.llm.response_cache.close()
    reference.llm.response_cache.close()


def test_checkpoint_identity_and_gradient_scope_are_explicit():
    kernel = NativeScienceKernel(legacy_world_system())
    state = kernel.to_dict()
    state["system_fingerprint"] = "0" * 64
    with pytest.raises(GraphRuntimeError, match="identity"):
        NativeScienceKernel(kernel.spec, checkpoint=state)
    assert kernel.gradient_contract()["end_to_end_autograd"] is False
    assert kernel.gradient_contract()["numeric_miniature_is_not_a_substitute"] is True


def test_open_llm_institution_uses_native_transport_and_persistent_state(tmp_path, fixed_corpus):
    from openai.types.chat import ChatCompletion
    from utopia.system.native_examples import connect_native_institution
    class InstitutionModel(FakeHTTPModel):
        def reply(self, **payload):
            context = self.contexts.get(payload['extra_body']['seed'], getattr(self, 'context', None))
            if context[0][0] != 'native_institution':
                return super().reply(**payload)
            prompt = payload['messages'][-1]['content']
            observed = json.loads(prompt.split('Observed input records and your prior state:\n')[1])
            assert observed['inputs']['observations'][0]['input_event_ids']
            world = observed['inputs']['observations'][0]['payload']
            assert world['papers']['papers']
            count = observed['state'].get('cycles', 0) + 1
            data = {'outputs': {'plans': [{'payload': {'proposal': 'NATIVE_OPEN_INSTITUTION'},
                     'actor_ids': [a.id for a in self.sim.ecosystem.get_available_authors()]}]},
                    'state': {'cycles': count}}
            self.requests.append((context, payload))
            return ChatCompletion.model_validate(dict(id='native-institution', object='chat.completion',
                created=0, model=self.model_name, choices=[dict(index=0,
                message=dict(role='assistant', content=json.dumps(data)), finish_reason='stop')],
                usage=dict(prompt_tokens=5, completion_tokens=3, total_tokens=8)))
    node = MechanismSpec('open-institution', MechanismFamily.CUSTOM, LLM_INSTITUTION,
        inputs=(PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('plans', ChannelKind.ARTIFACT, 'novel-plan'),),
        parameters={'instruction': 'Invent an institutional response to the observed native papers.',
                    'output_schemas': {'plans': {'type': 'object'}}, 'state_schema': {'type': 'object'}})
    spec = connect_native_institution(legacy_world_system(), node, researcher_output='plans')
    sim, calls = make_sim(tmp_path / 'world', native=NativeScienceKernel(spec), model_class=InstitutionModel)
    sim.run()
    assert sim.native_system.graph_checkpoint['mechanism_states']['open-institution']['cycles'] == 6
    assert len([ctx for (ctx, _, _), _ in calls if ctx[0] == 'native_institution']) == 6
    assert any('NATIVE_OPEN_INSTITUTION' in json.dumps(p) for (ctx, _, _), p in calls
               if ctx[:2] == ('phase1_directions', 2))
    from utopia.replay import ArtifactBundle, convert_artifacts, validate_references
    events = convert_artifacts(ArtifactBundle.discover(Path(sim.output_dir) / 'portable_checkpoint_year_6.json.gz'))
    assert validate_references(events) == []
    assert any(e.event_type == 'native.system.llm_institution_executed' for e in events)
    sim.llm.response_cache.close()


@pytest.mark.parametrize("retain_peer_review", [True, False])
def test_replacement_code_changes_real_publication_and_future_research_context(tmp_path, fixed_corpus, retain_peer_review):
    from utopia.system.code_mechanisms import CODE_IMPLEMENTATION, CODE_SCHEMA, DockerCodeExecutor, CodeExecutionError
    try:
        executor = DockerCodeExecutor()
    except (CodeExecutionError, OSError):
        pytest.skip("local Docker required for isolated generated-source integration")
    spec = legacy_world_system()
    original = next(n for n in spec.mechanisms if n.mechanism_id == "world.selection")
    artifact = {"schema": CODE_SCHEMA, "label": "Open dissemination integration example",
        "inputs": {"after": {"type": "object"}, "observations": {"type": "object"}},
        "outputs": {"next": {"type": "object"}, "world": {"type": "object"}, "decisions": {"type": "object"}},
        "state_schema": {"type": "object"},
        "source": """def step(context):
    observed = context['inputs']['observations'][0]['payload']
    decisions = []
    for conference in observed['conferences']['conferences']:
        for paper in conference['submitted_papers']:
            reviews = conference['reviews'].get(paper['id'], [])
            score = sum(r['overall_score'] for r in reviews) / len(reviews) if reviews else 0
            decisions.append({'payload': {'paper_id': paper['id'],
                'conference_id': conference['conference_id'], 'final_score': score, 'decision': 'accept'}})
    if not decisions:
        decisions = [{'payload': {'empty_cycle': True}}]
    return {'outputs': {'next': [{'payload': {'year': context['period']}}],
            'world': [{'payload': observed}], 'decisions': decisions},
            'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""}
    replacement = replace(original, implementation=CODE_IMPLEMENTATION,
        inputs=(*original.inputs, PortSpec("observations", ChannelKind.ARTIFACT, WORLD_ARTIFACT)),
        parameters={"code_artifact": artifact, "runtime_image_id": executor.image_id})
    spec = replace(spec, mechanisms=tuple(replacement if n.mechanism_id == original.mechanism_id else n for n in spec.mechanisms),
        connections=(*spec.connections, ConnectionSpec("world.review", "world", "world.selection", "observations", ChannelKind.ARTIFACT)))
    if not retain_peer_review:
        spec = replace(spec,
            mechanisms=tuple(n for n in spec.mechanisms if n.mechanism_id != 'world.review'),
            schedules=tuple(s for s in spec.schedules if s.mechanism_id != 'world.review'),
            connections=tuple(c for c in spec.connections if c.target_mechanism != 'world.review' and c.source_mechanism != 'world.review') + (
                ConnectionSpec('world.costs', 'next', 'world.selection', 'after', ChannelKind.SIGNAL),
                ConnectionSpec('world.costs', 'world', 'world.selection', 'observations', ChannelKind.ARTIFACT)))
    sim, calls = make_sim(tmp_path / "replaced", native=NativeScienceKernel(spec, code_executor=executor))
    sim.run()
    assert sim.yearly_results[0]['decisions'] == {'total_accepted': 4, 'total_rejected': 0}
    second = [json.dumps(payload) for (ctx, _, _), payload in calls if ctx[:2] == ("phase1_directions", 2)]
    assert second and all('Your Past Rejected Papers' not in prompt for prompt in second)
    assert any('Your Past Publications' in prompt for prompt in second)
    assert sim.native_system.graph_checkpoint['mechanism_states']['world.selection']['cycles'] == 6
    if not retain_peer_review:
        assert not any(ctx[0] == 'phase3_reviews' for (ctx, _, _), _ in calls)
    sim.llm.response_cache.close()
