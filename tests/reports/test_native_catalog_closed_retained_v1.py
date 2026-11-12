"""Actual closed exports and source binding; no new model/sandbox execution."""
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from scripts.reports.native_catalog_actuation_summary_v1 import summarize
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-catalog-actuation-v1'


def read(name): return checked(json.loads((DATA / name).read_text()))


def test_complete_actual_control_comparison_retains_all_scores_consumers_and_costs():
    r = checked(json.loads((ROOT / 'research/results/native-catalog-actuation-closed-verification-v1.json').read_text()))
    assert r['scientific_source_commit'] == '60563d8b107dc184a4ca02935e0d6ec9bc8674eb'
    assert r['complete_worlds'] == 3 and r['technical_nulls'] == 0 and r['seed'] == 61001
    assert set(r['closures']) == {'choices', 'effects', 'requests', 'summary'}
    for name, expected in r['retained_files'].items(): assert file_sha256(ROOT / name) == expected
    choices = read('choices.json'); summary = read('summary.json'); costs = read('costs.json')
    assert summarize(choices) == {k: v for k, v in summary.items() if k != 'content_sha256'}
    assert [(w['scores']['throughput'], w['scores']['founder-activity']) for w in summary['worlds']] == [
        (-12., -15.), (-18., -16.), (-18., -16.)]
    assert [w['committed_responses'] for w in summary['worlds']] == [148, 180, 168]
    assert [w['direction_request_attempts'] for w in summary['worlds']] == [9, 10, 0]
    assert [w['verified_catalog_project_effects'] for w in summary['worlds']] == [0, 0, 10]
    assert len(r['advice_choices_exactly_matching_own_actual_agenda']) == 10
    assert [w['annual'][-1]['active_founders'] for w in summary['worlds']] == [2, 2, 2]
    assert [w['annual'][-1]['total_founder_resources'] for w in summary['worlds']] == [50., 40., 40.]
    assert costs['scientist']['completed_responses'] == 496
    assert costs['scientist']['provider_usage']['prompt_tokens']['recorded_sum'] == 518946
    assert costs['scientist']['provider_usage']['completion_tokens']['recorded_sum'] == 45741
    assert set(costs['auxiliary']['groups']) == {'load-scientist'}
    assert costs['auxiliary']['groups']['load-scientist']['request_intents'] == 3
    assert not costs['unknown_usage_imputed']
    assert not r['automatic_invention_demonstrated'] and not r['held_out_evaluation']
    assert not r['independent_optimizer_replications'] and not r['publication_ready']
    assert len(read('requests.json')['complete_observed_input_classes']) == 3
    for name in ('scripts/run_native_catalog_actuation_v1.py', 'scripts/audit_native_catalog_actuation_v1.py',
            'utopia/system/native_catalog_planning.py'):
        assert subprocess.check_output(['git', 'show', r['scientific_source_commit'] + ':' + name], cwd=ROOT) == (ROOT / name).read_bytes()


def test_current_result_navigation_and_literal_data_readme_links_exist():
    docs = ('research/INDEX.md', 'research/STATUS.md', 'research/results/native-catalog-actuation-v1.md',
        'research/data/native-catalog-actuation-v1/README.md', 'research/components/native-catalog-actuation-v1.md',
        'research/components/native-catalog-summary-v1.md')
    assert check(ROOT, documents=docs, manifest=None)['status'] == 'passed'
