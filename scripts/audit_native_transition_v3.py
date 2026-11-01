#!/usr/bin/env python3
"""Read-only independent native-data, representation and derivative audit.

Partial audits never establish completion. Numerical differences here test the
fitted representation's autograd, NOT native-world derivatives.
"""
from dataclasses import asdict
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def direction_records(root, *, year, author_ids):
    """Match actual fixed-agent direction requests, not HTTP arrival positions."""
    from utopia.system.code_mechanisms import sha
    rows = [json.loads(line) for line in (root / 'wire-requests.jsonl').read_text().splitlines()]
    db = sqlite3.connect((root / 'replies/responses.sqlite').as_uri() + '?mode=ro', uri=True)
    try:
        replies = {p: json.loads(d)['choices'][0]['message']['content'] for p, d in db.execute('SELECT payload_sha,data FROM replies')}
    finally:
        db.close()
    values, counts, unmatched = {}, {}, 0
    for row in rows:
        payload = row['payload']
        if row['year'] != year or payload.get('response_format', {}).get('json_schema', {}).get('name') != 'research_direction_selection':
            continue
        prompt = '\n'.join(str(m['content']) for m in payload['messages'] if m['role'] == 'user')
        match = re.search(r'university researcher at ([\w-]+)\.', prompt)
        matches = [uid for uid in author_ids if match and uid.startswith(match[1] + '_researcher_')]
        if len(matches) != 1:
            unmatched += 1
            continue
        uid = matches[0]
        ordinal = counts.get(uid, 0)
        counts[uid] = ordinal + 1
        key = (uid, 'research-direction', ordinal)
        history = prompt.split('Now, you are trying to decide the research direction of your next project.', 1)[-1].split('## Your Funding Situation', 1)[0]
        values[key] = {'author_id': uid, 'activity': key[1], 'within_author_call': ordinal,
            'request_seed': payload.get('seed'), 'request_sha256': row['payload_sha256'],
            'message_sha256': sha(payload['messages']), 'publication_history_view_sha256': sha(history),
            'reply_content_sha256': sha(replies[row['payload_sha256']])}
    return values, unmatched


def compare_direction_records(left, right, *, author_ids, year=3):
    a, ua = direction_records(left, year=year, author_ids=author_ids)
    b, ub = direction_records(right, year=year, author_ids=author_ids)
    shared = sorted(a.keys() & b.keys())
    return {'year': year, 'matching': 'actual author ID, research-direction activity, within-author call ordinal; not HTTP arrival order',
        'left_only': len(a.keys() - b.keys()), 'right_only': len(b.keys() - a.keys()),
        'unidentified_requests': [ua, ub], 'pairs': [{**{k: a[key][k] for k in ('author_id', 'activity', 'within_author_call')},
            'same_request_seed': a[key]['request_seed'] == b[key]['request_seed'],
            'messages_changed': a[key]['message_sha256'] != b[key]['message_sha256'],
            'publication_history_view_changed': a[key]['publication_history_view_sha256'] != b[key]['publication_history_view_sha256'],
            'reply_content_changed': a[key]['reply_content_sha256'] != b[key]['reply_content_sha256'],
            'request_hashes': [a[key]['request_sha256'], b[key]['request_sha256']]} for key in shared],
        'limit': 'observed same-seed request/reply differences, not LLM input Jacobians or independently replicated causal effects'}


def audit_transition(run, loss):
    import torch
    from scripts.audit_native_design_loop import audit
    from scripts.audit_native_feedback_v2 import wire_summary
    from utopia.optimization.native_transition_data import extract_trajectory, compile_terminal_loss, verify_saved_trajectory
    from utopia.optimization.native_transition_autograd import NativeTransitionSurrogate, heldout_directional_check
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.code_mechanisms import sha
    from utopia.utils.data_utils import file_sha256
    plan_path = run / 'plan.json'
    before = file_sha256(plan_path)
    plan = json.loads(plan_path.read_text())
    if plan['loss_spec'] != loss:
        raise ValueError('audit objective differs from preregistered native execution')
    world = plan['world']
    trajectories, proofs, cells = [], [], []
    pending = []
    for name, controls in plan['cells']:
        path = run / 'cells' / name
        if not (path / 'trajectory.json').exists():
            pending.append(name)
            continue
        saved = json.loads((path / 'campaign/native-design-state.json').read_text())
        if len(saved['records']) != 1 or saved['pending'] is not None:
            raise ValueError('calibration cell must have exactly one terminal native observation')
        record = saved['records'][0]
        trajectory, evidence, amendment = verify_saved_trajectory(record, json.loads((path / 'trajectory.json').read_text()), run_directory=run / 'runs', source_commit=world['source_commit'],
            model_digest=world['model_digest'], corpus_sha256=world['corpus_sha256'], controls=controls, loss_spec=loss)
        check = audit(path, loss, 3, require_completion=False, native_run_directory=run / 'runs')
        check['rows'][0]['runs'][0]['wire'] = wire_summary(run / 'runs' / trajectory.run_id, needle='not-a-context-probe', required=True)
        trajectories.append(trajectory)
        proofs.append(evidence)
        cells.append({'name': name, 'controls': controls, 'actual_loss': trajectory.declared_terminal_loss,
            'data_identity_amendment': amendment, 'audit': check})
    result = {'schema': 'scienceutopia.native-transition-independent-audit.v3', 'plan_sha256': before,
        'world': world, 'cells': cells, 'pending_cells': pending, 'raw_output_root': str(run),
        'full_native_world_autograd': False, 'status': 'partial-native-data-audit' if pending else 'native-data-audited-analysis-pending'}
    if len(trajectories) >= 4 and not any(name in pending for name, _ in plan['cells'][:4]):
        try:
            model = NativeTransitionSurrogate.fit(trajectories[:4], compile_terminal_loss(loss))
            controls = torch.tensor(plan['gradient_query'], dtype=torch.float64, requires_grad=True)
            value, states, support = model.evaluate(torch.tensor(trajectories[0].states[0], dtype=torch.float64), controls)
            value.backward()
            numeric = torch.zeros_like(controls)
            h = 1e-5
            for i in range(controls.numel()):
                plus, minus = controls.detach().clone(), controls.detach().clone()
                plus.flatten()[i] += h
                minus.flatten()[i] -= h
                # Technical check of represented graph only, not native FD.
                vp, _, _ = model.evaluate(torch.tensor(trajectories[0].states[0]), plus, require_support=False)
                vm, _, _ = model.evaluate(torch.tensor(trajectories[0].states[0]), minus, require_support=False)
                numeric.flatten()[i] = (vp - vm).detach() / (2 * h)
            error = float((numeric - controls.grad).abs().max())
            if error > 1e-5:
                raise ValueError('represented autograd differs from represented numerical derivatives')
            result['representation'] = {'provenance': model.provenance, 'backward_gradient': controls.grad.tolist(),
                'approximate_loss': float(value.detach()), 'predicted_states': states.detach().tolist(),
                'support': support, 'same_representation_central_difference': numeric.tolist(),
                'same_representation_max_absolute_error': error,
                'derivative_scope': 'exact fitted-model autograd; approximate native feature-transition derivatives, not native pathwise backprop'}
            if len(trajectories) == 6:
                result['validation'] = [model.validate_heldout(t) for t in trajectories[4:]]
                result['directional_fidelity'] = heldout_directional_check(model, trajectories[4], trajectories[5])
                original = read_portable_checkpoint(Path(cells[0]['audit']['rows'][0]['runs'][0]['checkpoint']))
                author_ids = [a['id'] for a in original['ecosystem_data']['agents'] if a['can_author']]
                result['actual_year3_researcher_path'] = compare_direction_records(run / 'runs' / trajectories[0].run_id,
                    run / 'runs' / trajectories[2].run_id, author_ids=author_ids)
                result['status'] = 'representation-and-native-validation-audited'
        except (ValueError, RuntimeError) as error:
            result['analysis_error'] = {'type': type(error).__name__, 'message': str(error)}
            result['status'] = 'native-data-valid-representation-or-support-failure'
    if (run / 'representation-result.json').exists():
        report = json.loads((run / 'representation-result.json').read_text())
        if 'representation' not in result or sha(report['backward']['gradient']) != sha(result['representation']['backward_gradient']):
            raise ValueError('saved backward report differs from independently refitted graph')
        result['recorded_representation_sha256'] = file_sha256(run / 'representation-result.json')
        if 'gradient_proposal' in report:
            proposed = report['gradient_proposal']
            saved = json.loads((run / 'cells/gradient-proposal/campaign/native-design-state.json').read_text())
            actual, evidence = extract_trajectory(saved['records'][0], run_directory=run / 'runs', source_commit=world['source_commit'],
                model_digest=world['model_digest'], corpus_sha256=world['corpus_sha256'], controls=proposed['controls'], loss_spec=loss)
            if sha(proposed['trajectory']) != sha(asdict(actual)) or proposed['actual_native_loss'] != actual.declared_terminal_loss:
                raise ValueError('recorded gradient proposal differs from fresh native execution')
            result['gradient_proposal'] = proposed
    if (run / 'completion.json').exists():
        if pending or 'gradient_proposal' not in result and plan['evaluate_proposal'] or 'analysis_error' in result:
            raise ValueError('completion contradicts independent native/representation evidence')
        result['status'] = 'complete-and-independently-audited'
        result['completion'] = json.loads((run / 'completion.json').read_text())
    if file_sha256(plan_path) != before:
        raise ValueError('read-only audit changed or raced the immutable plan')
    return result


if __name__ == '__main__':
    import argparse
    from utopia.optimization.loss import load_loss_spec
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_transition(args.run.resolve(), load_loss_spec(args.loss)), ensure_ascii=False, indent=2, allow_nan=False))
