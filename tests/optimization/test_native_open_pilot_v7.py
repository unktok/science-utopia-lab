"""Runner reporting/writer checks; no inference and no scientific observations."""
import fcntl
from types import SimpleNamespace
import pytest

from scripts.run_native_open_pilot_v7 import main, summarize, derivative_diagnostics


def campaign(records):
    return SimpleNamespace(binding={'world':{'source_commit':'unit-only'}},state={'records':records})


def test_not_yet_executed_is_not_claimed_as_live_qwen(tmp_path):
    report=summarize(campaign([]),tmp_path)
    assert report['status']=='in-progress'
    assert report['configured_researcher_provider']=='qwen3:8b'
    assert report['physical_reply_count']==0
    assert report['claims']['live_fixed_Qwen_researchers'] is False


def test_budget_exhausted_with_invalid_designs_is_not_success(tmp_path):
    records=[{'request':{'generation':i,'strategy_id':'test'},'version_sha256':str(i),
        'draws':[{},{}],'observations':[None,None]} for i in range(2)]
    report=summarize(campaign(records),tmp_path)
    assert report['status']=='budget-complete-with-failures'
    assert report['complete_native_worlds']==0 and len(report['observations'])==4
    assert all(r['observation'] is None for r in report['observations'])


def test_second_writer_is_rejected_before_factory_or_model_access(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.argv',['probe','--output',str(tmp_path),'--data-cache','absent',
        '--inference-lock',str(tmp_path/'http.lock')])
    with (tmp_path/'pilot-writer.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(RuntimeError,match='another native open pilot writer'):
            main()


def test_derivative_diagnostic_failure_is_not_a_fabricated_native_cost_or_zero_gradient(monkeypatch):
    def fail(*a,**k):
        raise ValueError('intentional missing conditional representation')
    monkeypatch.setattr('scripts.run_native_open_pilot_v7.boundary_coverage',fail)
    coverage,backward=derivative_diagnostics(SimpleNamespace(mechanisms=[]),[])
    for report in (coverage,backward):
        assert report['status']=='failed-diagnostic'
        assert not report['native_loss_gradient_verified'] and not report['full_native_world_autograd']
        assert 'loss' not in report and 'gradient' not in report
