"""Retained real resource projections, no raw-world or model dependency."""
import json
import hashlib
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]


def test_exact_export_files_and_all_actor_boundaries_are_retained():
    data=ROOT/'research/data/native-liquidity-support-v1';figures=ROOT/'paper/figures/native-liquidity-support-v1'
    manifest=checked(json.loads((data/'manifest.json').read_text()))
    report=checked(json.loads((data/'report.json').read_text()))
    assert manifest['report_content_sha256']==report['content_sha256']
    for name,sha in manifest['files'].items():
        assert file_sha256((figures if name.endswith(('.png','.svg')) else data)/name)==sha
    assert len(report['worlds'])==4 and len(report['actor_boundaries'])==80
    assert [w['accepted_decisions'] for w in report['worlds']]==[5,7,7,7]
    assert [w['final_active_founders'] for w in report['worlds']]==[4,5,5,5]
    assert [w['final_resources'] for w in report['worlds']]==[360.,350.,500.,500.]
    assert all(r['initial_five_full_payloads_equal'] for r in report['request_contrasts'])
    assert report['interpretation']['developer_controls'] and not report['interpretation']['policy_search']


def test_manuscript_retains_actual_closed_studies_and_distinguishes_objective_search():
    text=(ROOT/'paper/integrated/native-loop.tex').read_text()
    for needle in ('663 completed scientist responses','600,856 input','66,114 output',
            '228 actual complete replies','101,340 input','32,493 output',
            '499 completed scientist replies','444,035 input','49,595 output',
            'final active founders from four','from five to seven','360 to 350',
            'different','objective-optimal institutions have not thereby been established'):
        assert needle in text
    for path in ('native-code-tested-loop-v1/component-observations.png',
            'native-common-content-readout-v1/fixed-content-ratings.png',
            'native-liquidity-support-v1/resource-controls.png'):
        assert 'figures/'+path in text and (ROOT/'paper/figures'/path).is_file()
    assert 'Actual-model\nsearch under a new objective remains a separate experiment.' in text


def test_new_pdf_binds_actual_committed_sources_and_preserves_previous_snapshot():
    r=json.loads((ROOT/'paper/integrated-native-resource-build-v1.json').read_text())
    assert file_sha256(ROOT/r['output'])==r['pdf_sha256']
    original=lambda name:subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=ROOT)
    base=json.loads(original(r['dependency_manifest_base']))
    for name,group in r['dependency_groups'].items():
        paths=base[name]['files']+group['additional_files']
        values={p:hashlib.sha256(original(p)).hexdigest() for p in paths}
        assert hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()==group['manifest_sha256']
    for name,sha in r['preserved_files'].items():assert file_sha256(ROOT/name)==sha
    assert (r['pages'],r['figures'],r['tables'])==(54,25,21)
    assert r['visual_review']['pages_reviewed_for_layout']==54
    assert r['build']['exit_codes']==[0,0] and r['build']['text_identical']
    assert not r['build']['off_page_text_words'] and not r['scientific_scope']['publication_ready']
