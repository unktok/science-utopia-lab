#!/usr/bin/env python3
"""PNG/SVG evidence figure from a COMPLETE independent actual-Qwen v9 audit.

No raw/operator/source execution or new forward call occurs. Synthetic schema
fixtures require an explicit test flag, are watermarked and restricted to tmp.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-qwen-response-audit.v9'
ACTUAL = 'actual-native-qwen-response-gradient-development-v9'
FIXTURE = 'synthetic-schema-fixture-not-actual-qwen'
NAMES = ('calibration-0','calibration-1','calibration-2','unused-0','unused-1','gradient-candidate')
BLUE, ORANGE, TEAL, GREY, PURPLE = '#24587B','#CC743D','#258678','#87949E','#785B92'


def _finite(value):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('figure quantities must be finite; missing predictions are not zero')
    return value


def _hash(value, length=64):
    return isinstance(value,str) and bool(re.fullmatch('[0-9a-f]{'+str(length)+'}',value))


def _same(a,b):
    return math.isclose(_finite(a),_finite(b),rel_tol=1e-10,abs_tol=1e-10)


def _response_counts(report,rows):
    """Never label replayed prefix responses as new physical Qwen calls."""
    logical=sum(r['response_count'] for r in rows)
    coupling=report.get('response_coupling')
    amendment=report.get('prospective_amendment') or {}
    if coupling is None:
        if amendment.get('id')=='native-qwen-response-gradient-v9-a3':
            raise ValueError('a3 requires explicit common-prefix response coupling')
        if report.get('physical_reply_count')!=logical:
            raise ValueError('physical reply total differs from six audited endpoints')
        return {'logical_response_count':logical,'fresh_physical_reply_count':logical,
                'replayed_response_count':0,'response_coupling':None}
    if (not isinstance(coupling,dict) or coupling.get('mode')!='actual-common-prefix-replay'
            or amendment.get('id')!='native-qwen-response-gradient-v9-a3'
            or type(coupling.get('unique_anchor_prefix_calls')) is not int
            or coupling['unique_anchor_prefix_calls']<=0):
        raise ValueError('known a3 common-prefix coupling and separate anchor-origin count required')
    fresh=replayed=0
    for row in rows:
        f,r=row.get('fresh_physical_reply_count'),row.get('replayed_response_count')
        if (type(f) is not int or type(r) is not int or min(f,r)<0
                or row['response_count']!=f+r):
            raise ValueError('coupled endpoint counts must satisfy logical = fresh + replayed')
        fresh+=f;replayed+=r
    if (report.get('logical_response_count')!=logical or replayed<=0
            or report.get('fresh_physical_reply_count')!=fresh
            or report.get('physical_reply_count')!=fresh):
        raise ValueError('coupled campaign fresh/logical counts differ; anchor calls are separate')
    return {'logical_response_count':logical,'fresh_physical_reply_count':fresh,
            'replayed_response_count':replayed,'response_coupling':{
                'mode':coupling['mode'],'unique_anchor_prefix_calls':coupling['unique_anchor_prefix_calls']}}


def figure_data(report, *, expected_source=None, allow_synthetic=False):
    """Validate audited scope and extract exact plotted numbers, without refit."""
    if report.get('content_sha256') != digest({k:v for k,v in report.items() if k!='content_sha256'}):
        raise ValueError('hash-bound independent audit required')
    fixture=report.get('fixture_kind')==FIXTURE
    if fixture and not allow_synthetic:
        raise ValueError('synthetic schema fixture requires explicit test-only permission')
    if (report.get('schema')!=SCHEMA or report.get('classification')!=ACTUAL
            or report.get('status')!='complete'):
        raise ValueError('complete independently audited actual-Qwen v9 classification required')
    source=report.get('source_commit')
    proof=report.get('source_proof',{})
    modules=proof.get('module_sha256s',{})
    world=report.get('world_binding',{})
    if (not _hash(source,40) or expected_source is not None and source!=expected_source
            or world.get('source_commit')!=source
            or not _hash(world.get('model_digest')) or not _hash(world.get('corpus_sha256'))
            or proof.get('current_scientific_and_comparator_modules_match_experiment_commit') is not True
            or not modules or not all(_hash(value) for value in modules.values())):
        raise ValueError('audited experiment source/model/corpus binding required')
    claims=report.get('claims',{})
    if (claims.get('actual_fixed_weight_Qwen') is not True
            or any(claims.get(k) is not False for k in ('exact_Qwen_Jacobian',
                'full_native_world_autograd','held_out_generalization','causal_scientific_benefit'))
            or any(claims.get(k)!=0 for k in ('new_model_calls','new_native_worlds',
                'new_container_or_generated_source_executions'))):
        raise ValueError('audit claim boundaries must exclude new calls and native/Qwen Jacobian claims')
    valid=report.get('technical_validity',{})
    if (valid.get('completed_worlds')!=6 or valid.get('planned_world_budget')!=6
            or valid.get('failures')!=[]
            or valid.get('all_completed_checkpoints_remeasured') is not True
            or valid.get('all_completed_raw_response_projections_rejoined') is not True):
        raise ValueError('exactly six completed, remeasured physical worlds required; no failure penalties')
    rows=report.get('endpoints',[])
    if len(rows)!=6 or [r.get('name') for r in rows]!=list(NAMES):
        raise ValueError('six rows in exact calibration/unused/candidate order required')
    if [r.get('theta') for r in rows[:5]]!=[.2,.5,.8,.35,.65]:
        raise ValueError('preregistered calibration/unused coordinates differ')
    if report.get('world_order')!=[{'name':r['name'],'theta':r['theta']} for r in rows]:
        raise ValueError('audited physical world order differs')
    if (report.get('objective',{}).get('role')!='optimization-loss'
            or report['objective'].get('hard_loss_replayed_for_every_completed_world') is not True
            or report['objective'].get('loss_spec',{}).get('id')!='native-joint-v5-net-reviewed-utility'):
        raise ValueError('fixed replayed native utility objective required')
    for row in rows:
        measurements=row.get('objective_measurements',{})
        native=_finite(row.get('native_loss'))
        a=_finite(measurements.get('native.accepted_decisions'))
        q=_finite(measurements.get('native.accepted_peer_score_sum'))
        r=_finite(measurements.get('native.review_records'))
        if (not _same(native,3.25*a-q+.05*r) or not _same(native,row.get('hard_represented_loss'))
                or not _hash(row.get('checkpoint_sha256')) or not _hash(row.get('system_fingerprint'))
                or type(row.get('response_count')) is not int or row['response_count']<=0):
            raise ValueError('endpoint native loss, raw objective measurements, replay or identity differs')
    counts=_response_counts(report,rows)
    analysis=report.get('response_operator_analysis')
    if not isinstance(analysis,dict) or not _hash(analysis.get('operator_representation_sha256')):
        raise ValueError('complete calibration-only response operator analysis required')
    freeze=analysis.get('freeze_order_proof',{})
    if (freeze.get('calibration_only_operator_reconstructed') is not True
            or freeze.get('unused_outcomes_seen')!=0
            or freeze.get('frozen_file_content_matches_current_bytes') is not True
            or freeze.get('historical_creation_time_authenticated') is not False
            or analysis.get('all_control_check',{}).get('status')!='exact-control-invariants-verified'
            or analysis['all_control_check'].get('world_count')!=6):
        raise ValueError('calibration-only freeze and six-world control proof required')
    backward=analysis.get('center_backward',{})
    if (backward.get('coordinates')!=[.5]
            or backward.get('native_derivative_verified') is not False
            or backward.get('full_native_world_autograd') is not False):
        raise ValueError('center represented-gradient scope differs')
    gradients=[]
    for key in ('gradient','frozen_boundary_gradient','learned_response_contribution'):
        values=backward.get(key)
        if not isinstance(values,list) or len(values)!=1:
            raise ValueError('exactly one represented gradient coordinate required')
        gradients.append(_finite(values[0]))
    if not _same(gradients[0]-gradients[1],gradients[2]):
        raise ValueError('point-gradient contribution does not equal total minus frozen')
    proposal=analysis.get('frozen_proposal',{}).get('proposal',{})
    expected_candidate=min(.8,max(.2,.5+min(.1,max(-.1,-.02*gradients[0]))))
    if (proposal.get('unused_outcomes_seen')!=0 or not _same(proposal.get('candidate'),expected_candidate)
            or not _same(rows[5]['theta'],expected_candidate)):
        raise ValueError('candidate differs from predeclared frozen point-gradient rule')
    temperature=analysis.get('temperature_selection',{})
    candidates=temperature.get('candidates',[]);selected=temperature.get('selected_index')
    if (type(selected) is not int or not 0<=selected<len(candidates)
            or temperature.get('unused_endpoints_seen')!=0):
        raise ValueError('calibration-only temperature selection missing')
    calibration=candidates[selected]
    predictions=calibration.get('predicted_calibration_losses',[])
    if (len(predictions)!=3 or calibration.get('native_calibration_losses')!=[r['native_loss'] for r in rows[:3]]):
        raise ValueError('calibration predictions or native observations differ')
    plotted=[{'name':r['name'],'theta':r['theta'],'native_loss':r['native_loss'],
        'predicted_loss':_finite(p),'role':'calibration','diagnostic_status':'fit-data'}
        for r,p in zip(rows[:3],predictions)]
    checks=analysis.get('unused_checks',[])
    if len(checks)!=2:
        raise ValueError('two unused endpoint checks required')
    for row,check,role in zip(rows[3:],checks+[analysis.get('candidate_check',{})],
                              ['unused','unused','frozen-candidate']):
        if check.get('checkpoint_sha256')!=row['checkpoint_sha256'] or not _same(check.get('native_loss'),row['native_loss']):
            raise ValueError('predictions must bind their exact physical endpoint')
        predicted=check.get('predicted_loss');status=check.get('status','')
        if predicted is None:
            if not status.startswith('unsupported'):
                raise ValueError('missing predictions require explicit unsupported status, never zero')
        else:
            _finite(predicted)
            if (status not in ('passed-unused-native-endpoint','failed-unused-native-fidelity')
                    or not _same(check.get('absolute_error'),abs(predicted-row['native_loss']))):
                raise ValueError('plotted endpoint error/status differs')
        plotted.append({'name':row['name'],'theta':row['theta'],'native_loss':row['native_loss'],
                        'predicted_loss':predicted,'role':role,'diagnostic_status':status})
    finite=analysis.get('unused_finite_path',{})
    actual_delta=rows[4]['native_loss']-rows[3]['native_loss']
    path_status=finite.get('status','')
    if path_status.startswith('unsupported'):
        path={'status':path_status,'actual_native_delta':actual_delta,
              'response_delta':None,'frozen_delta':None,'response_error':None,'frozen_error':None}
    else:
        response=_finite(finite.get('predicted_finite_delta'))
        frozen=_finite(finite.get('frozen_boundary_predicted_finite_delta'))
        if (path_status not in ('passed-unused-native-finite-path-check','failed-unused-native-finite-path-fidelity')
                or not _same(finite.get('actual_native_delta'),actual_delta)
                or not _same(finite.get('response_aware_native_error'),abs(response-actual_delta))
                or not _same(finite.get('frozen_boundary_native_error'),abs(frozen-actual_delta))
                or finite.get('native_derivative_verified') is not False
                or finite.get('full_native_world_autograd') is not False):
            raise ValueError('unused finite-change predictions/errors/scope differ')
        path={'status':path_status,'actual_native_delta':actual_delta,
              'response_delta':response,'frozen_delta':frozen,
              'response_error':abs(response-actual_delta),'frozen_error':abs(frozen-actual_delta)}
    delta=rows[5]['native_loss']-rows[1]['native_loss']
    outcome='improved' if delta<0 else 'worse' if delta>0 else 'tied'
    if not _same(analysis.get('candidate_minus_center_native_loss'),delta) or analysis.get('candidate_improvement_status')!=outcome:
        raise ValueError('actual candidate outcome must retain improvements, ties and worse results')
    return {'classification':FIXTURE if fixture else ACTUAL,'source_commit':source,
        'audit_content_sha256':report['content_sha256'],'endpoints':plotted,
        'gradients':dict(zip(('total','frozen','response_contribution'),gradients)),
        'unused_finite_path':path,'candidate':{'theta':rows[5]['theta'],'native_loss':rows[5]['native_loss'],
            'center_native_loss':rows[1]['native_loss'],'delta':delta,'outcome':outcome},
        'physical_reply_count':report['physical_reply_count'],'temperature':calibration['temperature'],**counts}


def _limits(values):
    low,high=min([0.,*values]),max([0.,*values])
    span=high-low or 1.
    return low-.24*span,high+.30*span


def create(report_path, output, *, expected_source=None, allow_synthetic=False):
    report_path,output=Path(report_path),Path(output)
    report=decode_json(report_path.read_text(),strict=True,finite_floats=True)
    data=figure_data(report,expected_source=expected_source,allow_synthetic=allow_synthetic)
    if data['classification']==FIXTURE and not output.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError('synthetic fixtures may render only in the system temporary directory, never paper assets')
    raw=report.get('raw_output_root')
    if raw and output.resolve().is_relative_to(Path(raw).resolve()):
        raise ValueError('figure output cannot mutate immutable native raw evidence')
    paths={kind:output.with_suffix('.'+kind) for kind in ('png','svg')}
    manifest_path=output.with_suffix('.manifest.json')
    if report_path.resolve() in [p.resolve() for p in (*paths.values(),manifest_path)]:
        raise ValueError('figure outputs cannot overwrite the independent input audit')
    output.parent.mkdir(parents=True,exist_ok=True)
    coupled=data['response_coupling'] is not None
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':8,
            'axes.spines.top':False,'axes.spines.right':False,
            'svg.fonttype':'none','svg.hashsalt':data['audit_content_sha256']}):
        fig,axes=plt.subplots(2,2,figsize=(5.5,6.),gridspec_kw={'width_ratios':[1.35,1]})
        fig.subplots_adjust(left=.13,right=.975,top=.765,bottom=.23,wspace=.53,hspace=.96)
        a,b,c,d=axes.flat
        points=data['endpoints']
        loss_limits=_limits([p[k] for p in points for k in ('native_loss','predicted_loss') if p[k] is not None])
        for i,p in enumerate(points):
            a.scatter(i-.08,p['native_loss'],s=24,color=BLUE,zorder=4)
            if p['predicted_loss'] is not None:
                a.scatter(i+.08,p['predicted_loss'],s=28,color=ORANGE,marker='x',linewidth=1.3,zorder=5)
            else:
                a.text(i,.97,'n/a',transform=a.get_xaxis_transform(),ha='center',va='top',fontsize=6.2,color=GREY)
        for start,end,color in ((-.5,2.5,BLUE),(2.5,4.5,ORANGE),(4.5,5.5,PURPLE)):
            a.axvspan(start,end,color=color,alpha=.055,zorder=0)
        a.set(ylim=loss_limits,xlim=(-.5,5.5),ylabel='Native / predicted loss L')
        labels=[]
        for name,p in zip(('C0','C1','C2','U0','U1','G'),points):
            flag='*' if p['diagnostic_status'].startswith(('failed','unsupported')) else ''
            labels.append(f'{name}{flag}\n{p["theta"]:.3g}')
        a.set_xticks(range(6),labels,fontsize=7)
        a.set_title('(a) Six logical worlds' if coupled else '(a) Six reset worlds',loc='left',fontsize=8.7,pad=10)
        a.text(.0,-.40,'C: calibration · U: unused · G: frozen candidate\n* Fidelity failed / unsupported',transform=a.transAxes,fontsize=6.5,color='#52616C',va='top')
        gradient=data['gradients']
        for y,(key,label,color) in zip([2,1,0],(('total','Total',BLUE),('frozen','Frozen',GREY),('response_contribution','Learned\nresponse',ORANGE))):
            value=gradient[key]
            b.barh(y,value,height=.44,color=color)
            b.annotate(f'{value:.3g}',(value,y),xytext=(4 if value>=0 else -4,0),
                       textcoords='offset points',va='center',ha='left' if value>=0 else 'right',fontsize=7)
        b.set(yticks=[2,1,0],yticklabels=['Total','Frozen','Learned\nresponse'],xlabel='dL / dθ (represented)',
              xlim=_limits(list(gradient.values())),ylim=(-.6,2.6))
        b.set_title('(b) Center point gradient\nθ = 0.5',loc='left',fontsize=8.5,pad=10)
        path=data['unused_finite_path']
        values=[path['actual_native_delta'],path['response_delta'],path['frozen_delta']]
        for y,value,error,color in zip([2,1,0],values,[None,path['response_error'],path['frozen_error']],[TEAL,ORANGE,GREY]):
            if value is None:
                c.text(0,y,'unsupported',va='center',fontsize=6.8,color=GREY)
                continue
            c.barh(y,value,height=.44,color=color)
            label=f'{value:.3g}' if error is None else f'{value:.3g}\n|err|={error:.3g}'
            c.text(.98,y,label,transform=c.get_yaxis_transform(),va='center',ha='right',fontsize=6.7,
                   bbox={'facecolor':'white','alpha':.85,'edgecolor':'none','pad':.4})
        c.set(yticks=[2,1,0],yticklabels=['Native','Response-\naware','Frozen'],xlabel='Finite loss change ΔL',
              xlim=_limits([v for v in values if v is not None]),ylim=(-.6,2.6))
        c.set_title('(c) Unused finite change\nθ: 0.35 → 0.65',loc='left',fontsize=8.5,pad=10)
        status='unsupported' if path['status'].startswith('unsupported') else 'passed' if path['status'].startswith('passed') else 'FAILED'
        c.text(0,-.55,'Finite-path diagnostic: '+status,transform=c.transAxes,fontsize=6.8,color='#52616C')
        candidate=data['candidate']
        d.scatter([0,1],[candidate['center_native_loss'],candidate['native_loss']],s=45,
                  color=[BLUE,PURPLE],marker='D',zorder=4)
        for x,value in enumerate([candidate['center_native_loss'],candidate['native_loss']]):
            d.annotate(f'{value:.4g}',(x,value),xytext=(0,7),textcoords='offset points',ha='center',fontsize=7)
        d.set(ylim=loss_limits,xlim=(-.55,1.55),ylabel='Actual native loss L')
        d.set_xticks([0,1],[f'Center\nθ = 0.5',f'Candidate\nθ = {candidate["theta"]:.4g}'],fontsize=7)
        d.set_title('(d) Native reevaluation',loc='left',fontsize=8.5,pad=10)
        d.text(0,-.55,f'ΔL = {candidate["delta"]:+.4g} · {candidate["outcome"]}',transform=d.transAxes,fontsize=7,color='#52616C')
        for ax in axes.flat:
            ax.axhline(0,color='#CAD2D8',linewidth=.65,zorder=0) if ax in (a,d) else ax.axvline(0,color='#CAD2D8',linewidth=.65,zorder=0)
            ax.grid(axis='y' if ax in (a,d) else 'x',alpha=.15)
            ax.set_axisbelow(True)
            ax.tick_params(labelsize=7)
            (ax.yaxis if ax in (a,d) else ax.xaxis).set_major_locator(MaxNLocator(nbins=4))
        fixture=data['classification']==FIXTURE
        fig.text(.045,.97,'SCHEMA FIXTURE · NOT ACTUAL QWEN' if fixture else 'Qwen response-aware institutional update',
                 fontsize=11,weight='bold',va='top',color='#85404C' if fixture else '#223746')
        subtitle=(f'6 common-prefix-coupled development worlds · {data["fresh_physical_reply_count"]} fresh / '
                  f'{data["logical_response_count"]} logical replies') if coupled else (
                  f'6 reset development worlds · {data["physical_reply_count"]} physical Qwen replies · one seed')
        fig.text(.045,.916,'Synthetic fixture values · no model/native calls' if fixture else subtitle,fontsize=7.4,color='#52616C')
        fig.legend(handles=[Line2D([],[],marker='o',linestyle='',color=BLUE,label='Actual native loss'),
            Line2D([],[],marker='x',linestyle='',color=ORANGE,label='Fitted response prediction')],
            loc='upper left',bbox_to_anchor=(.028,.886),ncol=2,fontsize=7.6,frameon=False,handletextpad=.45,columnspacing=1.6)
        fig.text(.045,.065,'Learned response representation, not a Qwen/native-world Jacobian.',fontsize=7.2,color='#714955')
        fig.text(.045,.037,'Unused coordinates are development checks, not held-out seeds or causal benefit.',fontsize=7.0,color='#52616C')
        if coupled:
            origin=data['response_coupling']['unique_anchor_prefix_calls']
            fig.text(.045,.095,f'Actual prefix replayed · {origin} anchor-origin calls counted separately from new fresh calls.',fontsize=6.7,color='#52616C')
        try:
            fig.savefig(paths['png'],dpi=220,facecolor='white',metadata={'Software':'ScienceUtopiaLab audited v9 figure'})
            fig.savefig(paths['svg'],facecolor='white',metadata={'Date':None,'Creator':'ScienceUtopiaLab audited v9 figure'})
        finally:
            plt.close(fig)
    receipt={'schema':'scienceutopia.native-qwen-response-figure.v9',**data,
        'audit_file_sha256':file_sha256(report_path),'new_model_calls':0,'new_native_worlds':0,
        'exact_Qwen_or_native_Jacobian_claim':False,'matplotlib_version':matplotlib.__version__,
        'generator_file_sha256':file_sha256(Path(__file__)),
        'outputs':{kind:{'path':str(path.resolve()),'sha256':file_sha256(path)} for kind,path in paths.items()}}
    receipt['content_sha256']=digest(receipt)
    write_json_atomic(manifest_path,receipt,sort_keys=True,allow_nan=False)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-source')
    args=parser.parse_args()
    create(args.report,args.output,expected_source=args.expected_source)
