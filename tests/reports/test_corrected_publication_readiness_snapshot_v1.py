"""Check current table transcription/links, never certify publication readiness."""
import json
from pathlib import Path
import re

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / 'research/publication/publication-ready-v3.md'


def read(name): return json.loads((ROOT / name).read_text())


def rows():
    return {match[1]: match[2] for line in PAGE.read_text().splitlines()
        if (match := re.match(r'^\| (R[1-6]) \| (.*) \|$', line))}


def test_same_six_requirements_link_to_current_actual_closure_not_old_prefix():
    table = rows(); assert set(table) == {'R' + str(i) for i in range(1, 7)}
    closed = checked(read('research/results/native-priority-method-comparison-closed-v1.json'))
    assert closed['coverage']['complete_own_slots'] == 24 and closed['coverage']['physical_worlds'] == 27
    assert all(code == 0 for code in closed['actual_exit_codes'].values())
    assert closed['counts_against_visible_reference'] == {'tie': 12, 'worse': 12, 'better': 0}
    assert '旧24枠・27世界は全閉鎖' in table['R1']
    assert '12同点／12悪化／0改善' in table['R2']
    assert all('22件prefix' not in table[key] and '22/24' not in table[key] for key in ('R1', 'R4'))
    totals = closed['author_totals']
    assert f"{totals['completed_steps']}操作／{totals['successful_document_changes']}編集／{totals['duplicate_unchanged_read_observations']}重複read" in table['R4']


def test_latest_pdf_is_literal111_page_artifact_not_a_new_build_or_rebuild_proof():
    table = rows(); paper = checked(read('paper/integrated-priority-method-build-v1.json'))
    assert f"{paper['pages']}頁統合稿" in table['R5']
    assert f"{paper['figures']}図／{paper['tables']}表／{paper['cited_references']}文献" in table['R5']
    assert '111頁版固有の最小source再構築' in table['R5']
    assert '未完' in table['R5'] and '未達' in table['R6']


def test_new_profile_seeds_and_unfinished_scientific_eval_do_not_become_replications():
    table = rows(); dispatch = read('research/results/native-corrected-choice-real-dispatch-v1.json')
    design = dispatch['declared_design']
    assert f"optimizer_seed{design['optimizer_seed']}" in table['R3']
    assert f"replication_seeds{design['replication_seeds']}" in table['R3']
    assert design['optimizer_histories_per_method_objective'] == 1 and design['proposals_per_history'] == 4
    assert '独立反復ではない' in table['R3'] and '選択後評価未実行' in table['R1']
    preparation = read('research/results/native-corrected-choice-fixed-preparation-v1.json')
    assert not preparation['scientific_evaluation_dispatched'] and not preparation['unused_seed_attestation_completed']


def test_all_local_evidence_links_in_current_table_exist():
    for row in rows().values():
        for target in re.findall(r'\]\(([^)]+)\)', row):
            assert not target.startswith(('https:', 'http:'))
            assert (PAGE.parent / target).resolve().is_file(), target


def test_followup_decision_does_not_promote_a_warm_reference_or_add_a_merit_veto():
    decision = (PAGE.parent / 'corrected-pilot-to-main-claim-v1.md').read_text()
    assert 'not a changed optimizer' in decision and 'candidate rejection gate' in decision
    assert 'The own-only scope can be absent' in decision
    assert 'not independent' in decision and 'Do not automatically grow seeds' in decision
    assert 'without imposing an unpaid/fairness veto' in decision
    assert 'R2/R3/R5/R6 remain open' in decision
