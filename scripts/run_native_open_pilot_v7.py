#!/usr/bin/env python3
"""Small original-Qwen engineering probe for the integrated open interfaces.

Two external authoring rounds, two IID native designs each, one development
seed, two native years, original five researchers. No scale or value claim.
Missing authoring is a durable wait, not a failed world or a made-up cost.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, InboxVocabularyGenerator
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_hybrid import boundary_coverage, conditional_backward
from utopia.optimization.native_manifest_inbox import ManifestInbox, ExternalAuthoringPending, audit_manifest_inbox
from utopia.optimization.native_relaxation import native_tensor_trace
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_open_examples import joint_engineering_loss, open_native_system
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


def summarize(campaign,output):
    rows=[]
    for record in campaign.state['records']:
        for draw,observation in zip(record['draws'],record['observations']):
            row={'generation':record['request']['generation'],'version_sha256':record['version_sha256'],
                'strategy':record['request']['strategy_id'],'draw':draw,'observation':observation}
            if observation and observation['status']=='complete':
                path=observation['metadata']['runs'][0]['checkpoint_path']
                saved=read_portable_checkpoint(path)
                system=SystemSpec.from_dict(draw['suggestion']['candidate'])
                native=saved['native_system']
                coverage=boundary_coverage(system,native['events'])
                programs={n.mechanism_id:n.parameters['program'] for n in system.mechanisms if n.implementation=='program.tensor.v1'}
                backward=conditional_backward(native_tensor_trace(native['events']),programs,
                    trainable={'addressed-selection':['bias']},terms=[{'mechanism':'open-memory-router','output':'actions','coefficient':-1.}])
                domain=native.get('open_domain',{})
                row.update(checkpoint_path=str(path),checkpoint_sha256=file_sha256(path),
                    boundary_coverage=coverage,conditional_backward=backward,
                    open_domain=domain,process_receipts=[e for e in native['events'] if e['event_type'].startswith('native.process.')],
                    events=native['events'],system=system.to_dict(),year=saved['year'])
            rows.append(row)
    value={'schema':'scienceutopia.native-open-integrated-pilot.v7','source_commit':campaign.binding['world']['source_commit'],
        'world_binding':campaign.binding['world'],'campaign_binding':campaign.binding,
        'records':campaign.state['records'],'observations':rows,
        'authoring':audit_manifest_inbox(Path(output)/'authoring'),
        'claims':{'live_fixed_Qwen_researchers':True,'scripted_researcher_HTTP':False,
            'engineering_count_loss':True,'held_out':False,'causal_institutional_benefit':False,
            'scientific_value':False,'full_native_world_pathwise_autograd':False,
            'designer_improvement_established':False,'external_authorship_authenticated':False}}
    value['content_sha256']=digest(value)
    write_json_atomic(Path(output)/'evidence.json',value,sort_keys=True,allow_nan=False)
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data-cache',type=Path,required=True)
    parser.add_argument('--inference-lock',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    executor=DockerCodeExecutor()
    initial=open_native_system(executor.image_id)
    factory=LocalQwenNativeFactory(args.output/'worlds',args.data_cache,years=2,corpus_years=4,
        experiment_binding={'protocol':'native-open-integrated-v7','role':'development-engineering'},
        record_wire=True,record_code=True,inference_lock=args.inference_lock)
    world={'source_commit':factory.source_commit,'model_digest':factory.model_digest,'corpus_sha256':factory.corpus_sha256}
    strategies={name:{'kind':'external-codex-authoring','identity':'self-reported specialist',
        'scope':name,'provider_authenticated':False} for name in ('invent','revise')}
    campaign=NativeAdaptiveDesignCampaign(args.output/'campaign',initial_system=initial,
        loss_spec=joint_engineering_loss(),seeds=[42],world_binding=world,strategies=strategies,mode='hybrid')
    inbox=ManifestInbox(args.output/'authoring')
    generator=InboxVocabularyGenerator(inbox,instructions=(
        'Small development engineering probe. Keep original native scientific phases, open actor/artifact effects '
        'and the two tensor nodes executable, including addressed-selection bias and open-memory-router/actions '
        'because backward instrumentation names these. Author complete arbitrary code/parameters/process/wires; '
        'generated source executes only in the declared pinned networkless container. '
        'Source may be nested in native.process.activity.v1 parameters/delegate. Do not change its output ABI '
        'without also authoring matching ports/protocol/consumers. You may introduce new typed actor/artifact '
        'roles and arbitrary mechanisms. Keep source safely within existing granted capabilities, or explicitly '
        'author matching receiver declarations. Native projects run before typed research production. '
        'Use exact parent fingerprint and v1 design-patch format, return no hidden/incomplete edits. '
        'Include at least one real continuous parameter coordinate and one nontrivial structural/process factor. '
        'Provide two or more conditional options. Use actual feedback, including failures. '
        'Never fabricate a loss or claim policy/scientific improvement. No host or paid API access.'))
    try:
        while len(campaign.state['records'])<2:
            campaign.advance(simulation_factory=factory,generators={name:generator for name in strategies},count=2)
            summarize(campaign,args.output)
    except ExternalAuthoringPending as waiting:
        value=summarize(campaign,args.output)
        print(json.dumps({'status':'waiting-for-external-authoring','complete_generations':len(campaign.state['records']),
            'evidence_sha256':value['content_sha256'],**waiting.to_dict()}))
        return 3
    print(json.dumps({'status':'complete','generations':len(campaign.state['records']),
        'losses':[r['observation']['loss'] if r['observation'] else None for r in summarize(campaign,args.output)['observations']]}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
