"""Prospective designer transport contract, independent of backend schema compilation."""
import hashlib
import json

FORMAT = 'json'  # Chosen up front, never an error-triggered fallback.
CONTRACT = 'scienceutopia.designer-json-wire.v16'


def wire_record(payload, schema):
    # Send these exact bytes, not requests' independently serialized mapping.
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {'transport_contract': CONTRACT, 'request_wire_utf8': text,
        'request_wire_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'host_response_schema_sha256': hashlib.sha256(json.dumps(schema,
            ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()}


def post(session, endpoint, payload, schema, record, *, timeout=300):
    record.update(wire_record(payload, schema))
    # Transport settings are source-owned, not candidate/model-controlled. Keep
    # them in the receipt even when a single POST raises without a response.
    record['http_timeout_seconds'] = list(timeout) if isinstance(timeout, tuple) else timeout
    return session.post(endpoint, data=record['request_wire_utf8'].encode(),
        headers={'Content-Type': 'application/json'}, timeout=timeout)
