"""Model-facing alpha names for opaque audit references; raw evidence is intact.

Only source-defined message metadata is projected. Scientific payloads, actor/
artifact identifiers, timings, unknown fields and all saved records stay literal.
The inverse map is returned for audit/reconstruction, never silently discarded.
"""
import json

from utopia.system.design_patch import clone

SCHEMA = 'scienceutopia.model-provenance-view.v30'
SCOPE = ('Opaque audit references use prompt-local names, not cryptographic digests. '
    'Repeated names denote the same reference within this view. Original identifiers '
    'remain in the event log; scientific payloads are unchanged.')
FIELDS = ('message_id', 'input_event_ids', 'previous_receipt_sha256', 'domain_content_sha256')


def provenance_view(records):
    """Return (reconstructable view, alias->original map), without input mutation."""
    original = clone(records)
    by_original = {}

    def reference(value):
        if value not in by_original:
            by_original[value] = 'audit-ref:' + str(len(by_original))
        return by_original[value]

    viewed = []
    for message in original:
        item = clone(message)
        if isinstance(item, dict):
            for field in FIELDS:
                value = item.get(field)
                if isinstance(value, str) and value:
                    item[field] = reference(value)
                elif field == 'input_event_ids' and isinstance(value, list):
                    item[field] = [reference(part) if isinstance(part, str) and part else part for part in value]
        viewed.append(item)
    inverse = {alias: value for value, alias in by_original.items()}
    # Deliberately exposed audit hashes are scientific data, not hidden labels.
    # Keep payloads literal and show their link to the projected metadata so
    # equality/reference information is not lost at that boundary.
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, item in value.items():
                yield key
                yield from strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from strings(item)
    literal = list(strings([{k: v for k, v in item.items() if k not in FIELDS}
        if isinstance(item, dict) else item for item in original]))
    exposed = {alias: value for alias, value in inverse.items()
        if any(value == text or len(value) >= 24 and value in text for text in literal)}
    return {'schema': SCHEMA, 'scope': SCOPE, 'messages': viewed,
        'explicit_reference_values': exposed}, inverse


def render_provenance_view(records):
    view, inverse = provenance_view(records)
    if not inverse:
        # A context without opaque reference metadata retains its old bytes.
        return '\n'.join(json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False) for item in records)
    return json.dumps(view, ensure_ascii=False, sort_keys=True, allow_nan=False)
