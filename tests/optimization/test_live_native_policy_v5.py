import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location('live_native_policy_v5',
    Path(__file__).resolve().parents[2] / 'scripts/run_live_native_policy_v5.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def test_checkpoint_counts_derive_domain_state_not_reported_loss():
    state = {'paper_tracker': {'papers': [{'review_history': [
        {'decision': 'accept', 'reviews': [{}, {}]},
        {'decision': 'reject', 'reviews': [{}]}]}]},
        'ecosystem_data': {'agents': [
            {'can_author': True, 'is_active': False, 'resources': 3},
            {'can_author': True, 'is_active': True, 'resources': 5},
            {'can_author': False, 'is_active': True, 'resources': 100}]},
        'native_system': {'events': [{'event_type': 'native.system.context_delivered'},
                                     {'event_type': 'other'}]}}
    assert pilot.checkpoint_counts(state) == {
        'native.accepted_decisions': 1, 'native.rejected_decisions': 1,
        'native.review_records': 3, 'native.final_active_authors': 1,
        'native.final_author_resources': 8, 'native.institutional_context_deliveries': 1}


def test_prepare_rejects_unrelated_final_design(tmp_path):
    import json
    source, selected = tmp_path / 'source.json', tmp_path / 'winner.json'
    source.write_text(json.dumps({'records': [{'suggestion': {'candidate': {'old': True}}}]}))
    selected.write_text('{}')
    with pytest.raises(ValueError, match='exact archived final proposal'):
        pilot.prepare(source, selected, tmp_path / 'output')


def test_frozen_seed_draws_are_preserved():
    import json
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_discrete_policy import NativeDiscretePolicySearch
    from utopia.system.native_kernel import legacy_world_system
    root = Path(__file__).resolve().parents[2]
    designs = [legacy_world_system(seed=1301).to_dict(),
        json.loads((root / 'research/artifacts/native-open-source-v3-selected-system.json').read_text())]
    loss = load_loss_spec(root / 'research/objectives/losses/native-accepted-count-engineering-v1.json')
    search = NativeDiscretePolicySearch(designs, loss_spec=loss, seed=42)
    search.ask(2)
    # The preregistered seed happens to repeat the winner; never redraw for a
    # balanced or favorable-looking comparison.
    assert [row['action'] for row in search.pending] == [1, 1]
    assert NativeDiscretePolicySearch.from_state(search.state_dict(), loss_spec=loss).state_dict() == search.state_dict()
