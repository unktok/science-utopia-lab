"""Lossless, labeled tables for a native projection; no designer connection.

This codec removes repeated field names, not records, literal values or provenance.
It is not checkpoint validation, information-access authorization or token fit.
"""
from utopia.optimization.native_trajectory_projection_v1 import SCHEMA as PROJECTION_SCHEMA
from utopia.system.design_patch import clone, digest

SCHEMA = PROJECTION_SCHEMA + '.columnar'
TABLES = ('authors', 'native_phases_in_recorded_order',
          'applied_project_commands', 'base_native_plan_snapshots')
ASSIGNMENT = ('actor_id', 'topic', 'duration', 'start_year', 'end_year')


def _checked(value, schema):
    if (not isinstance(value, dict) or value.get('schema') != schema
            or value.get('content_sha256') != digest(
                {k: v for k, v in value.items() if k != 'content_sha256'})):
        raise ValueError('sealed trajectory schema/content differs')
    return value


def _columns(rows):
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError('literal table rows required')
    columns = sorted(rows[0]) if rows else []
    if any(sorted(r) != columns for r in rows):
        raise ValueError('table row fields differ; no dropping or filling')
    return columns


def _row(row, columns):
    if not isinstance(row, dict) or sorted(row) != sorted(columns):
        raise ValueError('table row fields differ; no dropping or filling')
    return [clone(row[key]) for key in columns]


def _unrow(row, columns):
    if (not isinstance(columns, list) or any(not isinstance(k, str) for k in columns)
            or len(set(columns)) != len(columns) or not isinstance(row, list)
            or len(row) != len(columns)):
        raise ValueError('literal row width or column names differ')
    return dict(zip(columns, clone(row)))


def encode(projection):
    """Keep every selected record/value; label each column once across years."""
    _checked(projection, PROJECTION_SCHEMA)
    annual = projection['annual']
    if not isinstance(annual, list):
        raise ValueError('literal annual records required')
    columns = {key: _columns([r for year in annual for r in year[key]]) for key in TABLES}
    counts = [year['recorded_event_counts'] for year in annual]
    columns['recorded_event_counts'] = _columns(counts)
    columns['assignment'] = list(ASSIGNMENT)
    encoded_years = []
    for original in annual:
        year = clone(original)
        for key in TABLES:
            rows = clone(original[key])
            for row in rows:
                if key == 'applied_project_commands':
                    row['assignment'] = _row(row['assignment'], columns['assignment'])
                elif key == 'base_native_plan_snapshots':
                    row['assignments'] = [_row(a, columns['assignment']) for a in row['assignments']]
            year[key] = [_row(row, columns[key]) for row in rows]
        year['recorded_event_counts'] = _row(original['recorded_event_counts'],
            columns['recorded_event_counts'])
        encoded_years.append(year)
    value = {'schema': SCHEMA, 'columns': columns, 'annual': encoded_years,
        'projection_metadata': {k: clone(v) for k, v in projection.items()
            if k not in ('annual', 'content_sha256')},
        'original_projection_content_sha256': projection['content_sha256']}
    value['content_sha256'] = digest(value)
    return value


def decode(encoded):
    """Reconstruct and verify the exact original projection, including hashes.

    Equality is data equality, not physical/source validity or permission to
    disclose the projection. Digests are integrity bindings, not signatures.
    """
    _checked(encoded, SCHEMA)
    if set(encoded) != {'schema', 'columns', 'annual', 'projection_metadata',
                         'original_projection_content_sha256', 'content_sha256'}:
        raise ValueError('columnar envelope fields differ')
    columns = encoded['columns']
    if (set(columns) != {*TABLES, 'recorded_event_counts', 'assignment'}
            or columns['assignment'] != list(ASSIGNMENT)
            or not isinstance(encoded['annual'], list)):
        raise ValueError('columnar contract differs')
    result = clone(encoded['projection_metadata'])
    if not isinstance(result, dict) or 'annual' in result or 'content_sha256' in result:
        raise ValueError('projection metadata contains reserved fields')
    years = []
    for encoded_year in encoded['annual']:
        year = clone(encoded_year)
        for key in TABLES:
            rows = [_unrow(row, columns[key]) for row in year[key]]
            for row in rows:
                if key == 'applied_project_commands':
                    row['assignment'] = _unrow(row['assignment'], columns['assignment'])
                elif key == 'base_native_plan_snapshots':
                    row['assignments'] = [_unrow(a, columns['assignment']) for a in row['assignments']]
            year[key] = rows
        year['recorded_event_counts'] = _unrow(year['recorded_event_counts'],
            columns['recorded_event_counts'])
        years.append(year)
    result.update(annual=years, content_sha256=encoded['original_projection_content_sha256'])
    _checked(result, PROJECTION_SCHEMA)
    if encode(result) != encoded:
        raise ValueError('noncanonical columnar representation')
    return result
