#!/usr/bin/env python3
"""Publication graphics from an immutable v11 audit; no model/source execution."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-open-estimators-independent-audit.v11'
ACTUAL = 'actual-native-qwen-open-estimators-development-v11'
FIXTURE = 'scripted-fixture-not-native-results'
ARMS = ('blackbox', 'score-control-variate')
LOSS_ID = 'native-joint-v5-net-reviewed-utility'
plt.rcParams['svg.hashsalt'] = 'scienceutopia-native-open-estimators-v11'


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _temporary(path):
    return Path(path).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())


def _vector(value):
    if not isinstance(value, dict) or not isinstance(value.get('logits'), dict):
        raise ValueError('missing gradient-vector diagnostics')
    groups = value['logits']
    coordinates = [*sum((groups[k] for k in sorted(groups)), []), *value.get('continuous_mean', [])]
    if not coordinates or any(not _finite(v) for v in coordinates):
        raise ValueError('nonfinite or empty gradient-vector diagnostics')
    return coordinates


def figure_data(report, expected_source=None, *, allow_synthetic=False):
    if not isinstance(report, dict) or report.get('content_sha256') != digest({k:v for k,v in report.items() if k != 'content_sha256'}):
        raise ValueError('audit must be content-hash bound')
    classification = report.get('classification')
    if (report.get('schema') != SCHEMA or report.get('status') != 'complete'
            or classification not in (ACTUAL, FIXTURE) or report.get('physical_native_worlds') != 8
            or report.get('logical_completed_draws') != 8 or set(report.get('arms', {})) != set(ARMS)):
        raise ValueError('figure requires the complete eight-world v11 audit')
    if classification == FIXTURE:
        if not allow_synthetic:
            raise ValueError('synthetic fixtures require an explicit test-only flag')
    elif allow_synthetic:
        raise ValueError('actual reports cannot use the synthetic flag')
    source = report.get('source_commit')
    if (expected_source is not None and source != expected_source
            or classification == ACTUAL and (expected_source is None or not isinstance(source, str)
                or len(source) != 40 or any(c not in '0123456789abcdef' for c in source))):
        raise ValueError('exact actual experiment source pin required')
    claims = report.get('claims', {})
    prohibited = ('held_out', 'causal_institutional_benefit', 'scientific_value',
        'designer_improvement_established', 'full_native_world_pathwise_autograd',
        'variance_reduction_established', 'external_authorship_authenticated')
    if any(claims.get(k) is not False for k in prohibited):
        raise ValueError('claims exceed this development pilot')
    if (claims.get('live_fixed_Qwen_researchers') is not (classification == ACTUAL)
            or claims.get('scripted_researcher_HTTP') is not (classification == FIXTURE)):
        raise ValueError('actual/fixture researcher attribution differs')
    replies = report.get('physical_researcher_responses')
    if (type(replies) is not int or replies <= 0
            or report.get('logical_completed_researcher_responses') != replies
            or report.get('completed_wire_requests') != replies
            or report.get('reused_responses_in_completed_worlds') != 0):
        raise ValueError('actual response / wire counts must match without reuse')
    audit = report.get('audit', {})
    if (audit.get('new_model_calls') != 0 or audit.get('new_container_executions') != 0
            or audit.get('checkpoint_loss_reextracted') is not True
            or audit.get('campaign_updates_and_prior_refits_replayed') is not True
            or audit.get('all_observations_and_exact_ties_retained') is not True
            or not _hash(audit.get('raw_inventory_sha256'))):
        raise ValueError('independent audit proofs missing')
    if classification == ACTUAL and audit.get('replay_source_proofs', {}).get('status') != 'verified-exact-replay-source-blobs':
        raise ValueError('actual source replay proof missing')
    if report.get('matched_initial_definitions', {}).get('matched') is not True:
        raise ValueError('initial method definitions must be audited as matched')
    loss_spec = report.get('loss_spec', {})
    if loss_spec.get('id') != LOSS_ID:
        raise ValueError('fixed native objective differs')
    rows, updates, identities = {}, [], set()
    for arm in ARMS:
        value = report['arms'][arm]
        observations = value.get('observations', [])
        incumbents = value.get('incumbents', {})
        if len(observations) != 4 or len(incumbents.get('path', [])) != 4 or incumbents.get('initial_unevaluated_system_scored') is not False:
            raise ValueError('all four observations and unscored initial state required')
        best, tied, selected = None, [], []
        for index, (row, incumbent) in enumerate(zip(observations, incumbents['path'])):
            if (row.get('generation'), row.get('draw_index')) != (index//2, index%2) or row.get('arm') != arm:
                raise ValueError('generation / draw order differs')
            if (row.get('status') != 'complete' or not _finite(row.get('loss'))
                    or not _hash(row.get('system_fingerprint')) or not _hash(row.get('checkpoint_sha256'))
                    or not isinstance(row.get('observation_id'), str) or row['observation_id'] in identities):
                raise ValueError('all actual endpoint identities and losses required')
            identities.add(row['observation_id'])
            metrics = row.get('metrics', {})
            evaluated = evaluate_loss(loss_spec, [{'run_id': row['observation_id'], 'metrics': metrics}])
            if evaluated.get('status') != 'complete' or evaluated.get('loss') != row['loss']:
                raise ValueError('plotted loss differs from audited native measurements')
            if not isinstance(row.get('latent'), list) or len(row['latent']) != 1 or not _finite(row['latent'][0]):
                raise ValueError('pilot figure requires the recorded one-dimensional latent, not inferred cutoff')
            assignment = row.get('assignment', {})
            if set(assignment) != {'review-aggregation'} or not isinstance(assignment['review-aggregation'], str):
                raise ValueError('recorded algorithm assignment required')
            identity = {k:row[k] for k in ('generation', 'draw_index', 'observation_id', 'system_fingerprint')}
            if best is None or row['loss'] < best:
                best, tied = row['loss'], [identity]
            elif row['loss'] == best:
                tied.append(identity)
            if (incumbent.get('best_loss_so_far') != best or incumbent.get('observed_loss') != row['loss']
                    or incumbent.get('best_observation_ties') != tied
                    or (incumbent.get('generation'), incumbent.get('draw_index')) != (index//2, index%2)):
                raise ValueError('running incumbent or exact tie ledger differs')
            selected.append({**row, 'incumbent_loss': best})
        if incumbents.get('best_loss') != best or incumbents.get('best_observation_ties') != tied:
            raise ValueError('terminal incumbent differs')
        rows[arm] = selected
        saved_updates = value.get('updates', [])
        if len(saved_updates) != 2 or [u.get('generation') for u in saved_updates] != [0, 1]:
            raise ValueError('two generation updates required')
        for generation, update in enumerate(saved_updates):
            mixed = update.get('mixed_report') or {}
            if update.get('generation_error') is not None:
                raise ValueError('failed authoring is not a completed method result')
            estimator = mixed.get('expectation_estimator')
            if arm == 'blackbox':
                if estimator is not None or mixed.get('gradient') is not None:
                    raise ValueError('black-box arm cannot have gradient diagnostics')
                continue
            expected = 'plain-likelihood-ratio' if generation == 0 else 'frozen-prior-control-variate-lr'
            if (not estimator or estimator.get('status') != 'valid' or estimator.get('estimator') != expected
                    or mixed.get('gradient') != estimator.get('gradient')):
                raise ValueError('score-method batch boundary or applied gradient differs')
            vectors = {k:_vector(estimator.get(k)) for k in ('gradient', 'plain_gradient', 'correction_gradient')}
            if len({len(v) for v in vectors.values()}) != 1:
                raise ValueError('gradient diagnostics refer to different coordinates')
            if generation == 0 and (estimator.get('prior_sample_ids') or vectors['gradient'] != vectors['plain_gradient'] or any(vectors['correction_gradient'])):
                raise ValueError('first batch must be plain LR without a prior fit')
            if generation == 1 and set(estimator.get('prior_sample_ids', [])) != {r['observation_id'] for r in rows[arm][:2]}:
                raise ValueError('control fit must use only preceding own-arm native observations')
            updates.append({'generation': generation, 'estimator': expected, 'vectors': vectors,
                'norms': {k: math.sqrt(math.fsum(x*x for x in v)) for k,v in vectors.items()}})
    return {'classification': classification, 'source_commit': source, 'rows': rows,
        'updates': updates, 'physical_researcher_responses': replies,
        'historical_baseline': None, 'initial_system_scored': False}


def create(source, output, expected_source=None, *, allow_synthetic=False):
    source, output = Path(source), Path(output)
    report = json.loads(source.read_text())
    data = figure_data(report, expected_source, allow_synthetic=allow_synthetic)
    if allow_synthetic and (not _temporary(source) or not _temporary(output)):
        raise ValueError('synthetic fixture input and output must remain in system temporary directory')
    targets = [output.with_suffix(suffix) for suffix in ('.png', '.svg', '.manifest.json')]
    raw = Path(report['audit'].get('raw_root', '/nonexistent-v11-raw')).resolve()
    if any(p.resolve().is_relative_to(raw) or p.resolve() == source.resolve() for p in targets):
        raise ValueError('figure must not overwrite source audit or immutable raw evidence')
    colors = {'blackbox':'#d97706', 'score-control-variate':'#008b8b'}
    labels = {'blackbox':'Black box', 'score-control-variate':'Score / prior CV'}
    markers = {'blackbox':'s', 'score-control-variate':'o'}
    offsets = {'blackbox':-.035, 'score-control-variate':.035}
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 5.9), gridspec_kw={'height_ratios':[1.1, 1]})
    loss_axis, latent_axis, algorithm_axis, estimator_axis = axes.flat
    algorithms = sorted({r['assignment']['review-aggregation'] for arm in ARMS for r in data['rows'][arm]})
    for arm in ARMS:
        rows = data['rows'][arm]
        x = [i+1+offsets[arm] for i in range(4)]
        loss_axis.plot(x, [r['loss'] for r in rows], color=colors[arm], marker=markers[arm], lw=1.4, label=f'{labels[arm]} observed')
        loss_axis.step(x, [r['incumbent_loss'] for r in rows], where='post', color=colors[arm], ls='--', lw=1.2, alpha=.85, label=f'{labels[arm]} incumbent')
        latent_axis.plot(x, [r['latent'][0] for r in rows], color=colors[arm], marker=markers[arm], lw=1.4, label=labels[arm])
        algorithm_axis.scatter(x, [algorithms.index(r['assignment']['review-aggregation']) for r in rows], color=colors[arm], marker=markers[arm], s=42, label=labels[arm], zorder=3)
    for axis in (loss_axis, latent_axis, algorithm_axis):
        axis.axvline(2.5, color='#94a3b8', lw=1, ls=':')
        axis.set_xticks([1,2,3,4], labels=['G0 D1','G0 D2','G1 D1','G1 D2'], fontsize=7)
        axis.set_xlim(.75,4.25)
        axis.tick_params(axis='y', labelsize=7)
        axis.grid(alpha=.18)
    loss_axis.set_title('(a) Original-world loss + running incumbent', fontsize=8.3, loc='left')
    loss_axis.set_ylabel('Native loss L (lower is better)', fontsize=8)
    loss_axis.legend(fontsize=5.7, loc='best', framealpha=.85)
    latent_axis.set_title('(b) Actual sampled institutional latent', fontsize=8.3, loc='left')
    latent_axis.set_ylabel('Sampled z — NOT the decision cutoff', fontsize=8)
    latent_axis.legend(fontsize=6.5, loc='best')
    algorithm_axis.set_title('(c) Actual executable aggregation choice', fontsize=8.3, loc='left')
    algorithm_axis.set_yticks(range(len(algorithms)), labels=algorithms, fontsize=7)
    algorithm_axis.set_ylim(-.45,len(algorithms)-.55 if len(algorithms)>1 else .45)
    algorithm_axis.legend(fontsize=6.5, loc='best')
    norm_meta = [('plain_gradient','Plain LR','#64748b'),('gradient','Applied','#008b8b'),('correction_gradient','Exact CV correction','#b45309')]
    for offset,(key,label,color) in zip([-.23,0,.23],norm_meta):
        estimator_axis.bar([u['generation']+offset for u in data['updates']], [u['norms'][key] for u in data['updates']], width=.22, color=color, label=label)
    estimator_axis.set_xticks([0,1],labels=['G0: no prior → LR','G1: prior fit → CV'],fontsize=7)
    estimator_axis.set_title('(d) Score-estimator diagnostics (not variance)', fontsize=8.3, loc='left')
    estimator_axis.set_ylabel('Gradient-vector Euclidean norm', fontsize=8)
    maximum_norm = max(u['norms'][key] for u in data['updates'] for key,_,_ in norm_meta)
    estimator_axis.set_ylim(0,max(.01,maximum_norm)*1.45)
    estimator_axis.tick_params(axis='y', labelsize=7)
    estimator_axis.grid(axis='y',alpha=.18)
    estimator_axis.legend(fontsize=6,loc='best')
    fig.suptitle('Open native institution design: two batches × two draws per method', fontsize=10)
    fig.text(.5,.055,'Fixed objective: L = 3.25A − Q + 0.05R. No scored initial system or historical baseline.',ha='center',fontsize=7,color='#334155')
    fig.text(.5,.032,'One development seed; separate actual worlds. No superiority, replication or variance-reduction claim.',ha='center',fontsize=6.8,color='#334155')
    fig.text(.5,.009,'Source authored externally; conditional algorithm + cutoff distributions optimized. World differentiation is not required.',ha='center',fontsize=6.5,color='#334155')
    if data['classification'] == FIXTURE:
        fig.text(.5,.5,'SCRIPTED SCHEMA FIXTURE — NOT ACTUAL QWEN',ha='center',va='center',rotation=25,fontsize=14,color='#dc2626',alpha=.23,weight='bold')
    fig.tight_layout(rect=(0,.09,1,.96),h_pad=1.6,w_pad=1.8)
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(targets[0],dpi=200,bbox_inches='tight',metadata={'Software':'Science Utopia Lab'})
    fig.savefig(targets[1],bbox_inches='tight',metadata={'Date':None})
    plt.close(fig)
    manifest = {'schema':SCHEMA+'.figure','classification':data['classification'],
        'audit_file_sha256':file_sha256(source),'audit_content_sha256':report['content_sha256'],
        'source_commit':data['source_commit'],'plotted_data':data,
        'outputs':{kind:{'path':str(path),'sha256':file_sha256(path)} for kind,path in zip(('png','svg'),targets)},
        'new_model_calls':0,'new_native_worlds':0,'new_container_executions':0,
        'held_out_claim':False,'optimizer_superiority_claim':False,'variance_reduction_claim':False}
    manifest['content_sha256'] = digest(manifest)
    write_json_atomic(targets[2],manifest,sort_keys=True,allow_nan=False)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected-source',required=True)
    parser.add_argument('--allow-synthetic-temp-only',action='store_true')
    args=parser.parse_args()
    print(json.dumps(create(args.audit,args.output,args.expected_source,
        allow_synthetic=args.allow_synthetic_temp_only),sort_keys=True))


if __name__ == '__main__':
    main()
