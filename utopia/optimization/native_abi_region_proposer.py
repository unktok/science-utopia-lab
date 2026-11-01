"""ABI-only staged authoring amendment; no source repair or algorithm template.

Historical staged prompts/receipts stay reconstructible through the unchanged
parent class. Only the durable binding and source-phase explanatory prompt are
overridden. Exact generated source still reaches the original native probes.
"""
from __future__ import annotations

from utopia.optimization.native_staged_region_proposer import NativeStagedRegionProposer
from utopia.system.design_patch import clone

ABI_SCHEMA = 'scienceutopia.native-region-proposal.staged-abi-v5'


def mechanical_input_access_paths(plan):
    """Literal flat ABI paths, not a supplied institutional implementation."""
    return {node['id']: {port: {
        'envelope_list': "context['inputs'][" + repr(port) + ']',
        'first_payload_if_nonempty': "context['inputs'][" + repr(port) + "][0]['payload']",
        'precondition_for_first_payload': 'Use [0] only after confirming this PORT list is nonempty.'}
        for port in sorted(node['inputs'])} for node in plan['nodes']}


def per_node_execution_input_examples(plan, boundary_examples):
    """Route only actually observed external projections along explicit wires.

    Generated internal outputs have not been executed at source-authoring time.
    They are described by schemas separately, never fabricated as observations
    or silently replaced with empty lists in an executable context snippet.
    """
    declared = {node['id']: node for node in plan['nodes']}
    result = []
    for node in plan['nodes']:
        periods = []
        for example in boundary_examples:
            inputs, evidence, internal = {}, {}, {}
            for port, data in sorted(node['inputs'].items()):
                external_refs = [ref for ref in data['sources'] if ref.startswith('boundary:')]
                internal_refs = [ref for ref in data['sources'] if ref.startswith('node:')]
                if external_refs:
                    values = []
                    for ref in external_refs:
                        alias = ref.split(':', 1)[1]
                        if alias not in example['boundary_inputs']:
                            raise ValueError('ABI prompt references unavailable observed boundary alias ' + ref)
                        values.extend(clone(example['boundary_inputs'][alias]))
                    inputs[port] = values
                    evidence[port] = {'status': 'actual-external-projection' if not internal_refs
                        else 'partial-actual-external-projection-internal-unobserved',
                        'explicit_sources': external_refs}
                if internal_refs:
                    sources = []
                    for ref in internal_refs:
                        _, source_id, source_port = ref.split(':')
                        sources.append({'reference': ref,
                            'payload_schema': clone(declared[source_id]['outputs'][source_port]['schema'])})
                    internal[port] = {'status': 'schema-only-not-an-observation',
                        'receiver_payload_schema': clone(data['schema']), 'source_output_schemas': sources}
                    if not external_refs:
                        evidence[port] = {'status': 'schema-only-not-an-observation', 'explicit_sources': internal_refs}
            periods.append({'period': example['period'],
                'context_snippet': {'period': example['period'], 'inputs': inputs},
                'input_evidence': evidence, 'internal_inputs_schema_only': internal,
                'notice': 'This is a PORT-keyed partial context projection, not a full executed candidate context. Omitted internal ports are unobserved, NOT empty lists.'})
        result.append({'node_id': node['id'], 'period_examples': periods})
    return result


NATIVE_WORLD_PAYLOAD_PATHS = {
    'scope': "Only for actual native-world payloads with schema scienceutopia.native-world-observation.v1; your internal protocols have their own declared schemas.",
    'conferences_container': {'path': "payload['conferences']", 'type': 'dict - NOT the conference list'},
    'conference_list': {'path': "payload['conferences']['conferences']", 'type': 'list of conference dicts'},
    'conference_submissions': {'path': "conf['submitted_papers']", 'type': 'list of actual paper dicts - NOT a dict; no .items()'},
    'conference_reviews': {'path': "conf['reviews']", 'type': 'dict mapping actual paper ID to list of review dicts'},
    'paper_reviews': {'path': "conf['reviews'].get(actual_paper_id, [])", 'type': 'list of review dicts; can be empty'},
    'individual_review': {'path': "review['overall_score']", 'type': 'numeric score field of an individual review DICT, not a property on the review list'},
}


class NativeABIRegionProposer(NativeStagedRegionProposer):
    """Same constructor/controller API, with separately bound ABI explanations."""

    def _draft(self, *, binding, phase, index, attempt, schema, prompt, previous_hash):
        binding = {**binding, 'schema': ABI_SCHEMA}
        if phase == 'source':
            prompt = clone(prompt)
            plan = prompt['chosen_graph_plan']
            prompt['per_node_execution_input_examples'] = per_node_execution_input_examples(
                plan, prompt['actual_native_boundary_examples'])
            prompt['mechanical_input_access_paths'] = mechanical_input_access_paths(plan)
            prompt['native_world_payload_container_paths'] = clone(NATIVE_WORLD_PAYLOAD_PATHS)
            prompt['execution_input_abi_clarification'] = (
                "The response sources object is indexed by NODE ID to select which function to install. "
                "That does NOT add a node dimension to step(context). Inside EACH installed function, "
                "context['inputs'] is directly keyed by YOUR INPUT PORT, and each value is a LIST of envelopes. "
                "Do NOT write context['inputs'][NODE_ID][PORT]. Use the literal per-node access paths below. "
                "Each node receives its own flat port dictionary; no other node's input dictionary is nested there. "
                "Observed external inputs are labelled projections; internal outputs are schema-only until executed. "
                "No institutional algorithm or Python function body is supplied by these ABI examples.")
        return super()._draft(binding=binding, phase=phase, index=index, attempt=attempt,
            schema=schema, prompt=prompt, previous_hash=previous_hash)
