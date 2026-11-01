from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.audit_native_objective_v5 import audit_campaign, checkpoint_measurements
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.loss import evaluate_loss, load_loss_spec
from utopia.optimization.native_world import measure_native_world
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system

ROOT = Path(__file__).resolve().parents[2]


def measured(rounds):
    spec = legacy_world_system()
    sim = SimpleNamespace(native_system=SimpleNamespace(last_year=2, spec=spec, events=[]), num_years=2,
        paper_tracker=SimpleNamespace(papers_by_id={'p': SimpleNamespace(review_history=rounds)}),
        ecosystem=SimpleNamespace(agent_population={}))
    return measure_native_world(sim, run_id='unit')


def decision(scores, *, accepted=True, final=99999):
    return {'decision': 'accept' if accepted else 'reject', 'score': final,
            'reviews': [{'overall_score': score} for score in scores]}


def test_raw_peer_score_not_forgeable_institution_score():
    value = measured([decision([2, 4]), decision([5]), decision([], final=100), decision([9], accepted=False)])
    assert value['metrics']['native.accepted_peer_score_sum']['value'] == 8
    assert value['metrics']['native.accepted_unreviewed_decisions']['value'] == 1
    assert value['metrics']['native.accepted_decisions']['value'] == 3
    assert value['metrics']['native.review_records']['value'] == 4


@pytest.mark.parametrize('bad', [None, True, '5', float('nan'), float('inf')])
def test_bad_peer_observation_not_zero_reward_or_count_failure(bad):
    value = measured([decision([bad])])
    assert value['metrics']['native.accepted_decisions']['value'] == 1
    assert value['metrics']['native.accepted_peer_score_sum']['status'] == 'unavailable'
    utility = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    assert evaluate_loss(utility, [value])['loss'] is None
    throughput = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-throughput.json')
    assert evaluate_loss(throughput, [value])['loss'] == -1


def test_explicit_objectives_change_rank_without_a_veto_or_sign_flip():
    throughput = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-throughput.json')
    utility = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    weak = measured([decision([3])])
    strong = measured([decision([5])])
    empty = measured([])
    assert evaluate_loss(throughput, [weak])['loss'] == evaluate_loss(throughput, [strong])['loss'] == -1
    assert evaluate_loss(utility, [weak])['loss'] == pytest.approx(.30)
    assert evaluate_loss(utility, [strong])['loss'] == pytest.approx(-1.70)
    assert evaluate_loss(utility, [empty])['loss'] == 0
    assert evaluate_loss(throughput, [empty])['loss'] == 0


def test_independent_completed_checkpoint_matches_native_adapter(tmp_path, fixed_corpus):
    spec = legacy_world_system()
    sim, _ = make_sim(tmp_path / 'world', native=NativeScienceKernel(spec))
    try:
        sim.run()
        path = Path(sim.output_dir) / 'portable_checkpoint_year_6.json.gz'
        assert checkpoint_measurements(path, 'actual', spec.fingerprint) == measure_native_world(sim, run_id='actual')
        with pytest.raises(ValueError, match='fingerprint'):
            checkpoint_measurements(path, 'actual', 'wrong')
        with pytest.raises(ValueError, match='completed'):
            checkpoint_measurements(path.parent / 'portable_checkpoint_year_1.json.gz', 'actual', spec.fingerprint)
    finally:
        sim.llm.response_cache.close()


def test_campaign_audit_checks_native_evidence_and_detects_nonloss_metric_tampering(tmp_path, fixed_corpus, monkeypatch):
    from tests.runtime import test_portable_checkpoint_integration as fixture
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.optimization.native_design import NativeDesignCampaign

    spec = legacy_world_system()
    binding = deepcopy(fixture.BINDING)
    binding['cell'] = spec.fingerprint
    binding['science_config']['source_commit'] = 'scripted-native-audit-test'
    monkeypatch.setattr(fixture, 'BINDING', binding)
    loss = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-throughput.json')
    utility = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    world = {'model_digest': binding['model_revision'], 'corpus_sha256': binding['corpus_sha256'],
             'source_commit': binding['science_config']['source_commit']}
    campaign = NativeDesignCampaign(tmp_path / 'campaign', initial_system=spec,
        loss_spec=loss, seeds=[42], world_binding=world)

    def factory(system, run_seed, run_id):
        cell = tmp_path / 'runs' / run_id
        sim, _ = make_sim(cell / 'simulation', native=NativeScienceKernel(system))
        sim.llm.response_cache.close()
        sim.llm.response_cache = CompletedResponseCache(cell / 'replies/responses.sqlite', binding=binding)
        sim.output_dir = str(cell / 'simulation/checkpoints/native-design')
        Path(sim.output_dir).mkdir(parents=True)
        return sim

    result = campaign.advance(simulation_factory=factory)
    assert result['observation']['status'] == 'complete'
    (tmp_path / 'completion.json').write_text(json.dumps({'budget': 1}))
    before = campaign.path.read_bytes()
    report = audit_campaign(tmp_path, loss, {utility['id']: utility})
    assert report['loss_path'] == [result['observation']['loss']]
    assert report['rows'][0]['cross_objective'][utility['id']]['status'] == 'complete'
    assert campaign.path.read_bytes() == before
    document = json.loads(before)
    document['records'][0]['observation']['metadata']['measurements'][0]['metrics']['native.accepted_peer_score_sum']['value'] += 1
    campaign.path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match='reconstructed measurements'):
        audit_campaign(tmp_path, loss)
