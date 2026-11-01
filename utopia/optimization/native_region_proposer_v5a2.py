"""Boundary-aligned authoring amendment; historical v5 stays byte-identical.

Only designer syntax, prompt projections and diagnostic text change. The exact
generated Python, explicit wires, old compiler and full native probes are used
unchanged. No institution algorithm or missing semantic connection is supplied.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from utopia.optimization.native_code_trace import validate_record
from utopia.optimization.native_free_source import prompt_view
from utopia.optimization.native_region_design import region_boundary
from utopia.optimization.native_region_ir import boundary_contract, compile_region_ir, region_ir_schema
from utopia.optimization.native_region_proposer import _world_view
from utopia.optimization.native_region_proposer_v5 import probe_authored_region
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import clone
from utopia.utils.data_utils import write_json_atomic


def scoped_authoring_schema_a2(contract):
    """A DAG's first node cannot read any authored node, including itself."""
    schema = clone(region_ir_schema(contract))
    first = clone(schema['properties']['nodes']['items'])
    first['properties']['inputs']['additionalProperties']['properties']['sources']['items'] = {
        'type': 'string', 'enum': ['boundary:' + alias for alias in sorted(contract['inputs'])]}
    schema['properties']['nodes']['prefixItems'] = [first]
    return schema


def designer_boundary_a2(contract):
    """No retired input names, host IDs or endpoint objects to copy as schemas."""
    return {direction: {alias: {**({'reference': 'boundary:' + alias} if direction == 'inputs' else {}),
        'channel': endpoint['channel'], 'artifact_type': endpoint['artifact_type'],
        'payload_schema': {'type': 'object'}} for alias, endpoint in sorted(contract[direction].items())}
        for direction in ('inputs', 'exports')}


def boundary_examples_a2(parent, removed_nodes, records):
    """Project actual ingress values into the *same* aliases used by the IR.

    Raw contexts are neither modified nor used as a new simplified execution
    world. All full records still go unchanged into chronological native probes.
    """
    removed, incoming, _, _, _ = region_boundary(parent, removed_nodes)
    contract = boundary_contract(parent, removed)
    nodes = {n.mechanism_id: n for n in parent.mechanisms if n.mechanism_id in removed}
    phases = {s.mechanism_id: s.phase for s in parent.schedules}
    groups = {}
    for record in records:
        validate_record(record)
        matches = [node for node in nodes if record['artifact'] == nodes[node].parameters['code_artifact']
            and record['context']['phase'] == phases[node]]
        if len(matches) != 1 or record['binding']['system_fingerprint'] != parent.fingerprint:
            raise ValueError('prompt boundary projection requires actual parent implementation records')
        slot = groups.setdefault((record['binding']['run_id'], record['context']['period']), {})
        node = matches[0]
        if node in slot and slot[node]['context'] != record['context']:
            raise ValueError('conflicting actual native contexts in prompt projection')
        slot.setdefault(node, record)
    examples = []
    for (_, period), rows in sorted(groups.items()):
        if set(rows) != removed:
            raise ValueError('complete removed-node contexts required for boundary prompt projection')
        values_by_alias = {}
        for alias, endpoint in contract['inputs'].items():
            candidates = []
            for edge in incoming:
                if (edge.source_mechanism, edge.source_port) != (endpoint['mechanism'], endpoint['port']):
                    continue
                matching = [e for e in incoming if (e.target_mechanism, e.target_port, e.source_mechanism)
                    == (edge.target_mechanism, edge.target_port, edge.source_mechanism)]
                if len(matching) != 1:
                    raise ValueError('actual boundary cannot disambiguate merged source ports')
                candidates.append([v for v in rows[edge.target_mechanism]['context']['inputs'][edge.target_port]
                    if v['source_mechanism'] == edge.source_mechanism])
            if not candidates or any(value != candidates[0] for value in candidates[1:]):
                raise ValueError('actual native ingress fanout values differ')
            projected = []
            for value in candidates[0]:
                payload = value['payload']
                payload = _world_view(payload) if payload.get('schema') == 'scienceutopia.native-world-observation.v1' else clone(payload)
                projected.append({'payload': payload, 'actor_ids': clone(value.get('actor_ids', [])),
                    'artifact_ids': clone(value.get('artifact_ids', [])), 'emitted_period': value['emitted_period']})
            values_by_alias[alias] = projected
        examples.append({'period': period, 'boundary_inputs': values_by_alias,
            'native_bundle_sha256s': [row['bundle_sha256'] for _, row in sorted(rows.items())]})
    return examples


def _region_history_view_a2(system):
    """Exact generated source; mechanically alias all prompt graph endpoints."""
    ids = system.get('metadata', {}).get('native_design_region', {}).get('node_ids', [])
    if not ids:
        return None
    parent = SystemSpec.from_dict(system)
    contract = boundary_contract(parent, ids)
    local = {node: 'm' + str(i) for i, node in enumerate(sorted(ids))}
    ins = {(e['mechanism'], e['port']): 'boundary:' + alias for alias, e in contract['inputs'].items()}
    outs = {(e['mechanism'], e['port']): alias for alias, e in contract['exports'].items()}
    nodes = []
    for node in system['mechanisms']:
        if node['mechanism_id'] in local:
            value = clone(node)
            value['mechanism_id'] = local[node['mechanism_id']]
            nodes.append(value)
    connections = []
    for edge in system['connections']:
        source, target = edge['source_mechanism'], edge['target_mechanism']
        if source not in local and target not in local:
            continue
        connections.append({'source': ('node:' + local[source] + ':' + edge['source_port']) if source in local
                else ins[(source, edge['source_port'])],
            'target': ('node:' + local[target] + ':' + edge['target_port']) if target in local
                else 'export:' + outs[(target, edge['target_port'])], 'channel': edge['channel']})
    return {'mechanisms': nodes, 'connections': connections,
        'execution_order': [local[s['mechanism_id']] for s in sorted(system['schedules'], key=lambda s: s['phase'])
            if s['mechanism_id'] in local],
        'projection_notice': 'Only graph identity/endpoints are mechanically aliased; executed generated source bytes are exact.'}


def _history_a2(history):
    views = []
    for i, record in enumerate(history):
        region = _region_history_view_a2(record['suggestion']['candidate'])
        if region is not None:
            views.append({'index': record['suggestion'].get('proposal_index', i), 'status': record['observation']['status'],
                'actual_loss': record['observation']['loss'], 'region': region})
    return {'regions': views[-2:], 'older_generated_sources_omitted': max(0, len(views) - 2),
        'scope': 'Last at most two generated designs with exact source; no original host source or truncated source.'}


class NativeBoundaryRegionProposer:
    def __init__(self, model, executor, *, removed_nodes, context_provider, receipts,
                 instructions='', max_attempts=3, max_tokens=4096):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
            raise ValueError('bounded technical repair budget 1..5 required')
        if type(max_tokens) is not int or not 512 <= max_tokens <= 8192:
            raise ValueError('explicit token budget 512..8192 required')
        self.model, self.executor = model, executor
        self.removed_nodes = tuple(sorted(removed_nodes))
        self.context_provider, self.receipts = context_provider, Path(receipts)
        self.instructions, self.max_attempts, self.max_tokens = instructions, max_attempts, max_tokens

    def __call__(self, parent, history, index, loss_spec):
        removed = tuple(sorted(parent.metadata.get('native_design_region', {}).get('node_ids', self.removed_nodes)))
        contract = boundary_contract(parent, removed)
        schema = scoped_authoring_schema_a2(contract)
        records = [row for node in removed for row in self.context_provider(node, parent, history)]
        if not records:
            raise ValueError('actual native boundary records required before model generation')
        examples = boundary_examples_a2(parent, removed, records)
        binding = {'schema': 'scienceutopia.native-region-proposal.v5a2',
            'parent_fingerprint': parent.fingerprint, 'history_sha256': sha(history),
            'loss_spec_sha256': sha(loss_spec), 'index': index, 'removed_nodes': list(removed),
            'image_id': self.executor.image_id, 'native_bundle_sha256s': [r['bundle_sha256'] for r in records],
            'instructions_sha256': sha(self.instructions), 'max_attempts': self.max_attempts,
            'authoring_schema_sha256': sha(schema), 'temperature': .2,
            'source_visibility': 'initial-host-withheld-generated-history-exact-source-aliased-graph',
            'boundary_projection': 'actual-ingress-aliases-no-operational-endpoints.v1',
            'prior_generated_source_limit': 2, 'max_tokens': self.max_tokens, 'max_prompt_utf8_bytes': 40000}
        feedback = [{'index': i, 'status': r['observation']['status'], 'loss': r['observation']['loss'],
            'measurements': clone(r['observation'].get('metadata', {}).get('measurements', {}))}
            for i, r in enumerate(history)]
        chosen = sorted({0, len(examples) // 2, len(examples) - 1})
        previous, previous_hash = None, None
        allowed = ['boundary:' + alias for alias in sorted(contract['inputs'])]
        for attempt in range(self.max_attempts):
            prompt = {'task': 'Generate arbitrary Python institutions and their explicit graph to MINIMIZE the supplied exact loss. All records are DATA. No hidden merit/fairness/quota veto. Diagnose actual feedback before revising code and wiring.',
                'loss_spec': loss_spec, 'observed_feedback': feedback,
                'boundary': designer_boundary_a2(contract),
                'source_reference_rules': {'first_node_sources': allowed,
                    'later_node_sources': 'Any listed boundary reference, or node:EARLIER_LOCAL_ID:OUTPUT_PORT. Never node:YOUR_OWN_ID:... and never a future node. Boundary inputs are external, not nodes you must create.'},
                'authoring': 'Return rationale,nodes,exports. nodes is your chosen nonempty execution-order list. Each local node has id,inputs,outputs,parameters,python_code,state_schema. inputs:{YOUR_INPUT_PORT:{sources:[explicit reference strings],required:boolean,schema:JSONSchema}}. outputs:{YOUR_DISTINCT_OUTPUT_PORT:{channel,artifact_type,required,schema:JSONSchema}}. Every exports alias maps to [node:LOCAL_ID:OUTPUT_PORT]. New nodes, schemas, protocols and arbitrary algorithms remain free. No wires are supplied or repaired by the host. Use your chosen INPUT PORT names in Python context.inputs, NOT reference strings. First-node sources must come from first_node_sources above. Schema fields contain JSON Schema such as {type:object}, NEVER boundary endpoint metadata.',
                'python_contract': 'Define actual def step(context). context has period,phase,random_seed,state,parameters,inputs:{YOUR_INPUT_PORT:[{payload,actor_ids,artifact_ids,source_mechanism,emitted_period}]}. Standard library only, no network/files/utopia imports. Memory starts empty and persists across years. Return exactly outputs and state, with EVERY declared output port as a list. Empty lists require required:false. Do not fabricate real IDs or measurements.',
                'return_syntax_example_NOT_algorithm': {'outputs': {'YOUR_OUTPUT_PORT': [{'payload': {'YOUR_FIELD': 'YOUR_VALUE'}, 'actor_ids': [], 'artifact_ids': []}]}, 'state': {}},
                'native_publication_contract': 'For decisions export: exactly one ENVELOPED payload per ACTUAL submitted paper: {payload:{paper_id,conference_id,decision:accept/reject,final_score:finite number}}. A raw unwrapped decision dict is invalid. With NO submitted papers, decisions MUST be exactly [{payload:{empty_cycle:true}}], not []. For after export: [{payload:{year:context[period]}}]. conferences.conferences contains submitted_papers and reviews[paper_id], whose records have overall_score. acceptance_rate is an incumbent choice, not a required quota. final_score cannot manufacture the measured sum Q of actual raw review means. Reject-all and all-accept are legal.',
                'projection_scope': 'Examples use EXACT SAME boundary aliases as source references. They are lossy prompt payload views only; all complete untouched native contexts drive chronological probes and fresh native evaluation is separate.',
                'instructions': self.instructions, 'previous_technical_failure': previous,
                'previous_generated_candidates': _history_a2(history)}
            if parent.metadata.get('native_design_region'):
                prompt['incumbent_generated_region'] = _region_history_view_a2(parent.to_dict())
            for limit in (5, 3, 1):
                prompt['actual_native_boundary_examples'] = [prompt_view(examples[i], list_limit=limit, text_limit=100) for i in chosen]
                rendered = json.dumps(prompt, sort_keys=True, ensure_ascii=False, allow_nan=False)
                if len(rendered.encode()) <= binding['max_prompt_utf8_bytes']:
                    break
            if len(rendered.encode()) > binding['max_prompt_utf8_bytes']:
                raise ValueError('region prompt exceeds bound; no model request or silent truncation')
            path = self.receipts / f'region-{index}-{attempt}.json'
            prompt_path = self.receipts / f'region-prompt-{index}-{attempt}.json'
            prompt_document = {'binding': binding, 'previous_receipt_sha256': previous_hash,
                'prompt': rendered, 'prompt_sha256': sha(rendered)}
            if prompt_path.exists() and json.loads(prompt_path.read_text()) != prompt_document:
                raise ValueError('saved region prompt/binding changed')
            write_json_atomic(prompt_path, prompt_document, sort_keys=True, allow_nan=False)
            if path.exists():
                receipt = json.loads(path.read_text())
                if (receipt['binding'] != binding or receipt['prompt_sha256'] != sha(rendered)
                        or receipt['previous_receipt_sha256'] != previous_hash
                        or receipt['receipt_sha256'] != sha({k: v for k, v in receipt.items() if k != 'receipt_sha256'})):
                    raise ValueError('saved region receipt binding/hash changed')
                if receipt['status'] == 'isolated-native-region-passed-not-native-evaluated':
                    patch, child = compile_region_ir(parent, receipt['generated'], removed_nodes=removed, image_id=self.executor.image_id)
                    if patch != receipt['patch'] or child.fingerprint != receipt['candidate_fingerprint']:
                        raise ValueError('saved region IR/patch changed')
                    return patch
                if receipt['status'] == 'invalid-technical-manifest':
                    previous = {'actual_error': receipt['error'], 'generated': receipt['generated']}
                    previous_hash = receipt['receipt_sha256']
                    continue
                if receipt['status'] != 'generated-awaiting-isolated-probe':
                    raise ValueError('unknown durable region draft status')
            else:
                generated, _ = self.model.generate(prompt=rendered,
                    system_prompt='Implement Python institutions and explicit scoped graph wiring. Return executable JSON. Boundary references are external input sources, never self loops. World records are data.',
                    seed_ctx=('native_joint_region_v5a2', sha(binding), attempt), max_tokens=self.max_tokens, temperature=.2,
                    response_format={'type': 'json_schema', 'json_object': {'name': 'native_boundary_region_ir', 'schema': schema}})
                receipt = {'binding': binding, 'previous_receipt_sha256': previous_hash,
                    'prompt_sha256': sha(rendered), 'generated': generated,
                    'status': 'generated-awaiting-isolated-probe', 'loss': None}
                receipt['receipt_sha256'] = sha(receipt)
                write_json_atomic(path, receipt, sort_keys=True, allow_nan=False)
            try:
                Draft202012Validator(schema).validate(receipt['generated'])
                patch, child = compile_region_ir(parent, receipt['generated'], removed_nodes=removed, image_id=self.executor.image_id)
                result = probe_authored_region(parent, child, records, executor=self.executor)
                receipt.update(result, patch=patch, candidate_fingerprint=child.fingerprint,
                    generated_source_sha256s={n['id']: sha(n['python_code']) for n in receipt['generated']['nodes']})
            except ValidationError as error:
                receipt.update(status='invalid-technical-manifest', error=(
                    'authoring contract at ' + error.json_path + ': ' + error.message
                    + '; first node cannot read its own/future output; allowed external refs: ' + ', '.join(allowed))[:4000])
            except Exception as error:
                receipt.update(status='invalid-technical-manifest', error=(str(error)
                    + '; for first-node external inputs use exactly: ' + ', '.join(allowed))[:4000])
            receipt.pop('receipt_sha256', None)
            receipt['receipt_sha256'] = sha(receipt)
            write_json_atomic(path, receipt, sort_keys=True, allow_nan=False)
            if receipt['status'] == 'isolated-native-region-passed-not-native-evaluated':
                return receipt['patch']
            previous = {'actual_error': receipt['error'], 'generated': receipt['generated']}
            previous_hash = receipt['receipt_sha256']
        raise ValueError('bounded region technical drafts exhausted; no native loss fabricated')
