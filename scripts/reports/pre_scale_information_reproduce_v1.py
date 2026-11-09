"""Rebuild closed M numerical figures from retained observations, without raw inference.

This checks retained algebra and artifact identities, not the omitted original
requests/checkpoints. The separately recorded original-source full audit is not
repeated by this command.
"""
import argparse
import json
import math
from pathlib import Path
import statistics

from scripts.reports.pre_scale_information_v1 import CONDITIONS,SEEDS,METRICS,number,render
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'research/data/pre-scale-information-v1'
FIGURES=ROOT/'paper/figures/pre-scale-information-v1'


def validate(report):
    checked(report)
    if report['schema']!='scienceutopia.pre-scale-information-report.v1':
        raise ValueError('closed information report required')
    rows=report['rows'];seen=set();lookup={}
    for row in rows:
        c,s=row['condition'],row['seed'];key=(c,s)
        if c not in CONDITIONS or s not in SEEDS or key in seen or row['id']!=f'{c}-s{s}':
            raise ValueError('unique declared world identity required')
        seen.add(key);lookup[key]=row
        if set(row['components'])!=set(METRICS):raise ValueError('all retained raw components required')
        values={k:number(v) for k,v in row['components'].items()}
        for key_count in ('A','R','active','deliveries'):
            value=values[key_count]
            if type(value)!=int or value<0:raise ValueError('nonnegative integer component required')
        a,q,r=(values[k] for k in ('A','Q','R'))
        scores={'throughput':-a,'efficiency':math.fsum([-q,.5*r]),
            'selective':math.fsum([4*a,-q,.1*r])}
        if set(row['scores'])!=set(scores) or any(not math.isclose(number(row['scores'][k]),v,
                rel_tol=1e-12,abs_tol=1e-12) for k,v in scores.items()):
            raise ValueError('retained loss does not match A/Q/R')
        y=row['first_direction_input_year']
        if y is not None and (type(y)!=int or not 1<=y<=4):raise ValueError('input year outside native horizon')
    if seen!={(c,s) for c in CONDITIONS for s in SEEDS}:raise ValueError('all twelve worlds required')
    means={c:{k:statistics.mean(lookup[c,s]['scores'][k] for s in SEEDS)
        for k in ('throughput','efficiency','selective')} for c in CONDITIONS}
    paired=[]
    for s in SEEDS:
        base=lookup['M0',s]
        for c in CONDITIONS[1:]:
            row=lookup[c,s]
            paired.append({'seed':s,'condition':c,
                'loss_difference_from_disconnected':{k:row['scores'][k]-base['scores'][k]
                    for k in ('throughput','efficiency','selective')},
                'component_difference_from_disconnected':{k:row['components'][k]-base['components'][k]
                    for k in METRICS}})
    if means!=report['condition_loss_means'] or paired!=report['paired_differences']:
        raise ValueError('retained means or paired differences do not match individual worlds')
    return report


def table_body(report):
    validate(report);lookup={(r['condition'],r['seed']):r for r in report['rows']};lines=[]
    for i,s in enumerate(SEEDS):
        if i:lines.append(r'\addlinespace')
        for c in CONDITIONS:
            row=lookup[c,s];v=row['components'];scores=row['scores']
            first=row['first_direction_input_year'];year='--' if first is None else str(first)
            fields=[str(s),c,*[format(v[k],'g') for k in ('A','Q','R')],
                format(scores['throughput'],'g'),format(scores['efficiency'],'g'),year]
            lines.append('&'.join(fields)+r'\\')
    return '\n'.join(lines)+'\n'


def reproduce(output):
    if output.exists() or output.resolve().is_relative_to(DATA):raise ValueError('fresh separate output required')
    report=validate(json.loads((DATA/'report.json').read_text()))
    manifest=checked(json.loads((DATA/'manifest.json').read_text()))
    if manifest['report_content_sha256']!=report['content_sha256']:raise ValueError('retained manifest/report join differs')
    inputs={'report.json':DATA/'report.json',
        'information-comparison.png':FIGURES/'information-comparison.png',
        'information-comparison.svg':FIGURES/'information-comparison.svg'}
    if set(manifest['files'])!=set(inputs):raise ValueError('unexpected retained figure set')
    if any(file_sha256(path)!=manifest['files'][name] for name,path in inputs.items()):
        raise ValueError('retained source artifact hash differs')
    output.mkdir(parents=True)
    write_json_atomic(output/'report.json',report,sort_keys=True,allow_nan=False)
    render(report,output)
    for name in inputs:
        if file_sha256(output/name)!=manifest['files'][name]:raise ValueError('rebuilt numerical/figure bytes differ')
    (output/'table-body.tex').write_text(table_body(report))
    result={'schema':'scienceutopia.pre-scale-information-reproduction.v1',
        'input_report_sha256':report['content_sha256'],'original_audit_sha256':report['audit_sha256'],
        'all_twelve_worlds':True,'losses_means_paired_differences_recomputed':True,
        'report_png_svg_bytes_identical':True,'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},
        'raw_audit_repeated':False,'new_model_calls':0,'new_native_worlds':0,'new_code_executions':0}
    write_json_atomic(output/'reproduction.json',{**result,'content_sha256':digest(result)},sort_keys=True,allow_nan=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=reproduce(a.output)
    print(json.dumps({'output':str(a.output),'identical':r['report_png_svg_bytes_identical'],'new_model_calls':0}))


if __name__=='__main__':main()
