"""Current reader pointers must not silently select an older manuscript snapshot."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]


def test_first_integrated_pdf_pointer_matches_the_latest_closed_receipt():
    text=(ROOT/'paper/README.md').read_text()
    paths=re.findall(r'\]\((\.\./output/pdf/[^)]+\.pdf)\)',text)
    receipt=json.loads((ROOT/'paper/integrated-native-resource-build-v1.json').read_text())
    first=(ROOT/'paper'/paths[0]).resolve()
    assert first==ROOT/receipt['output']
    assert hashlib.sha256(first.read_bytes()).hexdigest()==receipt['pdf_sha256']
    assert f"{receipt['pages']}-page integrated draft" in text
    assert f"with{receipt['figures']} figures and{receipt['tables']} tables" in text
    assert not receipt['scientific_scope']['new_objective_actual_model_optimization_claimed']
    assert 'not\ncompleted evidence in this PDF' in text
    assert 'running experiment' not in text


def test_navigation_separates_historical_heartbeats_from_current_orientation():
    text=(ROOT/'research/INDEX.md').read_text()
    active,old=text.split('## Earlier checkpoints and retained studies',1)
    assert 'native-objective-instrument-loop-v1.md' in active
    assert 'Latest54-page integrated manuscript' in active
    assert 'Earlier live four-world resource assay' in old
    assert 'historical checkpoint' in old


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
