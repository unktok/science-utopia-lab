"""Native joint software proof does not stand in for actual unused evaluation."""
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]


def test_complete_scripted_path_is_source_bound_and_does_not_claim_scientific_dispatch():
    p=checked(json.loads((ROOT/'research/results/native-joint-fixed-evaluation-preparation-verification-v1.json').read_text()))
    assert p['source_commit']=='2f70116c7c32499e59a7dc5271505d854cc519b0'
    for name,sha in p['source_files'].items():
        raw=subprocess.check_output(['git','show',p['source_commit']+':'+name],cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest()==sha
    assert p['SCRIPTED_native_worlds']==18 and p['SCRIPTED_annual_checkpoints']==72
    assert p['SCRIPTED_role_factory_and_actual_receipt_replay_paths']
    assert p['SCRIPTED_upstream_study_audits_and_unused_inventories_are_fixtures']
    assert p['SCRIPTED_logical_rows']==32 and p['SCRIPTED_missing_own_rows']==2
    assert p['SCRIPTED_all_reference_paired_rows']==128 and p['SCRIPTED_fixed_policy_contrast_rows']==16
    assert len(p['SCRIPTED_core_report_files'])==9 and len(p['SCRIPTED_cold_readers'])==3
    assert p['SCRIPTED_cold_reader_CLI_invocations']==6
    assert all(r['worlds']==18 for r in p['SCRIPTED_cold_readers'].values())
    assert p['SCRIPTED_two_cold_cost_CLI_outputs_match'] and p['SCRIPTED_scientist_replies']==2545
    assert p['SCRIPTED_both_figures_visually_reviewed'] and p['SCRIPTED_figure_watermarks_present']
    assert not any(p[k] for k in ('fixture_seeds_are_actual_evaluation_seeds','actual_evaluation_seeds_chosen',
        'actual_evaluation_prepared','actual_evaluation_dispatched','new_actual_model_calls','new_actual_scientific_worlds',
        'independent_optimizer_replications','scientific_gain_demonstrated','publication_ready'))


def test_closed_native_pilot_has_equal_incumbent_and_best_own_losses_without_reselection():
    r=checked(json.loads((ROOT/'research/data/native-planning-objective-loop-v1/report.json').read_text()))
    for objective,loss,ref_count,total in [('throughput',-18.,4,7),('content-utility',-13.333333333333332,1,4)]:
        own=r['frozen_selection'][objective];best=min(row['scores'][objective] for row in r['references'])
        refs=[row for row in r['references'] if row['scores'][objective]==best]
        assert best==own['loss']==loss
        assert len(refs)==ref_count and len(refs)+len(own['all_tied_ids'])==total
        assert own['selected_id']==own['all_tied_ids'][0]
        assert min(best,own['loss'])==best and best-own['loss']==0


def test_preparation_and_incumbent_notes_have_portable_links():
    result=check(ROOT,documents=('research/components/native-joint-fixed-evaluation-v1.md',
        'research/logbook/2026-11-14-joint-fixed-evaluation-preparation.md',
        'research/publication/optimization-incumbent-vs-generated-output-v1.md',
        'research/protocols/campaigns/native-joint-fixed-evaluation-v1.md'),manifest=None)
    assert result['status']=='passed',result['errors']
