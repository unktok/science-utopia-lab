"""Fake stage processes exercise actual public sealed save and closure checks."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_instruction_summary_v1 as module
from utopia.optimization.native_numeric_designer import save, checked


def complete_chain(chain):
    chain.mkdir()
    for label in ('choices', 'effects', 'requests'):
        for i in (1, 2):
            p = chain/(label+'-'+str(i)); p.mkdir()
            save(p/'report.json', {'SCRIPTED': label})
    audits = chain/'audits'; audits.mkdir()
    for label in ('audit', 'costs'):
        for i in (1, 2): save(audits/(label+'-'+str(i)+'.json'), {'SCRIPTED': label})
    # Original audit/cost closure is plain JSON; control chain closure is sealed.
    (audits/'ended.json').write_text(json.dumps({'status': 'closed',
        'audit_file_sha256': module.sha(audits/'audit-1.json'),
        'cost_file_sha256': module.sha(audits/'costs-1.json')}))
    end = {'status': 'closed', 'steps': [{'stage': s, 'exit_code': 0} for s in module.STAGES],
        'designer_POSTs': 0, 'policy_selection': False, 'assay_plan_file_sha256': 'SCRIPTED plan hash',
        'report_files': {label: module.same_files(chain/(label+'-1'), chain/(label+'-2'))
                         for label in ('choices', 'effects', 'requests')}}
    save(chain/'ended.json', end)


def test_real_report_files_and_plain_audit_closure_are_checked(tmp_path):
    chain = tmp_path/'chain'; complete_chain(chain)
    result = module.wait_reports(chain)
    assert result['status'] == 'closed' and len(result['steps']) == 9
    (chain/'effects-2/report.json').write_text('changed')
    with pytest.raises(ValueError, match='postprocessing outputs differ'): module.wait_reports(chain)


def test_stopped_or_missing_terminal_does_not_invent_completion(tmp_path):
    chain = tmp_path/'chain'; chain.mkdir()
    ticks = iter((0., 2.))
    with pytest.raises(ValueError, match='finite summary wait'):
        module.wait_reports(chain, seconds=1, clock=lambda: next(ticks), poll=lambda _: None)
    assert not (chain/'ended.json').exists()
    save(chain/'ended.json', {'status': 'stopped'})
    with pytest.raises(ValueError, match='control chain stopped'): module.wait_reports(chain)


@pytest.mark.parametrize('failure', [None, 'wait', 'summary-1', 'source-change', 'plan-change'])
def test_full_public_wait_export_and_finite_stop_paths(tmp_path, monkeypatch, failure):
    source = tmp_path/'reader'; source.mkdir()
    science = tmp_path/'science'; science.mkdir()
    raw = science/'outputs/assay'; raw.mkdir(parents=True)
    save(raw/'plan.json', {'SCRIPTED': 'not science'})
    chain = tmp_path/'chain'; complete_chain(chain)
    save(chain/'started.json', {'schema': 'scienceutopia.native-instruction-timing-continuation.v1',
        'source_commit': 'a'*40, 'assay_source': str(science), 'assay_output': str(raw)})
    end = checked(json.loads((chain/'ended.json').read_text()))
    # Fresh test fixture has no historical scientific identity; update its own
    # expected checksum before dispatch, never an actual journal.
    (chain/'ended.json').unlink()
    save(chain/'ended.json', {**{k: v for k, v in end.items() if k != 'content_sha256'},
                            'assay_plan_file_sha256': module.sha(raw/'plan.json')})
    original_wait = module.wait_reports; changed = []
    monkeypatch.setattr(module, 'ROOT', source)
    monkeypatch.setattr(module, 'git_binding', lambda p: 'f'*40 if changed else 'a'*40 if p == science else 'b'*40)
    def wait(p, **kwargs):
        if failure == 'wait': raise ValueError('SCRIPTED original stopped')
        result = original_wait(p, **kwargs)
        if failure == 'plan-change': (raw/'plan.json').write_text('SCRIPTED changed')
        return result
    monkeypatch.setattr(module, 'wait_reports', wait)
    events = []
    def execute(argv, **kwargs):
        out = Path(argv[argv.index('--output')+1]); events.append(out.name)
        assert kwargs['timeout'] == 1800 and kwargs['cwd'] == source
        if failure == out.name: return SimpleNamespace(returncode=1)
        out.mkdir(); save(out/'summary.json', {'SCRIPTED': 'same summary'})
        if failure == 'source-change': changed.append(True)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, 'run', execute)
    args = SimpleNamespace(chain=chain, output=source/'outputs/summary')
    if failure is None:
        module.run(args)
        ended = checked(json.loads((args.output/'ended.json').read_text()))
        assert ended['status'] == 'closed' and events == ['summary-1', 'summary-2']
        assert not ended['new_model_calls'] and not ended['visual_review_complete']
    else:
        with pytest.raises(ValueError): module.run(args)
        ended = checked(json.loads((args.output/'ended.json').read_text()))
        assert ended['status'] == 'stopped' and not ended['science_restarted']
        assert events.count('summary-1') <= 1 and events.count('summary-2') <= 1
        if failure in ('wait', 'plan-change'): assert events == []
        if failure in ('summary-1', 'source-change'): assert events == ['summary-1']
