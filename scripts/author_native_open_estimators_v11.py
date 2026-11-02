"""Explicit external-Codex pilot design, NOT an autonomous invention algorithm.

This optional authoring example is separate from the generic runner. It creates
an executable evidence protocol and Python decision rule, not a world model.
The host never evaluates the source strings. Later generations explicitly retain
the same algorithms so a prior-only control variate has compatible semantics.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec,
    MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec, SystemSpec)
from utopia.system.code_mechanisms import CODE_SCHEMA
from utopia.system.design_patch import apply_design_patch, clone, digest, make_patch
from utopia.system.native_kernel import WORLD_ARTIFACT
from utopia.system.native_process import compile_dependencies
from utopia.utils.data_utils import write_json_atomic

PROTOCOL = 'native-review-evidence-v11'
EVIDENCE_SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    rows = []
    for conference in world['conferences']['conferences']:
        for paper in conference['submitted_papers']:
            reviews = conference['reviews'].get(paper['id'], [])
            scores = [r['overall_score'] for r in reviews]
            mean = sum(scores) / len(scores) if scores else 0.0
            evidence = mean
            rows.append({'paper_id':paper['id'], 'conference_id':conference['conference_id'],
                'mean_score':mean, 'evidence':evidence, 'review_count':len(scores)})
    return {'outputs':{'evidence':[{'payload':{'records':rows}}]},
        'state':{'cycles':context['state'].get('cycles',0)+1}}
'''
CONSERVATIVE_SOURCE = EVIDENCE_SOURCE.replace(
    'evidence = mean', 'evidence = min(scores) if scores else 0.0')
DECISION_SOURCE = '''def step(context):
    evidence = context['inputs']['evidence'][0]['payload']['records']
    cutoff = context['parameters']['cutoff']
    decisions = [{'payload':{'paper_id':r['paper_id'], 'conference_id':r['conference_id'],
        'decision':'accept' if r['evidence'] >= cutoff else 'reject',
        'final_score':r['mean_score']}} for r in evidence]
    return {'outputs':{'decisions':decisions or [{'payload':{'empty_cycle':True}}],
        'next':[{'payload':{'year':context['period']}}],
        'world':[{'payload':context['inputs']['observations'][0]['payload']}]},
        'state':{'cycles':context['state'].get('cycles',0)+1}}
'''


def _code(image, label, source, inputs, outputs, **parameters):
    return {'runtime_image_id': image, **parameters, 'code_artifact': {
        'schema': CODE_SCHEMA, 'label': label, 'source': source,
        'inputs': {p.port_id: {'type': 'object'} for p in inputs},
        'outputs': {p.port_id: {'type': 'object'} for p in outputs},
        'state_schema': {'type': 'object'}}}


def authored_base(parent):
    image = next(n.parameters['runtime_image_id'] for n in parent.mechanisms
        if n.implementation == 'code.python.v1')
    removed = {'native-feature-extractor', 'addressed-selection', 'open-memory-router'}
    old = next(n for n in parent.mechanisms if n.mechanism_id == 'world.selection')
    inputs = (next(p for p in old.inputs if p.port_id == 'after'),
        PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),
        PortSpec('evidence', ChannelKind.ARTIFACT, PROTOCOL))
    selection = replace(old, inputs=inputs, parameters=_code(image,
        'Externally authored evidence-conditioned selection', DECISION_SOURCE,
        inputs, old.outputs, cutoff=3.5))
    evidence_inputs = (PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),)
    evidence_outputs = (PortSpec('evidence', ChannelKind.ARTIFACT, PROTOCOL),)
    node = MechanismSpec('review-evidence', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=evidence_inputs, outputs=evidence_outputs,
        parameters=_code(image, 'Externally authored reviewer aggregation',
            EVIDENCE_SOURCE, evidence_inputs, evidence_outputs))
    nodes = tuple(replace(selection if n.mechanism_id == old.mechanism_id else n,
        inputs=tuple(p for p in (selection if n.mechanism_id == old.mechanism_id else n).inputs
            if not p.port_id.startswith('requires-')))
        for n in parent.mechanisms if n.mechanism_id not in removed) + (node,)
    connections = tuple(e for e in parent.connections if
        e.source_mechanism not in removed and e.target_mechanism not in removed
        and not e.target_port.startswith('requires-')
        and not (e.target_mechanism == old.mechanism_id and e.target_port != 'after'))
    def edge(source, port, target, target_port):
        return ConnectionSpec(source, port, target, target_port, ChannelKind.ARTIFACT)
    connections += (edge('world.review','world','review-evidence','world'),
        edge('review-evidence','evidence','world.selection','evidence'),
        edge('world.review','world','world.selection','observations'))
    schedules = tuple(s for s in parent.schedules if s.mechanism_id not in removed)
    schedules += (ScheduleSpec('review-evidence', 125),)
    spec = replace(parent, mechanisms=nodes, connections=connections,
        schedules=schedules, artifact_types=(*parent.artifact_types, ArtifactTypeSpec(PROTOCOL)))
    deps = {n.mechanism_id: [] for n in nodes}
    deps['open-domain-actions'] = ['open-source']
    priorities = dict(parent.metadata['native_process']['priorities'])
    priorities = {k:v for k,v in priorities.items() if k not in removed}
    priorities['review-evidence'] = 125
    return compile_dependencies(spec, deps, priorities=priorities)


def _replace_system_patch(parent, target):
    # Exact top-level atomic replacement, not inferred graph repair.
    operations = [{'op':'replace','path':'/'+key,'value':value}
        for key,value in target.to_dict().items() if parent.to_dict()[key] != value]
    return make_patch(parent, operations, rationale='Explicit external v11 evidence protocol/source/wiring') if operations else None


def authored_definition(request, *, method):
    parent = SystemSpec.from_dict(request['parent_system'])
    generation = request['generation']
    provenance = {'kind':'external-codex-authored-pilot-example',
        'identity':'root integration author; self-reported, not authenticated',
        'autonomous_Qwen_invention':False, 'generation':generation,
        'own_history_sha256':request['history_sha256']}
    if generation == 0:
        base = authored_base(parent)
        index = next(i for i,n in enumerate(base.mechanisms) if n.mechanism_id == 'review-evidence')
        selection_index = next(i for i,n in enumerate(base.mechanisms) if n.mechanism_id == 'world.selection')
        factors = [{'id':'review-aggregation','kind':'categorical','choices':[
            {'id':name,'operations':[{'op':'replace',
                'path':f'/mechanisms/{index}/parameters/code_artifact/source','value':source}],
                'provenance':{'author':'external Codex pilot example','meaning':name}}
            for name,source in [('mean-evidence',EVIDENCE_SOURCE),('minimum-evidence',CONSERVATIVE_SOURCE)]]}]
        continuous = [{'id':'evidence-cutoff','path':f'/mechanisms/{selection_index}/parameters/cutoff',
            'lower':2.75,'upper':4.25,'mean':0.,'sigma':1.}]
        # The first definition is semantically method-matched; request-specific
        # authoring provenance may differ without changing source or draws.
        return {'base_patch':_replace_system_patch(parent,base), 'factors':factors,
            'continuous':continuous,'logits':{'review-aggregation':[0.,0.]},
            'provenance':provenance}
    if generation != 1 or len(request['history']) != 1:
        raise ValueError('this explicit pilot author supports exactly two generations')
    previous = request['history'][0]
    definition = clone(previous['definition'])
    first_parent = SystemSpec.from_dict(request['history'][0]['draws'][0]['suggestion']['candidate'])
    # Reset only the first draw's explicitly sampled algorithm and continuous
    # value to their declared base. Preserve its actual installed other fields.
    base_doc = first_parent.to_dict()
    evidence_index = next(i for i,n in enumerate(base_doc['mechanisms']) if n['mechanism_id']=='review-evidence')
    base_doc['mechanisms'][evidence_index]['parameters']['code_artifact']['source'] = EVIDENCE_SOURCE
    cutoff = definition['continuous'][0]
    from utopia.system.design_patch import _edit
    _edit(base_doc, {'op':'replace','path':cutoff['path'],'value':3.5})
    base = SystemSpec.from_dict(base_doc)
    definition['base_patch'] = _replace_system_patch(parent,base)
    if method == 'score-control-variate':
        weights = previous['report']['mixed']['weights_after']
        definition['logits'] = clone(weights['logits'])
        definition['continuous'][0]['mean'] = weights['continuous_mean'][0]
        provenance['revision'] = 'Explicitly carry own learned logits/mean; retain executable semantics for prior-only CV'
    elif method == 'blackbox':
        complete = [(d,o) for d,o in zip(previous['draws'],previous['observations'])
            if o and o['status']=='complete' and not o['metadata'].get('technical_failures')]
        if not complete:
            raise ValueError('no valid native outcomes for a loss-driven revision')
        best_draw,best_observation = min(complete,key=lambda row:row[1]['loss'])
        if len({o['loss'] for _,o in complete}) > 1:
            definition['continuous'][0]['mean'] = best_draw['latent'][0]
            selected = best_draw['assignment']['review-aggregation']
            definition['logits'] = {'review-aggregation':[
                1. if c['id']==selected else 0. for c in definition['factors'][0]['choices']]}
            provenance['revision'] = 'Derivative-free own-best latent recentering and categorical preference; no gradient claim'
        else:
            provenance['revision'] = 'Own losses tied; keep first distribution, no forced revision'
        provenance['based_on_observation_id'] = best_observation['observation_id']
    else:
        raise ValueError('unknown method arm')
    definition['provenance'] = provenance
    return definition


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--response',type=Path,required=True)
    parser.add_argument('--method',choices=['blackbox','score-control-variate'],required=True)
    args=parser.parse_args()
    request=json.loads(args.request.read_text())
    nested=request['request']['authoring_input']
    definition=authored_definition(nested,method=args.method)
    response={'request_sha256':digest(request),'manifest':definition,
        'authoring':{'kind':'codex-agent','identity':'root authored pilot example',
            'authenticated':False,'autonomous_invention':False}}
    if args.response.exists():
        if json.loads(args.response.read_text()) != response:
            raise ValueError('existing external response differs; do not overwrite')
    else:
        write_json_atomic(args.response,response,sort_keys=True,allow_nan=False)


if __name__=='__main__':
    main()
