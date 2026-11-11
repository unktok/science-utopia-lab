"""Retained real resource projections, no raw-world or model dependency."""
import json
from pathlib import Path

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
