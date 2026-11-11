"""Reconstruct common-content measurements from native state and known raw replies."""
from pathlib import Path
from types import SimpleNamespace

from utopia.optimization.common_content_observer import CommonContentObserver,content,request_for
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest


class ColdObserver(CommonContentObserver):
    def __init__(self,directory,contract):
        if not (Path(directory)/'contract.json').is_file():raise ValueError('original observer contract required before cold reader')
        class Forbidden:
            def __call__(self,*a,**k):raise AssertionError('cold observer cannot dispatch')
            def lease(self,*a,**k):raise AssertionError('cold observer cannot acquire inference')
        super().__init__(directory,contract,backend=Forbidden())

    def rate(self,paper):
        if not (self.root/'writer.lock').is_file():raise ValueError('original observer writer lock required')
        for critic in range(self.contract['critics']):
            key,_,_=request_for(self.contract,paper,critic)
            if not (self.root/'requests'/(key+'.result.json')).is_file():
                raise ValueError('missing original critic position; cold reader cannot refill it')
        return super().rate(paper)


def accepted_request_keys(state,contract):
    return {request_for(contract,content(paper),critic)[0] for paper in state['paper_tracker']['papers']
        if any(d.get('decision')=='accept' for d in paper['review_history']) for critic in range(contract['critics'])}


def reconstruct_measurement(state,base,observer):
    spec=SystemSpec.from_dict(state['native_system']['spec'])
    years=state['portable']['contract']['simulation']['num_years']
    if (base['system_fingerprint']!=spec.fingerprint or state['year']!=years or state['phase']!=5
            or state['native_system']['last_year']!=years):raise ValueError('actual completed native checkpoint required')
    papers={}
    for record in state['paper_tracker']['papers']:
        if record['id'] in papers:raise ValueError('duplicate actual native paper')
        papers[record['id']]=SimpleNamespace(id=record['id'],review_history=clone(record['review_history']),
            to_dict=lambda record=record:clone(record))
    # Read-only typed projections of original data, not a new Simulation or
    # a substituted scientific world. Native physical proof is separate.
    simulation=SimpleNamespace(num_years=years,native_system=SimpleNamespace(last_year=years,spec=spec),
        paper_tracker=SimpleNamespace(papers_by_id=papers))
    result=observer.measure(simulation,clone(base))
    result['measurement_adapter_contract_sha256']=digest(observer.contract)
    return result
