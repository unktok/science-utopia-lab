"""Same literal late-frame messages, prospectively declared common64k context."""
import argparse
import json
from pathlib import Path

from scripts import diagnose_native_longitudinal_frame_capacity_v1 as base
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = base.ROOT
MODULE = 'scripts.diagnose_native_longitudinal_frame_capacity_v2'
SCHEMA = 'scienceutopia.longitudinal-late-frame-capacity.v2'
PROTOCOL = 'research/protocols/campaigns/native-longitudinal-frame-capacity-v2.md'


def derived_frame(frame):
    value = clone(frame); payload = json.loads(frame['wire_utf8'])
    if payload['options']['num_ctx'] != 40960:
        raise ValueError('literal old40k fixture required; no arbitrary field mutation')
    original = clone(payload); payload['options']['num_ctx'] = 65536
    value['wire_utf8'] = json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    value['wire_sha256'] = digest(value['wire_utf8'])
    value['wire_utf8_bytes'] = len(value['wire_utf8'].encode())
    value['original_wire_sha256'] = frame['wire_sha256']
    value['changed_fields'] = {'/options/num_ctx': [40960,65536]}
    check = clone(payload); check['options']['num_ctx'] = 40960
    if check != original: raise ValueError('diagnostic changed data besides declared context')
    return value


def make_plan(root, audits, source):
    value = base.make_plan(root,audits,source)
    value.update(schema=SCHEMA+'.plan',script_sha256=file_sha256(__file__),
        shared_runner_sha256=file_sha256(base.__file__),protocol_sha256=file_sha256(ROOT/PROTOCOL),
        frames=[derived_frame(f) for f in value['frames']],
        context_change_both_arms=[40960,65536],messages_tools_seeds_outputs_and_other_options_unchanged=True)
    return value


def require_plan(root):
    base.require_environment(); p = base.read(root/'plan.json')
    expected = make_plan(p['origin_run'],p['origin_audits'],base.pinned_revision(ROOT))
    if expected != {k:v for k,v in p.items() if k!='content_sha256'}:
        raise ValueError('exact source/runtime/one-field derived64k diagnostic differs')
    return p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','run','worker'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--origin-run',type=Path);parser.add_argument('--audit',type=Path,action='append')
    parser.add_argument('--resources',type=Path)
    args=parser.parse_args();out=args.output.resolve()
    if not out.is_relative_to(ROOT/'outputs'):raise ValueError('fresh ignored diagnostic output required')
    if args.command=='prepare':
        base.require_environment()
        if out.exists() or args.origin_run is None or not args.audit:raise ValueError('fresh output/original fixture required')
        p=make_plan(args.origin_run,args.audit,base.pinned_revision(ROOT));out.mkdir(parents=True)
        base.save(out/'plan.json',p);require_plan(out)
        print(json.dumps({'context_both_arms':65536,'maximum_chat_POSTs':2,'new_model_POSTs':0}))
    elif args.command=='run':
        if args.resources is None:raise ValueError('fresh unchanged-profile resource proof required')
        base.run(out,args.resources,require_plan_fn=require_plan,worker_module=MODULE)
    else:base.worker(out,require_plan_fn=require_plan)


if __name__ == '__main__':main()
