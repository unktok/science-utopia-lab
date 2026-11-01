"""Explicit, policy-free graph edits for externally authored native institutions.

This optional syntax lowers to the existing arbitrary JSON patch API. It never
inventories allowed policies, invents connections, deletes incident edges, or
executes source. Callers own the complete final schedules and type declarations.
"""
from __future__ import annotations

from .design_patch import apply_design_patch, clone, make_patch
from .native_migration import native_execution_nodes


def native_authoring_contract(system):
    """Return exact source/graph data and the flat sandbox ABI, without execution."""
    return {
        'schema': 'scienceutopia.native-structural-authoring-contract.v1',
        'parent_fingerprint': system.fingerprint,
        'system': clone(system.to_dict()),
        'execution_nodes': [node.mechanism_id for node in native_execution_nodes(system)],
        'python_abi': {
            'entrypoint': 'step(context)',
            'input_access': "context['inputs'][PORT]",
            'input_value': {'payload': 'JSON object', 'actor_ids': 'list of actual IDs',
                            'artifact_ids': 'list of actual IDs',
                            'source_mechanism': 'producer ID', 'emitted_period': 'integer'},
            'return': {'outputs': {'DECLARED_PORT': [{'payload': {'YOUR_FIELDS': 'YOUR_VALUES'}}]},
                       'state': {}},
            'notes': [
                'Inputs are flat PORT -> list of envelopes, never indexed by node ID.',
                'Every declared output key is required; optional output lists may be empty.',
                'Payload schemas, transport ports, channels, schedules and wires are separate contracts.',
                'Literal source is sandbox data, not evaluated by this helper.',
            ],
        },
        'mixed_search_binding': {
            'base_patch': 'bound to this parent_fingerprint',
            'factor_operations': 'JSON operations relative to the compiled base_patch result',
            'continuous_paths': 'JSON pointers valid in every compiled factor assignment',
        },
    }


def explicit_graph_patch(parent, *, remove_nodes=(), put_nodes=(), disconnect=(), connect=(),
                         schedules, agent_types=None, artifact_types=None, metadata=None, rationale=''):
    """Compile an explicit atomic node/edge transaction, without semantic repair.

    Nodes and edges are complete canonical SystemSpec dictionaries. Replacing a
    node preserves its position; additions append in caller order. Schedules are
    the COMPLETE final array: deleting a node does not silently delete schedules
    or incident connections. Undeclared disconnections and dangling edges fail.
    The original arbitrary patch API remains available for all other edits.
    """
    before = clone(parent.to_dict())
    removed = list(remove_nodes)
    replacements = clone(list(put_nodes))
    if len(set(removed)) != len(removed):
        raise ValueError('duplicate explicit node removal')
    existing = {node['mechanism_id']: node for node in before['mechanisms']}
    if any(identity not in existing for identity in removed):
        raise ValueError('explicit node removal does not exist')
    ids = [node['mechanism_id'] for node in replacements]
    if len(set(ids)) != len(ids) or set(ids) & set(removed):
        raise ValueError('ambiguous explicit node replacement')
    lookup = {node['mechanism_id']: node for node in replacements}
    nodes = [lookup.pop(node['mechanism_id'], node) for node in before['mechanisms']
             if node['mechanism_id'] not in removed]
    nodes.extend(node for node in replacements if node['mechanism_id'] in lookup)
    edges = before['connections']
    for edge in clone(list(disconnect)):
        if edge not in edges:
            raise ValueError('explicit disconnected edge does not exist or is duplicated')
        edges.remove(edge)
    for edge in clone(list(connect)):
        if edge in edges:
            raise ValueError('explicit connected edge already exists or is duplicated')
        edges.append(edge)
    operations = [
        {'op': 'replace', 'path': '/mechanisms', 'value': nodes},
        {'op': 'replace', 'path': '/connections', 'value': edges},
        {'op': 'replace', 'path': '/schedules', 'value': clone(list(schedules))},
    ]
    for key, value in [('agent_types', agent_types), ('artifact_types', artifact_types)]:
        if value is not None:
            operations.append({'op': 'replace', 'path': '/' + key, 'value': clone(list(value))})
    if metadata is not None:
        operations.append({'op': 'replace', 'path': '/metadata', 'value': clone(metadata)})
    patch = make_patch(parent, operations, rationale=rationale)
    apply_design_patch(parent, patch)
    return patch


def factor_operations(compiled_base, choice_patch):
    """Check an independently authored choice against its true post-base parent.

    Return only operations, as required by NativeFactorizedDesignSearch. A patch
    bound to the pre-base parent is deliberately rejected, never rebased by IDs.
    Cross-factor compatibility is still checked by the full grammar compiler.
    """
    apply_design_patch(compiled_base, choice_patch)
    return clone(choice_patch['operations'])
