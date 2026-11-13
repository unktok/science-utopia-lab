"""Cold reader evidence and waiting jobs, not actual new study results."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT / 'research/results/native-planning-mechanism-readouts-preparation-v1.json').read_text()))


def blob(source, path):
    return subprocess.check_output(['git', 'show', source + ':' + path], cwd=ROOT)


def test_original_full_path_checks_and_three_actual_continuations_remain_separate():
    r = receipt()
    assert r['analysis_source_commit'] == 'efc89316e91e4c1f94aaf2b98036fddf909a423e'
    assert [(q['tests'], q['failures']) for q in r['qa']] == [(21, 1), (21, 0), (1, 0), (39, 0)]
    full = r['full_path']
    assert full['SCRIPTED_HTTP_not_scientific_results']
    assert full['native_worlds'] == 14 and full['annual_checkpoints'] == 56
    assert full['identical_original_cold_audits'] == full['full_score_report_exports'] == 2
    for kind, count, session in [('choices', 3, 31541), ('effects', 3, 17156), ('requests', 2, 22974)]:
        export = full['extra_reader_exports'][kind]
        assert export['worlds'] == 14 and export['two_cold_CLI_exports_match'] and len(export['files']) == count
        job = r['actual_continuations'][kind]; start = checked(job['start'])
        assert job['session'] == session and start['analysis_source_commit'] == r['analysis_source_commit']
        assert not start['new_inference_allowed'] and not start['retry_failed_stages']
        extra = start.get('report_extra_arguments', [])
        if kind == 'requests':
            assert extra == []
        else:
            assert extra[0] == '--frozen-source'
            assert Path(extra[1]).name == 'native-planning-objective-loop-v1-a2'
            assert extra[2:] == (['--scope', 'planning-objective-development'] if kind == 'effects' else [])
    assert not r['actual_scientific_closed_outputs_claimed'] and not r['publication_ready']
    assert not r['new_scientific_inference'] and not r['actual_scientific_loss_or_selection_changed']


def test_exact_historical_reader_and_actual_scientific_decoder_compatibility():
    r = receipt(); source = r['analysis_source_commit']
    for path, expected in r['source_files_sha256'].items():
        assert hashlib.sha256(blob(source, path)).hexdigest() == expected
    compatibility = r['compatibility_with_actual_frozen_scientific_source']
    assert compatibility['source_commit'] == '8cd61578b94d86dd0cf2ff3b0e581d9a2698fc0f'
    assert compatibility['not_an_actual_8cd_scientific_closed_report']
    for row in compatibility['interfaces']:
        old, new = [blob(s, row['path']) for s in (compatibility['source_commit'], source)]
        if row.get('whole_file_identical'):
            assert old == new and hashlib.sha256(old).hexdigest() == row['sha256']
        else:
            functions = [next(n for n in ast.parse(b).body if isinstance(n, ast.FunctionDef) and n.name == row['function']) for b in (old, new)]
            assert ast.dump(functions[0]) == ast.dump(functions[1])
            assert hashlib.sha256(ast.dump(functions[0]).encode()).hexdigest() == row['AST_sha256']
