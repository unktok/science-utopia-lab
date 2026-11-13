"""Read-only workflow eligibility after the independent first numeric dispatch.

No winner, loss or partial stopped-study observation is imported as feedback.
This is a prospective scheduling binding, not repair of an old frozen plan.
"""
from pathlib import Path

from scripts.dispatch_native_parameter_after_stop_v1 import SCHEMA as DISPATCH_SCHEMA, read, sha, revision
from scripts.finish_native_institution_loop_v1 import same_files
from scripts.run_pre_scale_completion_chain_v1 import process_identity
from utopia.optimization.native_numeric_designer import checked

SCHEMA = 'scienceutopia.native-workflow-numeric-prerequisite.v2'
PROTOCOL = 'research/protocols/campaigns/native-workflow-after-independent-numeric-v2.md'
ROOT = Path(__file__).resolve().parents[1]
STAGES = ['numeric-run', 'audit-1', 'audit-2', 'costs-1', 'report-1', 'costs-2', 'report-2']


def binding(directory):
    directory = Path(directory).resolve()
    start, plan = [read(directory / name) for name in ('started.json', 'plan.json')]
    if (start['schema'] != DISPATCH_SCHEMA or plan['schema'] != DISPATCH_SCHEMA + '.plan'
            or start['source_commit'] != plan['source_commit']
            or start['numeric_source_commit'] != plan['numeric_source_commit']
            or start['plan_file_sha256'] != sha(directory / 'plan.json')
            or start['original_study_restarted'] is not False
            or plan['historical_unknown_resolved'] is not False
            or plan['old_protocol_criteria_relaxed_in_place'] is not False
            or plan['new_numeric_worlds_upper_bound'] != 6 or plan['new_designer_calls'] != 0):
        raise ValueError('exact independent first numeric dispatch binding required')
    # Check the dispatcher's and scientist's immutable worktrees, not this
    # development tree's HEAD. Neither old source is edited or re-dispatched.
    numeric_root = Path(plan['run'])
    numeric_plan = checked(read(numeric_root / 'plan.json'))
    numeric_start = checked(read(numeric_root / 'started.json'))
    if (numeric_plan['schema'] != 'scienceutopia.native-parameter-comparator.v1.plan'
            or numeric_start['schema'] != 'scienceutopia.native-parameter-comparator.v1.start'
            or numeric_plan['source_commit'] != plan['numeric_source_commit']
            or numeric_plan['content_sha256'] != plan['numeric_plan_content_sha256']
            or numeric_start['plan_sha256'] != numeric_plan['content_sha256']
            or sha(numeric_root / 'plan.json') != plan['numeric_plan_file_sha256']
            or numeric_plan['budget']['native_worlds_upper_bound'] != 6
            or numeric_plan['origin']['run'] == plan['stopped_run']
            or revision(directory.parents[1]) != plan['source_commit']
            or revision(plan['frozen_source']) != plan['numeric_source_commit']):
        raise ValueError('original numeric source/plan/start changed')
    public = read(directory / 'original-public-plan-check.json')
    if public != {'source_commit': numeric_plan['source_commit'], 'plan_sha256': numeric_plan['content_sha256']}:
        raise ValueError('original public numeric plan check differs')
    return {'schema': SCHEMA, 'directory': str(directory), 'protocol': PROTOCOL,
        'protocol_sha256': sha(ROOT / PROTOCOL),
        'started_file_sha256': sha(directory / 'started.json'),
        'dispatcher_plan_file_sha256': sha(directory / 'plan.json'),
        'dispatcher_source_commit': plan['source_commit'], 'pid': start['pid'],
        'numeric_source_commit': numeric_plan['source_commit'], 'numeric_run': str(numeric_root),
        'numeric_plan_file_sha256': sha(numeric_root / 'plan.json'),
        'numeric_plan_content_sha256': numeric_plan['content_sha256'],
        'numeric_started_file_sha256': sha(numeric_root / 'started.json'),
        'numeric_writer_pid': numeric_start['pid'], 'numeric_feedback_imported': False,
        'old_study_reclassified_or_resumed': False}


def require_closed(value):
    root = Path(value['directory'])
    if binding(root) != value:
        raise ValueError('frozen independent numeric prerequisite changed')
    end = read(root / 'ended.json')
    if (end['status'] != 'closed' or [s['stage'] for s in end['steps']] != STAGES
            or any(type(s['exit_code']) is not int or s['exit_code'] != 0 for s in end['steps'])
            or end['science_restarted'] is not False or end['old_unknown_resolved'] is not False
            or any(process_identity(pid) is not None for pid in (value['pid'], value['numeric_writer_pid']))):
        raise ValueError('independent numeric dispatcher/science not normally closed and absent')
    numeric = Path(value['numeric_run'])
    start, terminal = [checked(read(numeric / name)) for name in ('started.json', 'terminal.json')]
    if (terminal['schema'] != 'scienceutopia.native-parameter-comparator.v1.terminal'
            or terminal['status'] != 'closed' or terminal['stage'] != 'closed'
            or terminal['consumed_slots'] != 6 or terminal['completed_observations'] != 6):
        raise ValueError('all original numeric slots must close without invented completion')
    audits = [checked(read(root / ('audit-' + str(i) + '.json'))) for i in (1, 2)]
    a = audits[0]
    if (a != audits[1] or (root / 'audit-1.json').read_bytes() != (root / 'audit-2.json').read_bytes()
            or a['schema'] != 'scienceutopia.native-parameter-comparator-audit.v1'
            or a['source_commit'] != value['numeric_source_commit']
            or a['plan_sha256'] != value['numeric_plan_content_sha256']
            or a['source_proof']['status'] != 'verified-exact-source-closure'
            or a['closure'] != {'started': start, 'terminal': terminal}
            or len(a['worlds']) != 6
            or (root / 'costs-1.json').read_bytes() != (root / 'costs-2.json').read_bytes()
            or same_files(root / 'report-1', root / 'report-2') != end['report_files']):
        raise ValueError('original independent numeric double audit/cost/report closure differs')
    return {'schema': SCHEMA + '.closure', 'ended_file_sha256': sha(root / 'ended.json'),
        'audit_content_sha256': a['content_sha256'], 'numeric_feedback_imported': False,
        'old_unknown_resolved': False}
