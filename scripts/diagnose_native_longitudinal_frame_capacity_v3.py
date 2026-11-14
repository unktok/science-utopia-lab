"""Same finite64k capacity calls, prospectively declared inspected CPU sharing."""
import argparse
import json
from pathlib import Path

from scripts import diagnose_native_longitudinal_frame_capacity_v1 as base
from scripts import diagnose_native_longitudinal_frame_capacity_v2 as v2
from scripts import observe_native_capacity_shared_cpu_v3 as resources
from utopia.utils.data_utils import file_sha256

ROOT=base.ROOT
MODULE='scripts.diagnose_native_longitudinal_frame_capacity_v3'
SCHEMA='scienceutopia.longitudinal-late-frame-capacity.v3'
PROTOCOL='research/protocols/campaigns/native-longitudinal-frame-capacity-v3.md'


def make_plan(root,audits,source):
    p=v2.make_plan(root,audits,source)
    p.update(schema=SCHEMA+'.plan',script_sha256=file_sha256(__file__),
        context_derivation_script_sha256=file_sha256(v2.__file__),
        resource_observer_sha256=file_sha256(resources.__file__),
        resource_contract=resources.CONTRACT,protocol_sha256=file_sha256(ROOT/PROTOCOL))
    return p


def require_plan(root):
    base.require_environment();p=base.read(root/'plan.json')
    q=make_plan(p['origin_run'],p['origin_audits'],base.pinned_revision(ROOT))
    if q!={k:v for k,v in p.items() if k!='content_sha256'}:raise ValueError('exact declared shared-CPU capacity plan differs')
    return p


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','run','worker'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--origin-run',type=Path)
    p.add_argument('--audit',type=Path,action='append');p.add_argument('--resources',type=Path)
    a=p.parse_args();out=a.output.resolve()
    if not out.is_relative_to(ROOT/'outputs'):raise ValueError('fresh ignored output under frozen diagnostic source required')
    if a.command=='prepare':
        base.require_environment()
        if out.exists() or not a.origin_run or not a.audit:raise ValueError('fresh output/original fixture required')
        plan=make_plan(a.origin_run,a.audit,base.pinned_revision(ROOT));out.mkdir(parents=True)
        base.save(out/'plan.json',plan);require_plan(out)
        print(json.dumps({'maximum_chat_POSTs':2,'context_both_arms':65536,'new_model_POSTs':0,'resource_scope':'capacity-only-v3'}))
    elif a.command=='run':
        if a.resources is None:raise ValueError('fresh capacity-only resource proof required')
        base.run(out,a.resources,require_plan_fn=require_plan,worker_module=MODULE,resource_check_fn=resources.require_resources)
    else:base.worker(out,require_plan_fn=require_plan)


if __name__=='__main__':main()
