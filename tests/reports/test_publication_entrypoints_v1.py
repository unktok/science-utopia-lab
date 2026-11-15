"""Current reader pointers must not silently select an older manuscript snapshot."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]


def test_first_integrated_pdf_pointer_matches_the_latest_closed_receipt():
    text=(ROOT/'paper/README.md').read_text()
    paths=re.findall(r'\]\((\.\./output/pdf/[^)]+\.pdf)\)',text)
    receipt=json.loads((ROOT/'paper/integrated-choice-resource-build-v1.json').read_text())
    first=(ROOT/'paper'/paths[0]).resolve()
    assert first==ROOT/receipt['output']
    assert hashlib.sha256(first.read_bytes()).hexdigest()==receipt['pdf_sha256']
    assert f"{receipt['pages']}-page integrated draft" in text
    assert f"with{receipt['figures']} figures,{receipt['tables']} tables" in text
    assert not receipt['publication_ready']
    assert receipt['scientific_scope']['new_scientific_model_calls_by_manuscript_work']==0
    assert receipt['scientific_scope']['previous_receipt_scope']['own_slots']==12
    current=text.split('## Earlier reviewed snapshots',1)[0]
    assert 'five physical frozen\nevaluation worlds remain' in current
    assert 'all three original-choice controls' in current
    assert 'not a focused main-track-ready' in current
    assert receipt['source_commit'] in current and receipt['pdf_sha256'] in current


def test_earlier_resource_pdf_keeps_its_own_literal_identity():
    # Updating the latest-pointer assertion must not discard the old artifact
    # or make its source-bound receipt a certificate for the newer PDF.
    receipt=json.loads((ROOT/'paper/integrated-native-resource-build-v1.json').read_text())
    assert hashlib.sha256((ROOT/receipt['output']).read_bytes()).hexdigest()==receipt['pdf_sha256']
    assert not receipt['scientific_scope']['new_objective_actual_model_optimization_claimed']


def test_historical_longitudinal_document_proof_preserves_its_own_reviewed_artifact():
    import subprocess
    from scripts.reports.paper_rebuild_bundle import integrated_expected, literal_dependencies
    from utopia.optimization.native_numeric_designer import checked
    receipt=checked(json.loads((ROOT/'paper/integrated-longitudinal-build-v1.json').read_text()))
    old=checked(json.loads((ROOT/'paper/integrated-staged-actual-build-v1.json').read_text()))
    proof=checked(json.loads((ROOT/'research/results/integrated-longitudinal-rebuild-subset-verification-v1.json').read_text()))
    policy=json.loads((ROOT/'research/publication/paper-rebuild-allowlist-integrated-longitudinal-v1.json').read_text())
    assert (receipt['pages'],receipt['figures'],receipt['tables'],receipt['cited_references'])==(88,46,40,29)
    assert receipt['visual_review']['pages_reviewed']==list(range(1,89))
    assert len(receipt['visual_review']['page_png_sha256'])==88
    assert receipt['build']['rendered_page_identity_verified']
    assert receipt['build']['layout_or_undefined_reference_warnings']==0
    assert receipt['scientific_scope']['fixed_worlds']==5
    assert receipt['scientific_scope']['fixed_logical_labels']==6
    assert not receipt['scientific_scope']['own_advantage_demonstrated']
    assert proof['original_receipt_content_sha256']==receipt['content_sha256']
    assert proof['page_png_sha256']==receipt['visual_review']['page_png_sha256']
    assert proof['all_rendered_page_pixels_match_reviewed_original']
    assert proof['prior_setup_failure']['exit_code']==1
    assert not proof['independent_inference_rerun'] and not proof['publication_ready']
    assert proof['input_files']==len(policy['files'])==74
    assert proof['literal_dependencies']==71
    expected=integrated_expected(ROOT,receipt,policy['entrypoint'])
    historical = lambda name: ((ROOT/name).read_bytes() if name in (receipt['output'],policy['receipt'],'LICENSE')
        else subprocess.check_output(['git','show',receipt['source_commit']+':'+name],cwd=ROOT))
    for name in policy['files']:
        if name not in ('LICENSE',policy['receipt']):
            assert hashlib.sha256(historical(name)).hexdigest()==expected[name]
    bodies={n:historical(n) for n in policy['files']}
    assert literal_dependencies(bodies,policy['entrypoint'],repository_parent_inputs=True)==receipt['literal_dependencies']
    assert hashlib.sha256((ROOT/old['output']).read_bytes()).hexdigest()==old['pdf_sha256']
    assert receipt['preserved_files'][old['output']]==old['pdf_sha256']


def test_navigation_separates_historical_heartbeats_from_current_orientation():
    text=(ROOT/'research/INDEX.md').read_text()
    active,old=text.split('## Records and historical navigation',1)
    assert 'native-longitudinal-postprocessing-v1.md' in active
    assert 'reviewed91-page working PDF' in active
    assert 'index-history-2026-11-15-longitudinal-prefix.md' in old
    assert 'not current heartbeats' in old
    assert 'Latest54-page integrated manuscript' not in active
    archived=(ROOT/'research/index-history-2026-11-15-longitudinal-prefix.md').read_text()
    _,old=archived.split('## Earlier checkpoints and retained studies',1)
    assert 'Earlier live four-world resource assay' in old
    assert 'historical checkpoint' in old


def test_navigation_snapshot_preserves_original_bytes_links_and_compatibility_anchor():
    import subprocess
    from scripts.check_repository_docs import check
    manifest='research/results/repository-navigation-snapshot-2026-11-15-v1.json'
    data=json.loads((ROOT/manifest).read_text())
    snapshots=tuple(row['snapshot'] for row in data['snapshots'])
    result=check(ROOT,documents=snapshots,manifest=manifest)
    assert result['status']=='passed',result['errors']
    assert result['snapshots']==2
    for row in data['snapshots']:
        old=subprocess.check_output(['git','show',data['source_commit']+':'+row['original']],cwd=ROOT)
        retained=(ROOT/row['snapshot']).read_bytes()
        assert retained==old
        assert len(retained)==row['bytes'] and len(retained.splitlines())==row['lines']
    assert all(data[k]==0 for k in ('deleted_worktrees','deleted_raw_artifacts',
        'deleted_branches','new_model_calls','new_scientific_worlds'))
    status=(ROOT/'research/STATUS.md').read_text()
    assert '## Metric-conditioned study execution snapshot' in status
    assert 'status-history-through-v45.md#metric-conditioned-study-execution-snapshot' in status


def test_current_reader_links_exist_and_readiness_is_not_claimed_by_finished_qa():
    for name in ('paper/README.md','research/publication/publication-ready-v3.md'):
        path=ROOT/name;text=path.read_text()
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if '://' not in target and not target.startswith('#'):
                assert (path.parent/target.split('#',1)[0]).exists(),(name,target)
    plan=(ROOT/'research/publication/publication-ready-v3.md').read_text()
    assert '| R2 |' in plan and 'R2の研究上の答えを先取りしない' in plan
    assert '76panel／228応答で正常終了' in plan
    assert '稼働中の目的、候補枠、参照、選択方法は変えない' in plan


def test_stopped_definition_stays_literal_unadopted_and_unevaluated():
    from utopia.system.design_patch import digest
    value=json.loads((ROOT/'research/data/native-objective-initial-stop-v1/submitted-definition.json').read_text())
    evidence=json.loads((ROOT/'research/results/native-objective-budget-stop-and-corrected-launch-v1.json').read_text())
    assert digest(value['definition'])==value['definition_sha256']==evidence['stopped_original']['submitted_inner_definition_sha256']
    assert not value['source_repaired'] and not value['controller_adopted']
    assert value['native_loss'] is None and value['candidate_native_worlds']==0
    assert value['scientific_source_commit']==evidence['stopped_original']['source_commit']
    assert evidence['corrected_source_study']['prior_stop_in_plan'] and evidence['stopped_original']['selected_policy'] is None
