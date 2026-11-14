"""Pure codec checks: not author capacity, inference or a world comparison."""
import json

import pytest

from tests.optimization.test_native_trajectory_projection_v1 import fixture
from utopia.optimization.native_trajectory_projection_v1 import project_checkpoint
from utopia.optimization.native_trajectory_columnar_v1 import encode, decode
from utopia.system.design_patch import clone, digest


def projection(tmp_path):
    state, kw = fixture(tmp_path)
    command = clone(state['native_system']['events'][1])
    state['native_system']['events'].insert(2, {
        'year': 1, 'sequence': 2, 'event_id': 'SCRIPTED-base-plan', 'phase': 1,
        'event_type': 'native.system.research_plan_applied',
        'payload': {'base_plan': {'plan': {'assignments': [command['payload']['assignment']]}}}})
    state['native_system']['events'][-1]['sequence'] = 3
    return project_checkpoint(state, **kw)


def reseal(value):
    value.pop('content_sha256')
    value['content_sha256'] = digest(value)
    return value


def test_roundtrip_keeps_every_value_metadata_order_and_original_hash(tmp_path):
    view = projection(tmp_path); before = clone(view)
    encoded = encode(view); saved = clone(encoded)
    assert view == before
    assert decode(encoded) == before and encoded == saved
    assert decode(json.loads(json.dumps(encoded, ensure_ascii=False))) == before
    assert encoded['original_projection_content_sha256'] == view['content_sha256']
    assert encoded['columns']['assignment'] == ['actor_id', 'topic', 'duration', 'start_year', 'end_year']
    assert len(encoded['annual'][0]['authors']) == len(view['annual'][0]['authors'])
    assert view['new_model_calls'] == 0 and not view['author_or_measurement_connection_implemented']
    assert len(json.dumps(encoded).encode()) < len(json.dumps(view).encode())


def test_integer_float_boolean_and_signed_zero_are_not_coerced(tmp_path):
    view = projection(tmp_path)
    view['additional_literal_values'] = [1, 1., -0., False, None, '日本語 🔬']
    view = reseal(view)
    restored = decode(encode(view))
    assert json.dumps(restored['additional_literal_values']) == json.dumps(view['additional_literal_values'])
    assert type(restored['annual'][0]['authors'][0]['opening_active']) is bool


@pytest.mark.parametrize('change', ['dropped-row', 'changed-value', 'wrong-width',
    'duplicate-column', 'column-order', 'extra-envelope-field', 'extra-metadata-annual'])
def test_modified_or_noncanonical_tables_are_not_filled_or_silently_accepted(tmp_path, change):
    value = encode(projection(tmp_path))
    if change == 'dropped-row': value['annual'][0]['authors'].pop()
    elif change == 'changed-value': value['annual'][0]['authors'][0][0] = 'WRONG'
    elif change == 'wrong-width': value['annual'][0]['authors'][0].pop()
    elif change == 'duplicate-column': value['columns']['authors'][0] = value['columns']['authors'][1]
    elif change == 'column-order': value['columns']['authors'].reverse()
    elif change == 'extra-envelope-field': value['uninterpreted'] = 1
    else: value['projection_metadata']['annual'] = []
    reseal(value)  # The original projection binding still must agree.
    with pytest.raises((ValueError, TypeError)): decode(value)


def test_changed_projection_without_resealing_is_not_input(tmp_path):
    view = projection(tmp_path); view['annual'].pop()
    with pytest.raises(ValueError, match='content'): encode(view)


def test_nonuniform_row_fields_are_not_dropped_or_imputed(tmp_path):
    view = projection(tmp_path)
    view['annual'][0]['authors'][0]['new-field'] = 'retained-or-fail'
    reseal(view)
    with pytest.raises(ValueError, match='no dropping or filling'): encode(view)


def test_empty_tables_and_repeated_assignments_remain_literal(tmp_path):
    view = projection(tmp_path)
    for year in view['annual']:
        year['authors'] = []
    original = view['annual'][0]['base_native_plan_snapshots'][0]['assignments'][0]
    view['annual'][0]['base_native_plan_snapshots'][0]['assignments'].append(clone(original))
    reseal(view)
    restored = decode(encode(view))
    assert restored == view
    assert len(restored['annual'][0]['base_native_plan_snapshots'][0]['assignments']) == 2


def test_actual_export_boundary_preserves_input_and_rejects_overwrite(tmp_path):
    from types import SimpleNamespace
    from scripts.reports.native_trajectory_columnar_v1 import export
    from utopia.optimization.native_numeric_designer import save, checked
    from utopia.optimization.native_trajectory_projection_v1 import SCHEMA
    from utopia.utils.data_utils import file_sha256
    view = projection(tmp_path)
    evidence = tmp_path / 'evidence'; evidence.mkdir()
    source = evidence / 'projection.json'
    save(source, {'schema': SCHEMA + '.export', 'projection': view})
    original = file_sha256(source)
    args = SimpleNamespace(projection_export=source, evidence_root=evidence,
        output=tmp_path / 'columnar.json')
    result = export(args)
    assert file_sha256(source) == original and result['original_bytes_unchanged']
    assert result == checked(json.loads(args.output.read_text()))
    assert result['exact_roundtrip'] and decode(result['columnar']) == view
    assert result['columnar_json_utf8_bytes'] < result['original_projection_json_utf8_bytes']
    assert not result['model_context_fit_proved'] and not result['allowed_designer_bank_claimed']
    assert result['new_model_calls'] == result['new_code_executions'] == 0
    with pytest.raises(ValueError, match='fresh output'): export(args)
    args.output = evidence / 'forbidden.json'
    with pytest.raises(ValueError, match='outside it'): export(args)
