"""Static builder/native primitive semantics; never execute institution source."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utopia.agents.base_agent import SimulationAgent
from utopia.config import SIMULATION_CONFIG
from utopia.funding.accounting import ResourceLedger
from utopia.optimization.native_institution_workflow_domain_v6 import require_institution_workflow_candidate
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.system import ChannelKind
from utopia.system.native_planning_controls import planning_controls
from utopia.system.native_resource_transfers import apply_native_resource_transfers
from utopia.system.native_terminal_cost_controls_v1 import HEADER,TERMINAL_BRANCH,terminal_consolidation_control
from utopia.system.runtime import DeliveredValue

ROOT=Path(__file__).resolve().parents[2]
IMAGE='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'
COMPONENT_YEAR=1


@pytest.fixture
def parent():
    return post_funding_cost_control(planning_controls(IMAGE,seed=61001)['assignment-reserve21-no-review-all'])


def test_literal_source_only_control_remains_in_original_effect_scope(parent):
    before=parent.to_dict(); candidate=terminal_consolidation_control(parent,terminal_year=4)
    assert parent.to_dict()==before
    assert require_institution_workflow_candidate(parent,candidate)
    changed=candidate.to_dict()
    a=next(n for n in before['mechanisms'] if n['mechanism_id']=='developer-liquidity-director')
    b=next(n for n in changed['mechanisms'] if n['mechanism_id']=='developer-liquidity-director')
    old=a['parameters']['code_artifact']['source']; new=b['parameters']['code_artifact']['source']
    assert new==HEADER+TERMINAL_BRANCH.replace('TERMINAL_PERIOD','4')+old[len(HEADER):]
    ast.parse(new)  # Parse only; never execute institution source on host.
    b['parameters']['code_artifact']['source']=old
    assert changed==before


@pytest.mark.parametrize('year',[True,0,-1,4.0])
def test_no_implicit_terminal_horizon_or_invalid_year(parent,year):
    before=parent.to_dict()
    with pytest.raises(ValueError,match='positive integer'):
        terminal_consolidation_control(parent,terminal_year=year)
    assert parent.to_dict()==before


class Actor:
    """SCRIPTED handoff state using the actual native resource-update method."""
    can_author=True
    update_resources=SimulationAgent.update_resources
    def __init__(self,identity,resources):
        self.id=identity; self.resources=resources; self.is_active=True
    def get_type(self): return 'university'


def handoff():
    # Measured year4 balance vector in a SCRIPTED standalone year1 handoff.
    # Native ledgers must begin at1. This is NOT the original year4 ledger.
    r=json.loads((ROOT/'research/results/native-legacy-topic-pilot-closed-v1.json').read_text())
    rows=r['original_resource_instrument_categories']['core-plus-related'][-1]['reconciled_authors']
    actors={a['researcher_id']:Actor(a['researcher_id'],a['closing_balance']+a['annual_research_cost']) for a in rows}
    ledger=ResourceLedger(); ledger.start_year(COMPONENT_YEAR,actors)
    kernel=SimpleNamespace(_simulation=SimpleNamespace(ecosystem=SimpleNamespace(agent_population=actors),
        resource_ledger=ledger),_frame={},events=[])
    return actors,ledger,kernel


def charge_and_close(actors,ledger):
    fee=SIMULATION_CONFIG['conference']['annual_cost']; assert fee==10
    # Original resource/ledger primitives, not Simulation._charge_annual_costs.
    for actor in actors.values():
        assert actor.is_active
        actor.update_resources(-fee,category='annual_research_cost',year=COMPONENT_YEAR,project='SCRIPTED-component-project')
    ledger.close_year(COMPONENT_YEAR,actors)
    return ledger.reconcile(COMPONENT_YEAR,actors,require_closed=True)


def test_actual_transfer_clipping_ledger_primitives_expose_collected_vs_uncollected_cost():
    actors,ledger,kernel=handoff(); before=sum(a.resources for a in actors.values())
    assert len(actors)==5 and before==80
    banker=max(actors,key=lambda aid:(actors[aid].resources,aid)); commands=[]
    for aid,a in sorted(actors.items()):
        if aid!=banker:
            commands.append(DeliveredValue(ChannelKind.RESOURCE,'SCRIPTED-transfer',
                {'transaction_id':'SCRIPTED-terminal-'+aid,'from_actor':aid,'to_actor':banker,'amount':a.resources},
                (aid,banker),(),('SCRIPTED-producer-event',),'SCRIPTED-producer','funds',COMPONENT_YEAR,COMPONENT_YEAR))
    context=SimpleNamespace(inputs={'transfers':tuple(commands)},period=COMPONENT_YEAR,state={})
    result=apply_native_resource_transfers(kernel,context)
    assert len(result.events)==4 and sum(a.resources for a in actors.values())==before
    assert all(a.is_active for a in actors.values())  # Exact zero is not deactivation.
    rows=charge_and_close(actors,ledger)
    assert sum(r['annual_research_cost'] for r in rows)==10
    assert sum(r['uncollected_cost'] for r in rows)==40
    assert sum(a.resources for a in actors.values())==70 and sum(a.is_active for a in actors.values())==1
    assert all(r['residual']==0 for r in rows)
    # Not a Docker run of the new source or native-world T/U/C evidence.


def test_same_isolated_handoff_without_transfer_collects_all_five_charges():
    actors,ledger,_=handoff(); rows=charge_and_close(actors,ledger)
    assert sum(r['annual_research_cost'] for r in rows)==50
    assert sum(r['uncollected_cost'] for r in rows)==0
    assert sum(a.resources for a in actors.values())==30 and all(a.is_active for a in actors.values())
