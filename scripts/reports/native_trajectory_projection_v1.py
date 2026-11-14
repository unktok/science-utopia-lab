"""Export one fixed-field completed native checkpoint; no author or inference."""
import argparse
import json
from pathlib import Path

from utopia.optimization import native_trajectory_projection_v1 as projection
from utopia.optimization.native_numeric_designer import save
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.utils.data_utils import file_sha256


def export(args):
    root = args.evidence_root.resolve(); checkpoint = args.checkpoint.resolve(); out = args.output.resolve()
    if (not checkpoint.is_relative_to(root) or out.is_relative_to(root)
            or checkpoint == out or out.exists()):
        raise ValueError('checkpoint inside declared evidence root and fresh output outside it required')
    sources = [Path(__file__).resolve(), Path(projection.__file__).resolve()]
    before = {str(p): file_sha256(p) for p in [checkpoint, *sources]}
    view = projection.project_checkpoint(read_portable_checkpoint(checkpoint),
        source_commit=args.source_commit, system_fingerprint=args.system_fingerprint,
        seed=args.seed, years=args.years, checkpoint_file_sha256=before[str(checkpoint)])
    if before != {str(p): file_sha256(p) for p in [checkpoint, *sources]}:
        raise ValueError('checkpoint or reader source changed during projection')
    return save(out, {'schema': projection.SCHEMA + '.export', 'projection': view,
        'input_and_component_file_sha256': before, 'original_bytes_unchanged': True,
        'projection_default_json_utf8_bytes': len(json.dumps(view,
            ensure_ascii=False, sort_keys=True).encode()),
        'full_physical_source_audit_claimed': False, 'model_context_fit_proved': False,
        'new_model_calls': 0, 'new_code_executions': 0, 'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('checkpoint', 'evidence-root', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('source-commit', 'system-fingerprint'):
        parser.add_argument('--' + name, required=True)
    for name in ('seed', 'years'):
        parser.add_argument('--' + name, type=int, required=True)
    result = export(parser.parse_args())
    print(result['content_sha256'])


if __name__ == '__main__':
    main()
