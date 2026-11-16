"""Inspect retained actual software proof; never rerun models or native worlds."""
import gzip
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'research/data/native-corrected-choice-full-public-v1'


def receipt():return checked(json.loads((ROOT/'research/results/native-corrected-choice-full-public-qa-v1.json').read_text()))


def test_actual_original_handle_source_exit_and_synthetic_boundary_are_preserved():
    r=receipt()
    assert r['original_handle']==67383 and r['actual_exit_code']==0 and r['passed']==1
    assert r['failures']==r['errors']==r['skipped']==0
    assert r['source_commit']=='083f374e0cf446eae64f79a2ec389fe0c884abc3'
    assert r['actual_model_POSTs']==r['new_scientific_losses']==0
    assert not r['real_new_source_model_calibration_verified'] and not r['publication_ready']
    assert not r['subprocess_CLI_routing_verified']
    assert file_sha256(DATA/'JUnit.xml')==r['JUnit_file_sha256']
    assert file_sha256(DATA/'corrected-verification.json')==r['verification_file_sha256']


def test_compressed_exact_cold_and_report_keep_all_attempts_and_both_selections():
    r=receipt();audit_raw=gzip.decompress((DATA/'audit.json.gz').read_bytes())
    report_raw=gzip.decompress((DATA/'report.json.gz').read_bytes())
    audit=checked(json.loads(audit_raw));report=checked(json.loads(report_raw))
    assert audit['content_sha256']==r['paired_audit_content_sha256']
    assert report['content_sha256']==r['paired_report_content_sha256']
    expected=r['verification']['original_source_cold_and_cost_files']
    assert hashlib.sha256(audit_raw).hexdigest()==next(h for p,h in expected.items() if p.endswith('audit-1.json'))
    assert hashlib.sha256(report_raw).hexdigest()==r['verification']['paired_report_files']['report.json']
    assert report['coverage']=={'declared_own_slots':24,'complete_own_slots':23,'generation_nulls':0,
        'execution_or_measurement_nulls':1,'physical_worlds':27}
    assert len(report['selected'])==len(report['own_only_selected'])==len(report['paths'])==6
    assert all(len(path)==4 for path in report['paths'].values())
    assert len(audit['source_proof']['files'])==r['actual_exact_source_file_count']==351


def test_all_actual_current_parameter_probes_are_counted_and_failures_are_not_hidden():
    r=receipt();rows=r['all8_actual_component_sessions']
    assert len(rows)==8 and sum(v['actual_component_probes'] for v in rows)==r['actual_component_probes']==32
    assert r['actual_component_probe_statuses']=={'returned':28,'raised':4}
    assert r['all_probes_use_current_marker_and_priority_parameters']
    assert sorted(v['generation'] for v in rows)==[0,0,1,1,2,2,3,3]
    assert r['intentional_submitted_execution_nulls']==1 and r['actual_completed_native_worlds']==26


def test_paired_export_manifests_and_all_slot_csv_are_exact_original_outputs():
    r=receipt()
    assert (DATA/'report-manifest-1.json').read_bytes()==(DATA/'report-manifest-2.json').read_bytes()
    assert file_sha256(DATA/'report-manifest-1.json')==r['verification']['paired_report_files']['manifest.json']
    assert file_sha256(DATA/'slots.csv')==r['verification']['paired_report_files']['slots.csv']
