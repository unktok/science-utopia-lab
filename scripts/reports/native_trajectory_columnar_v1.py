"""Encode an existing native projection export, without checkpoint/model access."""
import argparse
import json
from pathlib import Path

from utopia.optimization import native_trajectory_columnar_v1 as codec
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_trajectory_projection_v1 import SCHEMA as PROJECTION_SCHEMA
from utopia.utils.data_utils import file_sha256


def export(args):
    root = args.evidence_root.resolve(); source = args.projection_export.resolve()
    output = args.output.resolve()
    if not source.is_relative_to(root) or output.is_relative_to(root) or output.exists():
        raise ValueError('input inside explicit evidence root and fresh output outside it required')
    files = [source, Path(__file__).resolve(), Path(codec.__file__).resolve()]
    before = {str(p): file_sha256(p) for p in files}
    original = checked(json.loads(source.read_text()))
    if original['schema'] != PROJECTION_SCHEMA + '.export':
        raise ValueError('literal native projection export required')
    encoded = codec.encode(original['projection'])
    restored = codec.decode(encoded)
    if restored != original['projection']:
        raise ValueError('columnar roundtrip differs')
    if before != {str(p): file_sha256(p) for p in files}:
        raise ValueError('projection export or codec source changed')
    def size(value):
        return len(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode())
    return save(output, {'schema': codec.SCHEMA + '.export', 'columnar': encoded,
        'source_projection_export_content_sha256': original['content_sha256'],
        'input_and_component_file_sha256': before, 'original_bytes_unchanged': True,
        'exact_roundtrip': True, 'original_projection_json_utf8_bytes': size(original['projection']),
        'columnar_json_utf8_bytes': size(encoded),
        'model_context_fit_proved': False, 'author_or_measurement_connection_implemented': False,
        'full_physical_source_audit_claimed': False, 'allowed_designer_bank_claimed': False,
        'new_model_calls': 0, 'new_code_executions': 0, 'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('projection-export', 'evidence-root', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    print(export(parser.parse_args())['content_sha256'])


if __name__ == '__main__':
    main()
