"""Actual native method semantics, not an audited trajectory or policy benefit."""
from types import SimpleNamespace

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.system.test_native_science_kernel import make_sim
from utopia.agents.base_agent import SimulationAgent
from utopia.optimization.native_active_founders import from_states
from utopia.simulation import Simulation


def test_native_cost_and_funding_closure_flags_are_not_positive_resource_counts(tmp_path,fixed_corpus):
    sim,calls=make_sim(tmp_path/'semantic-unit')
    try:
        sim.initialize_agents()
        authors=sorted(sim.ecosystem.get_available_authors(),key=lambda a:a.id)
        assert len(authors)==4
        for actor,balance in zip(authors,(0,10,11,20)):
            actor.resources=balance;actor.is_active=True
            actor.project_start_year=0;actor.project_end_year=1
        authors[0].project_end_year=0  # idle: native annual cost skips this actor
        ids={a.id for a in authors}
        def view(year):
            return {'year':year,'phase':0 if year==0 else 5,
                'native_system':{'last_year':year,'spec':{'SCRIPTED':'unit flag instrument only'}},
                'portable':{'contract':{'binding':{'SCRIPTED':'not an original checkpoint'}}},
                'ecosystem_data':{'agents':[{'id':a.id,'can_author':a.can_author,
                    'is_active':a.is_active,'resources':a.resources} for a in authors]}}
        initial=view(0)
        # Explicitly call the real base methods, not the fixture's feedback
        # overlay. No run(), model response or checkpoint audit is claimed.
        Simulation._charge_annual_costs(sim,1)
        assert [a.resources for a in authors]==[0,0,1,10]
        assert all(a.is_active for a in authors)
        results={};Simulation._finish_funding_cycle(sim,1,results,{},[])
        assert [a.is_active for a in authors]==[True,True,False,False]
        assert ids<={a.id for a in sim.ecosystem.agent_population.values()}
        assert results['ecosystem_metrics']['active_agents']==4  # historical capability counter
        assert len(sim.ecosystem.get_available_authors())==2
        assert sum(a.is_active and a.resources>0 for a in authors)==0
        assert from_states([initial,view(1)])['value']==2  # P adds no resource threshold
        assert not calls
    finally:sim.llm.response_cache.close()


def test_exact_zero_does_not_guarantee_next_debit_or_automatic_reactivation():
    actor=SimpleNamespace(id='SCRIPTED-resource-semantics',resources=10,is_active=True)
    SimulationAgent.update_resources(actor,-10)
    assert (actor.resources,actor.is_active)==(0,True)
    SimulationAgent.update_resources(actor,-1)
    assert (actor.resources,actor.is_active)==(0,False)
    SimulationAgent.update_resources(actor,20)
    assert (actor.resources,actor.is_active)==(20,False)
