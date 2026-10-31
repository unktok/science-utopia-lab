"""ID-addressed design transactions, compiled to the same auditable patch.

Avoids array-index bookkeeping without restricting institution algorithms.
Raw JSON edits remain an escape hatch for any SystemSpec field.
"""
from .design_patch import apply_design_patch, clone, make_patch, _edit
from .model import SystemSpec

SCHEMA = 'scienceutopia.system-design-intent.v1'


def _put(rows, key, item):
    if not isinstance(item, dict) or key not in item:
        raise ValueError('named design item needs ' + key)
    index = next((i for i, row in enumerate(rows) if row[key] == item[key]), None)
    if index is None: rows.append(clone(item))
    else: rows[index] = clone(item)


def compile_design_intent(parent, intent):
    if not isinstance(intent, dict) or set(intent) != {'schema', 'parent_fingerprint', 'changes', 'rationale'} or intent['schema'] != SCHEMA or intent['parent_fingerprint'] != parent.fingerprint:
        raise ValueError('named design intent schema/parent mismatch')
    if not isinstance(intent['changes'], list) or not 1 <= len(intent['changes']) <= 256:
        raise ValueError('bounded nonempty design changes required')
    document = clone(parent.to_dict())
    for change in intent['changes']:
        if not isinstance(change, dict): raise ValueError('design change must be an object')
        op = change.get('op')
        if op == 'put_node' and set(change) == {'op', 'node'}:
            node = change['node']
            # Parse one node to materialize documented defaults, not silently
            # discard misspelled fields. Arbitrary source/parameters survive.
            if set(node) - {'mechanism_id', 'family', 'implementation', 'version', 'inputs', 'outputs', 'parameters'}:
                raise ValueError('unknown node fields')
            for port in [*node.get('inputs', []), *node.get('outputs', [])]:
                if set(port) - {'port_id', 'channel', 'artifact_type', 'required'}: raise ValueError('unknown port fields')
            normalized = SystemSpec.from_dict({'system_id': 'normalize-node', 'version': 1, 'mechanisms': [node]}).to_dict()['mechanisms'][0]
            _put(document['mechanisms'], 'mechanism_id', normalized)
        elif op == 'remove_node' and set(change) == {'op', 'id'}:
            name = change['id']
            if not any(n['mechanism_id'] == name for n in document['mechanisms']): raise ValueError('cannot remove unknown node')
            document['mechanisms'] = [n for n in document['mechanisms'] if n['mechanism_id'] != name]
            document['connections'] = [c for c in document['connections'] if name not in (c['source_mechanism'], c['target_mechanism'])]
            document['schedules'] = [s for s in document['schedules'] if s['mechanism_id'] != name]
        elif op in ('connect', 'disconnect') and set(change) == {'op', 'connection'}:
            from .model import ConnectionSpec, ChannelKind
            edge = dict(change['connection'])
            edge['channel'] = ChannelKind(edge['channel'])
            from dataclasses import asdict
            edge = asdict(ConnectionSpec(**edge)); edge['channel'] = edge['channel'].value
            if op == 'connect':
                if edge not in document['connections']: document['connections'].append(edge)
            elif edge in document['connections']: document['connections'].remove(edge)
            else: raise ValueError('cannot disconnect unknown edge')
        elif op == 'schedule' and set(change) == {'op', 'schedule'}:
            from .model import ScheduleSpec
            from dataclasses import asdict
            schedule = asdict(ScheduleSpec(**change['schedule']))
            document['schedules'] = [s for s in document['schedules'] if (s['mechanism_id'], s['trigger']) != (schedule['mechanism_id'], schedule['trigger'])]
            document['schedules'].append(schedule)
        elif op == 'artifact_type' and set(change) == {'op', 'artifact_type'}:
            from .model import ArtifactTypeSpec
            from dataclasses import asdict
            _put(document['artifact_types'], 'artifact_type_id', asdict(ArtifactTypeSpec(**change['artifact_type'])))
        elif op == 'edit' and set(change) == {'op', 'edit'}:
            _edit(document, change['edit'])
        elif op == 'deliver_to_researchers' and set(change) <= {'op', 'source', 'source_port', 'receiver', 'phase', 'latency'}:
            from .native_kernel import add_context_receiver
            document = add_context_receiver(SystemSpec.from_dict(document),
                **{k: v for k, v in change.items() if k != 'op'}).to_dict()
        else:
            raise ValueError('unsupported named design operation/fields')
    before = parent.to_dict()
    patch = make_patch(parent, [{'op': 'replace', 'path': '/' + key, 'value': value}
        for key, value in document.items() if before[key] != value], rationale=intent['rationale'])
    apply_design_patch(parent, patch)
    return patch
