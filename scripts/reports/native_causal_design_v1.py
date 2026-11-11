"""Export literal phase/order evidence without models, source execution or loss inference."""
import argparse
import json
from pathlib import Path

from utopia.optimization.native_causal_design import describe
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, file_sha256, write_json_atomic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.system.resolve():
        raise ValueError('fresh independent output required')
    before = file_sha256(args.system)
    result = {'schema':'scienceutopia.native-causal-design-export.v1',
        'input_file_sha256':before, 'causal_design':describe(decode_json(args.system.read_text(), strict=True, finite_floats=True)),
        'original_source_audit':False, 'new_model_calls':0, 'new_code_executions':0}
    if file_sha256(args.system) != before:
        raise ValueError('input changed during read-only projection')
    result['content_sha256'] = digest(result)
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({'output':str(args.output), 'content_sha256':result['content_sha256'],
        'status':result['causal_design']['status'], 'new_model_calls':0}))


if __name__ == '__main__':
    main()
