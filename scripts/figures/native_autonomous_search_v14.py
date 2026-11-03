#!/usr/bin/env python3
"""Actual-data-only autonomous institutional search figure, 5.5 inches wide."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from scripts.analyze_native_autonomous_search_v14 import (
    ACTUAL, FIXTURE, SCHEMA, FORBIDDEN_CLAIMS, design_change, executable_contracts, objective_specs,
    ReadOnlyAdaptive, ReadOnlyNested, _hashed_record)
from scripts.analyze_native_open_estimators_v11 import incumbent_path
from scripts.native_nested_estimator_audit_v13 import conditional_update_proof
from scripts.figures.native_nested_search_v13 import _table
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

COLORS = ('#087e9c','#a94779','#5a579c')
NAMES = ('Throughput / black-box','Efficiency / black-box','Efficiency / nested LR')
SHORT = ('T-BB','E-BB','E-LR')


def _hash(value,n=64):
    return isinstance(value,str) and len(value) == n and all(c in '0123456789abcdef' for c in value)


def _compact_observation(self,value,draw):
    if draw['suggestion'] is None:
        if value is not None:
            raise ValueError('invalid draw has fabricated observation')
        return
    evaluated = evaluate_loss(self.loss,value['metadata']['measurements'])
    if (value['suggestion_id'] != draw['suggestion']['suggestion_id']
            or value['candidate'] != draw['suggestion']['candidate']
            or value['metadata']['world_backend'] != 'native-research-world'
            or value['metadata']['loss_spec_sha256'] != loss_spec_sha256(self.loss)
            or value['metadata']['loss_evaluation'] != evaluated
            or value['loss'] != (evaluated['loss'] if evaluated['status'] == 'complete' else None)
            or (value['status'] == 'complete') != (evaluated['status'] == 'complete')):
        raise ValueError('compact observation source/loss differs')


class _CompactAdaptive(ReadOnlyAdaptive):
    _check_observation = _compact_observation


class _CompactNested(ReadOnlyNested):
    _check_observation = _compact_observation


def _replay(run):
    cls = _CompactAdaptive if run['method'] == 'blackbox' else _CompactNested
    controller = cls.__new__(cls)
    controller.binding = deepcopy(run['binding'])
    controller.binding_sha256 = digest(controller.binding)
    controller.initial = SystemSpec.from_dict(controller.binding['initial_system'])
    controller.loss = deepcopy(run['loss_spec'])
    controller.state = {'schema':'scienceutopia.native-adaptive-open-search.v7' if run['method'] == 'blackbox'
        else 'scienceutopia.native-nested-search.v13','binding':controller.binding,
        'records':deepcopy(run['records']),'pending':deepcopy(run['pending'])}
    controller._validate()
    expected = conditional_update_proof(run['records']) if run['method'] == 'nested-lr' else None
    if run['conditional_update_proof'] != expected:
        raise ValueError('conditional LR analytical proof differs')


def figure_data(report,expected_source=None,*,allow_synthetic=False):
    _hashed_record(report)
    classification = report.get('classification')
    if (report.get('schema') != SCHEMA or report.get('status') not in ('complete','budget-complete-with-failures')
            or classification not in (ACTUAL,FIXTURE) or (classification == FIXTURE) != allow_synthetic
            or len(report.get('run_order',[])) != 3 or set(report['runs']) != set(report['run_order'])):
        raise ValueError('terminal exact independent audit required; synthetic is explicit test-only')
    if classification == ACTUAL and (not _hash(expected_source,40) or expected_source != report['source_commit']):
        raise ValueError('exact actual source pin required')
    audit = report['audit']
    required = ('campaign_and_lineage_replayed','checkpoint_loss_reextracted',
        'all_failures_and_exact_ties_retained','designer_requests_raw_replies_and_operations_joined',
        'scientist_and_designer_costs_separate')
    if (any(audit.get(k) is not True for k in required) or audit.get('new_model_calls') != 0
            or audit.get('new_container_executions') != 0 or not _hash(audit.get('raw_inventory_sha256'))
            or digest(audit['raw_input_sha256s']) != audit['raw_inventory_sha256']
            or any(report['claims'].get(k) is not False for k in FORBIDDEN_CLAIMS)):
        raise ValueError('independent immutable raw/source/native proof and bounded claims required')
    if classification == ACTUAL:
        source = audit['replay_source_proofs']
        files = source['files']
        names = {'scripts/run_native_autonomous_search_v14.py','utopia/optimization/native_adaptive_search.py',
            'utopia/optimization/native_nested_search.py','scripts/native_physical_evidence_v13.py'}
        if (source['status'] != 'verified-exact-replay-source-blobs' or not names <= set(files)
                or any(not _hash(v.get('actual_source_sha256'))
                    or v['actual_source_sha256'] != v.get('analysis_source_sha256') for v in files.values())):
            raise ValueError('actual v14 runtime/driver/helper source equivalence required')
    rows, edits, costs, accounting = [], [], [], []
    slots = complete = failures = scientist = 0
    designer = {k:0 for k in ('generations','dispatch_intents','known_responses','valid_drafts','interrupted_response_unknown')}
    seen = set()
    expected_contracts = [(list(objective_specs())[0],'blackbox',2),
        (list(objective_specs())[1],'blackbox',2),(list(objective_specs())[1],'nested-lr',4)]
    for run_index,identity in enumerate(report['run_order']):
        run = report['runs'][identity]
        request = run['request']
        if ((request['loss_spec']['id'],run['method'],request['native_budget']) != expected_contracts[run_index]
                or run['loss_spec'] != objective_specs()[request['loss_spec']['id']]
                or run['pending'] is not None or not run['terminal']):
            raise ValueError('frozen distinct request budget/loss contracts differ')
        _replay(run)
        if incumbent_path(run['observations']) != run['incumbents']:
            raise ValueError('all-tie incumbent path differs')
        run_rows, row_cursor, slot_cursor, complete_run = [],0,0,0
        for index,record in enumerate(run['records']):
            attempted = [(None,None,None)] if record['generation_error'] else [
                (i,d,o) for i,(d,o) in enumerate(zip(record['draws'],record['observations']))]
            for draw_index,draw,observation in attempted:
                row = run['observations'][row_cursor]
                span = record['request']['count'] if draw is None else 1
                if (row['draw'] != draw or row['observation'] != observation or row['slot'] != slot_cursor
                        or row['record_index'] != index or row['draw_index'] != draw_index
                        or row['scheduled_native_slots'] != span or row['generation_error'] != record['generation_error']
                        or row['loss'] != row['own_loss']):
                    raise ValueError('retained every-attempt identity or slot differs')
                if row['status'] == 'complete':
                    proof = row['physical_proof']
                    if (not observation or observation['status'] != 'complete'
                            or row['observation_id'] in seen or not _hash(row['checkpoint_sha256'])
                            or proof['checkpoint_sha256'] != row['checkpoint_sha256']
                            or proof['measurement'] != observation['metadata']['measurements'][0]
                            or proof['measurement']['metrics'] != row['metrics']
                            or proof['native_loss'] != row['own_loss']
                            or proof['native_counts']['kernel_restored_without_execution'] is not True):
                        raise ValueError('unique native physical checkpoint proof differs')
                    seen.add(row['observation_id'])
                    for loss_id,loss in objective_specs().items():
                        result = evaluate_loss(loss,[{'run_id':row['observation_id'],'metrics':row['metrics']}])
                        if result['status'] != 'complete' or result['loss'] != row['cross_scores'][loss_id]:
                            raise ValueError('native checkpoint cross-score differs')
                    complete_run += 1
                elif (row['status'] not in ('generation-failure','technical-failure')
                        or row['own_loss'] is not None or any(v is not None for v in row['cross_scores'].values())):
                    raise ValueError('failed slots must remain null')
                if row['system'] is not None:
                    if (draw['suggestion']['candidate'] != row['system']
                            or SystemSpec.from_dict(row['system']).fingerprint != row['system_fingerprint']
                            or executable_contracts(row['system']) != row['contracts']
                            or design_change(record['request']['parent_system'],row['system']) != row['lineage']['vs_parent']):
                        raise ValueError('actual code/graph/literal parent delta differs')
                run_rows.append({**row,'incumbent_loss':run['incumbents']['path'][row_cursor]['best_loss_so_far']})
                row_cursor += 1
                slot_cursor += span
            if run['method'] == 'blackbox' or record['request']['external_authoring']:
                authored = next(a for a in run['authored_definitions'] if a['record_index'] == index)
                base = None if record['generation_error'] else GeneratedMixedDesign(
                    SystemSpec.from_dict(record['request']['parent_system']),record['definition'],
                    loss_spec=run['loss_spec'],seed=record['request']['rng_seed'],
                    single_draw_blackbox=record['request']['count'] == 1).base.to_dict()
                if (authored['definition'] != record['definition']
                        or authored['base_system'] != base
                        or authored['definition_sha256'] != digest(record['definition'])
                        or authored['literal_change'] != (design_change(record['request']['parent_system'],
                            authored['base_system']) if authored['base_system'] is not None else None)):
                    raise ValueError('authored definition/base literal edits differ')
                edits.append({'label':SHORT[run_index]+f" G{record['request']['generation']}",
                    'counts':authored['literal_change']['counts'] if authored['literal_change'] else None})
        if (row_cursor != len(run['observations']) or slot_cursor != request['native_budget']
                or run['consumed_native_slots'] != slot_cursor or run['physical_native_worlds'] != complete_run
                or run['technical_failures'] != slot_cursor-complete_run):
            raise ValueError('charged/physical/failure accounting differs')
        ds = run['designer']
        if ds['generations'] != len(ds['proofs']):
            raise ValueError('designer generation evidence count differs')
        counts = {k:0 for k in ('dispatch_intents','known_responses','valid_drafts','interrupted_response_unknown')}
        for proof in ds['proofs']:
            _hashed_record(proof['binding'],field='binding_sha256')
            _hashed_record(proof['result'])
            if (proof['binding']['request_sha256'] != proof['request_sha256']
                    or proof['request_sha256'] != digest(proof['binding']['request'])
                    or proof['result']['attempts'] != proof['attempts']
                    or proof['result']['definition'] != next(r['definition'] for r in run['records']
                        if r['request_sha256'] == proof['request_sha256'])):
                raise ValueError('designer request/raw/result/consumed-definition join differs')
            counts['dispatch_intents'] += len(proof['attempts'])
            if len(proof['attempt_records']) != len(proof['attempts']):
                raise ValueError('designer draft completion omitted')
            for attempt,done in zip(proof['attempts'],proof['attempt_records']):
                if done is None:
                    if attempt['status'] != 'interrupted-response-unknown' or attempt['completed_sha256'] is not None:
                        raise ValueError('unknown designer completion relabelled')
                    counts['interrupted_response_unknown'] += 1
                    continue
                _hashed_record(done)
                if attempt['status'] != done['status']:
                    raise ValueError('designer technical draft outcome differs')
                reply = done.get('model_reply') or {}
                assistants = [m for m in reply.get('messages',[]) if m.get('role') == 'assistant']
                counts['known_responses'] += int(bool(assistants) or 'raw_http_response' in reply.get('transport',{}))
                counts['valid_drafts'] += int(done['status'] == 'valid')
                if done['status'] == 'valid':
                    from utopia.optimization.native_search_generator_v14 import compile_authored_output
                    if compile_authored_output(proof['binding']['request'],reply['output'],
                            binding_sha256=proof['binding']['binding_sha256'],
                            provider_binding=proof['binding']['provider_binding']) != done['definition']:
                        raise ValueError('designer authored operations repaired in figure evidence')
        if any(ds[key] != value for key,value in counts.items()):
            raise ValueError('designer known/unknown/attempt accounting differs')
        for key in designer:
            designer[key] += ds[key]
        rows.append(run_rows)
        costs.append({'label':SHORT[run_index],'designer_intents':ds['dispatch_intents'],
            'designer_replies':ds['known_responses'],'scientist_requests':run['completed_wire_requests'],
            'scientist_replies':run['physical_researcher_responses']})
        accounting.append({'label':SHORT[run_index],'slots':slot_cursor,'worlds':complete_run,
            'directories':run['physical_world_directory_count'],'nulls':slot_cursor-complete_run})
        slots += slot_cursor
        complete += complete_run
        failures += slot_cursor-complete_run
        scientist += run['physical_researcher_responses']
    if (slots != 8 or report['planned_native_world_budget'] != 8 or report['consumed_native_slots'] != slots
            or report['physical_native_worlds'] != complete or report['technical_failures'] != failures
            or report['physical_researcher_responses'] != scientist or report['designer_costs'] != designer):
        raise ValueError('aggregate native/designer accounting differs')
    measurements = report.get('designer_cost_measurements',{})
    for key,measurement in measurements.items():
        values = [r['designer']['cost_measurements'][key] for r in report['runs'].values()]
        if measurement != {'recorded_sum':math.fsum(v['recorded_sum'] for v in values),
                'record_count':sum(v['record_count'] for v in values)}:
            raise ValueError('designer timing/token aggregate differs')
    return {'classification':classification,'source_commit':report['source_commit'],'rows':rows,
        'edits':edits,'costs':costs,'accounting':accounting,'designer_costs':designer,
        'physical_researcher_responses':scientist,'planned_native_world_budget':8,
        'consumed_native_slots':slots,'physical_native_worlds':complete}


def render(report,output,*,audit_path,expected_source=None,allow_synthetic=False):
    data = figure_data(report,expected_source,allow_synthetic=allow_synthetic)
    output = Path(output)
    with matplotlib.rc_context({'font.family':'DejaVu Sans','font.size':7.3,
            'axes.titlesize':8.3,'axes.labelsize':7.3,'xtick.labelsize':7.2,'ytick.labelsize':7.2,
            'svg.fonttype':'none','svg.hashsalt':'native-autonomous-search-v14'}):
        fig = Figure(figsize=(5.5,7.4))
        FigureCanvasAgg(fig)
        axes = fig.subplots(3,2)
        for index,ax in enumerate(axes.flat[:3]):
            rows = data['rows'][index]
            xs = [r['slot']+1 for r in rows]
            ys = [r['own_loss'] if r['own_loss'] is not None else math.nan for r in rows]
            bs = [r['incumbent_loss'] if r['incumbent_loss'] is not None else math.nan for r in rows]
            ax.plot(xs,ys,'o-',color=COLORS[index],linewidth=1.3,markersize=4,label='Current')
            ax.step(xs,bs,where='post',color='#354654',linestyle='--',linewidth=1,label='Best so far')
            for row in rows:
                if row['own_loss'] is None:
                    ax.text(row['slot']+1,.93,'Null' if row['scheduled_native_slots'] == 1 else 'Null\n2 slots',
                        transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=7,color='#a23b43')
            labels = ['G0','G1'] if index < 2 else ['G0a','G0b','Updated','G1']
            ax.set_xticks(range(1,len(labels)+1),labels)
            ax.set_xlim(.65,len(labels)+.35)
            ax.set_title(chr(65+index)+'  '+NAMES[index],pad=7)
            ax.set_ylabel('Own loss (lower is better)')
            ax.grid(axis='y',alpha=.2)
            if any(math.isfinite(y) for y in ys):
                ax.legend(loc='best',fontsize=6.8,handlelength=1.4)
            else:
                ax.set_yticks([])
                ax.text(.5,.42,'No completed native loss',transform=ax.transAxes,ha='center',fontsize=7)
        ax = axes[1,1]
        ax.set_title('D  Authored base versus parent',y=1.05,pad=0)
        vals = [['n/a']*3 if e['counts'] is None else [str(e['counts']['source_bodies_added']),
            f"{e['counts']['nodes_added']}/{e['counts']['nodes_removed']}",
            f"{e['counts']['edges_added']}/{e['counts']['edges_removed']}"] for e in data['edits']]
        _table(ax,['New\nbodies','Nodes\n+/−','Wires\n+/−'],[e['label'] for e in data['edits']],vals,bbox=(0,.19,1,.74))
        ax.text(.5,.02,'Literal edits; n/a is failure.\nNew text is not proven invention.',
            transform=ax.transAxes,ha='center',va='bottom',fontsize=7,color='#435568')
        ax = axes[2,0]
        ax.set_title('E  Separate designer / scientist costs',y=1.05,pad=0)
        _table(ax,['Design\nintent/reply','Scientist\nrequest/reply'],[c['label'] for c in data['costs']],
            [[f"{c['designer_intents']}/{c['designer_replies']}",
                f"{c['scientist_requests']}/{c['scientist_replies']}"] for c in data['costs']],bbox=(0,.38,1,.50))
        timing = report.get('designer_cost_measurements',{}).get('model_call_seconds',{})
        designer_time = f"{timing['recorded_sum']/60:.2f} min" if timing.get('record_count') else 'n/a'
        scientist_time = (f"{report['completed_researcher_model_call_seconds']/60:.2f} min"
            if report['physical_native_worlds'] else 'n/a')
        ax.text(.5,.01,f'Designer recorded calls: {designer_time}.\nScientist model calls: {scientist_time}.\n'
            'Intent = dispatch intent; unknowns retained.\nScientist requests: completed worlds only.',
            transform=ax.transAxes,ha='center',va='bottom',fontsize=7,color='#435568')
        ax = axes[2,1]
        ax.set_title('F  Charged slots and physical evidence',y=1.05,pad=0)
        _table(ax,['Slots','Worlds','Dirs','Null'],[a['label'] for a in data['accounting']],
            [[str(a[k]) for k in ('slots','worlds','directories','nulls')] for a in data['accounting']],bbox=(0,.3,1,.58))
        ax.text(.5,.01,'Worlds = complete physical worlds.\nPartial directories remain in the audit.\nNull slots are never replaced.',
            transform=ax.transAxes,ha='center',va='bottom',fontsize=7,color='#435568')
        fig.suptitle('SYNTHETIC CONTRACT FIXTURE — NOT EVIDENCE' if allow_synthetic else
            'Autonomous model-authored institutional search',fontsize=10.3,fontweight='bold',y=.985)
        fig.text(.5,.025,'T: throughput, $L=-A$. E: reviewed efficiency, $L=-Q+0.5R$.\n'
            'BB: free re-authoring each slot. LR: 2 draws → conditional update → fresh draw → redesign.\n'
            'Three development requests; not a controlled method comparison. All failures/ties retained.\n'
            'One seed; no held-out, scientific-benefit, useful-invention or designer-improvement claim.',
            ha='center',fontsize=7,color='#435568')
        fig.tight_layout(rect=(.025,.12,.99,.955),h_pad=2.1,w_pad=1.7)
        fig.canvas.draw()
        output.parent.mkdir(parents=True,exist_ok=True)
        files = []
        for suffix in ('.png','.svg'):
            path = output.with_suffix(suffix)
            fig.savefig(path,dpi=200,metadata={'Date':None} if suffix == '.svg' else None)
            files.append({'path':str(path),'sha256':file_sha256(path)})
    manifest = {'schema':'scienceutopia.native-autonomous-search-figure.v14',
        'classification':data['classification'],'source_commit':data['source_commit'],
        'audit_file_sha256':file_sha256(audit_path),'audit_content_sha256':report['content_sha256'],
        'generator_sha256':file_sha256(Path(__file__)),'files':files,'data':data,'width_inches':5.5}
    manifest['content_sha256'] = digest(manifest)
    write_json_atomic(output.with_suffix('.manifest.json'),manifest,sort_keys=True,allow_nan=False)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected-source',required=True)
    parser.add_argument('--allow-synthetic',action='store_true')
    args = parser.parse_args()
    result = render(json.loads(args.audit.read_text()),args.output,audit_path=args.audit,
        expected_source=args.expected_source,allow_synthetic=args.allow_synthetic)
    print(json.dumps({'content_sha256':result['content_sha256'],'files':result['files']},sort_keys=True))


if __name__ == '__main__':
    main()
