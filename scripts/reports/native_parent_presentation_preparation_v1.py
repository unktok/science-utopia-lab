"""Offline literal input projections from every audited closed planning request.

No HTTP dispatch, source execution, old-log repair or new scientific result.
The hypothetical wire has its own labelled offline seed context; it is not a
replacement certificate or a recorded historical provider request.
"""
import argparse
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_bounded_author_context_v45 import capacity_observation
from utopia.optimization.native_designer_decoding_v24 import decoding_contract, designer_payload
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_parent_evidence_v46 import MODE, OPTION
from utopia.optimization.native_staged_author_v15 import (
    build_prompt, build_conversation, call_task, initial_draft,
)
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.parent-presentation-preparation.v1'


def project(binding, started, *, source):
    request, settings = binding['request'], binding['settings']
    if settings['conversation_profile'] != BOUNDED_AUTHORING or started['step'] != 0:
        raise ValueError('exact original first bounded planner request required')
    if OPTION in request.get('strategy_provenance', {}):
        raise ValueError('original control cannot already contain the prospective treatment')
    if digest({k: v for k, v in binding.items() if k != 'binding_sha256'}) != binding['binding_sha256']:
        raise ValueError('original author binding checksum differs')
    if digest(request) != binding['request_sha256'] or digest(started['prompt']) != started['prompt_sha256']:
        raise ValueError('original request or prompt checksum differs')
    result = {}
    for arm in ('control', 'literal'):
        value = clone(request)
        if arm == 'literal':
            value.setdefault('strategy_provenance', {})[OPTION] = MODE
        prompt = build_prompt(value, initial_draft(value), [], image_id=binding['image_id'],
            binding_sha256=binding['binding_sha256'], settings=settings)
        if arm == 'control' and prompt != started['prompt']:
            raise ValueError('default control projection changed from the actual historical prompt')
        data = json.loads(prompt)
        task = call_task(0, settings['max_steps'], conversation_profile=BOUNDED_AUTHORING, prompt=prompt)
        messages = build_conversation(prompt, task, native_tools=True, conversation_profile=BOUNDED_AUTHORING)
        decoding = decoding_contract('staged-v15', role='planner', conversation_profile=BOUNDED_AUTHORING)
        wire = designer_payload('staged-v15', binding['provider_binding'], messages,
            ('offline-parent-presentation-v1', source, binding['request_sha256']),
            max_tokens=settings['max_tokens'], temperature=decoding['temperature'],
            role='planner', conversation_profile=BOUNDED_AUTHORING)
        capacity = capacity_observation(wire)
        if arm == 'literal' and data['literal_current_system'] != request['parent_system']:
            raise ValueError('complete literal parent missing from treatment')
        result[arm] = {'prompt_utf8_bytes': len(prompt.encode()), 'prompt_sha256': digest(prompt),
            'hypothetical_wire_sha256': digest(wire), 'capacity': capacity,
            'planning_parent_evidence': data.get('planning_parent_evidence'),
            'literal_parent_included': data['literal_current_system'] == request['parent_system'],
            'historical_control_prompt_identical': prompt == started['prompt']}
    return result


def export(args):
    source = pinned_revision(ROOT)
    root, out = args.run.resolve(), args.output.resolve()
    paths = [args.audit_one.resolve(), args.audit_two.resolve(), args.report.resolve(), root/'plan.json']
    if (out.exists() or out.is_relative_to(root) or any(p.is_relative_to(out) for p in paths)
            or paths[0] == paths[1] or paths[0].read_bytes() != paths[1].read_bytes()):
        raise ValueError('fresh separate output and two matching original audits required')
    hashes = {str(p): file_sha256(p) for p in paths}
    audit, _, report, plan = [checked(json.loads(p.read_text())) for p in paths]
    before = _inventory(root)
    if (audit['schema'] != 'scienceutopia.native-planning-objective-loop-audit.v1'
            or report['schema'] != 'scienceutopia.native-planning-objective-report.v1'
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or report['source_commit'] != plan['source_commit'] or audit['source_commit'] != plan['source_commit']
            or audit['plan_sha256'] != plan['content_sha256'] or report['plan_sha256'] != plan['content_sha256']
            or report['audit_sha256'] != audit['content_sha256'] or audit['raw_inventory_sha256'] != digest(before)
            or audit['new_model_calls'] or audit['new_code_executions']
            or len(report['slots']) != 6
            or {(s['objective'], s['generation']) for s in report['slots']}
                != {(o, g) for o in ('throughput', 'content-utility') for g in range(3)}):
        raise ValueError('complete exact audited original six-slot planning study required')
    rows = []
    for slot in report['slots']:
        sha = slot['request_sha256']
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('literal original request identity required')
        directory = root/'search'/slot['objective']/'authoring'/('generation-'+sha)/'authoring'/('generation-'+sha)
        inputs = {}
        for filename in ('request.json', 'step-00.started.json'):
            p = directory/filename
            relative = str(p.relative_to(root))
            if not p.is_file() or before.get(relative) != file_sha256(p):
                raise ValueError('original audited first-planner input bytes required')
            inputs[relative] = file_sha256(p)
        binding = json.loads((directory/'request.json').read_text())
        if binding['request_sha256'] != sha or digest(binding['request']['parent_system']) != slot['parent_system_sha256']:
            raise ValueError('report and original request parent differ')
        rows.append({'objective': slot['objective'], 'generation': slot['generation'],
            'request_sha256': sha, 'inputs': inputs,
            'projections': project(binding, json.loads((directory/'step-00.started.json').read_text()), source=source)})
    result = {'schema': SCHEMA, 'analysis_source_commit': source,
        'scientific_source_commit': plan['source_commit'], 'original_audit_content_sha256': audit['content_sha256'],
        'original_report_content_sha256': report['content_sha256'], 'raw_inventory_sha256': digest(before),
        'inputs': hashes, 'slots': rows, 'new_model_calls': 0, 'new_native_worlds': 0,
        'new_code_executions': 0, 'backend_token_capacity_verified': False,
        'actual_backend_readiness_verified': False, 'new_experiment_dispatched': False,
        'scope': 'Six historical first-planner controls reproduce exactly; prospective literal '
            'projections preserve source and join parent observations. Wires are hypothetical, '
            'not dispatched or historical replacements. UTF-8 byte checks are not tokenizer '
            'evidence, real calibration, designer improvement or a causal study.', 'publication_ready': False}
    if (before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in paths}
            or pinned_revision(ROOT) != source):
        raise ValueError('original raw/input or reader source changed')
    out.mkdir(parents=True)
    save(out/'preparation.json', result)
    print(json.dumps({'slots': len(rows), 'preparation_file_sha256': file_sha256(out/'preparation.json'),
                      'new_model_calls': 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'audit-one', 'audit-two', 'report', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__':
    main()
