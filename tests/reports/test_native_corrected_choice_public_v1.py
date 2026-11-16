"""Opt-in full native/SDK/container software proof, not model performance.

HTTP/corpus/upstream attribution/synchronous child supervision are SCRIPTED.
Keep exact source clean and unchanged until the original pytest exits.
"""
from contextlib import nullcontext
import json
import os
from pathlib import Path
import tempfile

from openai import OpenAI
import pytest

from scripts import run_native_corrected_choice_search_v1 as driver
from scripts import audit_native_corrected_choice_search_v1 as auditor
from scripts.reports import native_priority_method_readout_v1 as readout
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_priority_method_public_v1 import public_mixed_operator_path
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.system import code_mechanisms
from utopia.utils.data_utils import write_json_atomic, file_sha256


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_CORRECTED_CHOICE_PUBLIC_QA')!='1',
    reason='explicit clean-source hardware window with no real inference required')
def test_corrected_four_generation_public_native_cold_cost_and_paired_readouts(tmp_path,fixed_corpus,monkeypatch):
    from types import SimpleNamespace
    declared=os.environ.get('SCIENCE_UTOPIA_CORRECTED_CHOICE_QA_EXTERNAL')
    if not declared:raise ValueError('explicit unused external closure/readout directory required')
    external=Path(declared).resolve()
    if external.exists() or any(external.is_relative_to(p.resolve()) for p in (driver.ROOT,tmp_path)):
        raise ValueError('fresh software export outside source/test raw required before QA')
    external.mkdir(parents=True)
    evidence=public_mixed_operator_path(tmp_path,fixed_corpus,monkeypatch,closure_output=external/'closure',
        driver_module=driver,auditor_module=auditor,corrected=True)
    root,p=evidence['run'],evidence['plan'];before=_inventory(root)
    selected=driver.read(root/'selection.json')
    assert selected['primary_is_measured_best_known_not_own_discovery']
    assert set(selected['own_only_selected'])==set(driver.METHODS)
    assert driver.read(root/'initial-choice-context.json')['actor_projection']
    failed=[w for w in driver.read(external/'closure/audit-1.json')['worlds'] if w['status']=='failed']
    assert len(failed)==1 and failed[0]['method']==driver.METHODS[2]
    def forbidden(*a,**kw):pytest.fail('readout cannot construct SDK/model or execute source')
    monkeypatch.setattr(OpenAI,'__init__',forbidden)
    monkeypatch.setattr(code_mechanisms.DockerCodeExecutor,'execute',forbidden)
    for index in (1,2):
        readout.export(SimpleNamespace(run=root,frozen_source=driver.ROOT,
            audit_one=external/'closure/audit-1.json',audit_two=external/'closure/audit-2.json',
            cost_one=external/'closure/costs-1.json',cost_two=external/'closure/costs-2.json',
            output=external/f'report-{index}'))
    assert all((external/'report-1'/name).read_bytes()==(external/'report-2'/name).read_bytes()
        for name in ('report.json','slots.csv','manifest.json'))
    report=driver.read(external/'report-1/report.json')
    assert len(report['paths'])==len(report['selected'])==len(report['own_only_selected'])==6
    assert all(len(path)==4 for path in report['paths'].values())
    assert report['coverage']['execution_or_measurement_nulls']==1 and report['coverage']['physical_worlds']==27
    assert before==_inventory(root)
    write_json_atomic(tmp_path/'corrected-verification.json',{'schema':'scienceutopia.native-corrected-choice-full-public-QA.v1',
        'source_commit':p['source_commit'],'plan_file_sha256':file_sha256(root/'plan.json'),
        'coverage':report['coverage'],'frozen_primary_and_own_only_endpoints':6,
        'history_lengths':[len(path) for path in report['paths'].values()],
        'known_native_null_retained':True,'actual_current_parameter_component_feedback':True,
        'paired_report_files':{name:file_sha256(external/'report-1'/name) for name in ('report.json','slots.csv','manifest.json')},
        'original_source_cold_and_cost_files':{str(path):file_sha256(path) for path in sorted((external/'closure').iterdir())},
        'actual_model_POSTs':0,'held_out_scientific_seeds_consumed':False,
        'HTTP_corpus_upstream_and_child_supervision':'SCRIPTED','subprocess_CLI_routing_verified':False,
        'new_scientific_result':False,'publication_ready':False},sort_keys=True)
