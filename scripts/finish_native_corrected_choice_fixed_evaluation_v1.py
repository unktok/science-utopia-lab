"""After actual writer AND supervisor exit: paired native cold proof and costs."""
import argparse
from functools import partial
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish
from scripts.finish_native_priority_method_comparison_v1 import wait_supervised
from scripts.run_native_corrected_choice_fixed_evaluation_v1 import SCHEMA, read
from scripts.supervise_native_corrected_choice_fixed_evaluation_v1 import PREFIX

ROOT = Path(__file__).resolve().parents[1]


def check_output(args, reader):
    output = args.output.resolve()
    roots = [reader.resolve(), args.run.resolve(), args.frozen_source.resolve()]
    if hasattr(args, 'analysis'): roots.append(args.analysis.resolve())
    if output.exists() or any(output.is_relative_to(root) for root in roots):
        raise ValueError('fresh external output required before waiting')
    plan = read(args.run.resolve() / 'plan.json')
    if plan['schema'] != SCHEMA + '.plan': raise ValueError('literal corrected fixed evaluation required')
    roots.extend(Path(plan['origin'][k]).resolve() for k in ('run', 'source', 'analysis', 'readouts'))
    if any(child.is_relative_to(root) for root in roots
            for child in (output, (output / 'report-1').resolve(), (output / 'report-2').resolve())):
        raise ValueError('output cannot enter original evidence/source before waiting')


def run(args):
    check_output(args, ROOT)
    return finish(args, plan_schema=SCHEMA + '.plan',
        audit_module='scripts.audit_native_corrected_choice_fixed_evaluation_v1',
        continuation_schema=SCHEMA + '.finish',
        writer_command='scripts.run_native_corrected_choice_fixed_evaluation_v1 run',
        waiting_stage='await-corrected-fixed-writer-and-supervisor',
        writer_wait=partial(wait_supervised, schema_prefix=PREFIX),
        next_steps='Preserve both fixed scopes/explicit origins/all nulls/seedwise cross-losses. '
            'No design/reselection or independent-search/superiority/publication claim follows.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True); run(parser.parse_args())
