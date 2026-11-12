"""Join the current working source to the newly closed T/U report."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_all_new_source_table_rows_match_actual_submissions_and_probes():
    r = json.loads((ROOT/'research/data/native-objective-instrument-loop-v1/report.json').read_text())
    text = (ROOT/'paper/integrated/native-loop.tex').read_text()
    rows = [line for line in text.splitlines()
            if line.startswith(('T/g','U/g')) and ' & ' in line]
    assert len(rows) == len(r['slots']) == 8
    for line, slot in zip(rows, r['slots']):
        fields = [x.strip().rstrip('\\') for x in line.split('&')]
        short = 'T' if slot['objective'] == 'throughput' else 'U'
        assert fields[0] == short+'/g'+str(slot['generation'])
        assert fields[1].lower() == slot['status']
        assert fields[2] == ('--' if slot['loss'] is None else '$'+str(int(slot['loss']))+'$')
        assert int(fields[-1].split('\\')[0]) == slot['component_trace']['component_testing']['probe_attempts']
    assert 'sec:native-content-search' in text
    assert 'figures/native-objective-instrument-paper-v1/loss-paths.png' in text
    assert 'not program-equivalence classes' in text
    assert 'no closed held-out result' in text


def test_published_pdf_receipt_is_not_rewritten_for_unbuilt_working_source():
    r = json.loads((ROOT/'paper/integrated-estimands-build-v1.json').read_text())
    assert r['source_commit'] == '7f8a39bf9dbf87a4bb6f88911e575937ae64ce4c'
    assert r['pages'] == 56 and r['figures'] == 26 and r['tables'] == 21
    content_map = (ROOT/'paper/integrated-content-map.md').read_text()
    assert 'reviewed56-page PDF predates this addition' in content_map
