"""Read initial native direction support; no optimum or attained gain claim.

Duration-only arithmetic separates catalog-assignment authority from the
original non-strict researcher's expertise-plus-related-topic parser support.
No model, scientific world, mechanism, ranking or new selection is executed.
"""
import argparse
import ast
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-direction-support.v1'
DIRECTIONS = 'utopia/agents/research_direction.py'
ROOT = Path(__file__).resolve().parents[2]


def literal_catalog(body):
    """Parse only literal constructor fields, never import/evaluate the source."""
    tree = ast.parse(body)
    values = [n.value for n in tree.body if isinstance(n, ast.Assign) and
        any(isinstance(t, ast.Name) and t.id == 'AVAILABLE_DIRECTIONS' for t in n.targets)]
    if len(values) != 1 or not isinstance(values[0], ast.List):
        raise ValueError('one literal original direction catalog required')
    rows = []
    for node in values[0].elts:
        if (not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name)
                or node.func.id != 'ResearchDirection' or node.args
                or any(k.arg is None for k in node.keywords)
                or len({k.arg for k in node.keywords}) != len(node.keywords)):
            raise ValueError('literal named direction constructors only; no source execution')
        rows.append({k.arg: ast.literal_eval(k.value) for k in node.keywords})
    return rows


def support(snapshot, catalog, *, years, papers_per_project):
    if (type(years) is not int or years < 1 or type(papers_per_project) is not int or papers_per_project < 1
            or type(snapshot['year']) is not int or snapshot['year'] != 0 or snapshot['paper_tracker']['papers']):
        raise ValueError('positive fixed horizon/output cap and empty initial year0 required')
    if catalog['schema'] != 'scienceutopia.native-direction-catalog.v1' or sha(catalog['directions']) != catalog['directions_sha256']:
        raise ValueError('exact original catalog checksum required')
    directions = catalog['directions']
    if any(not isinstance(d.get('topic'), str) or not d['topic'] for d in directions):
        raise ValueError('literal nonempty catalog topic strings required')
    topics = {d['topic']: d for d in directions}
    if len(topics) != len(directions) or any(type(d['years']) is not int or d['years'] < 1
            or not isinstance(d['related_topics'], list) or any(not isinstance(t, str) for t in d['related_topics'])
            for d in directions):
        raise ValueError('unique catalog topics and positive literal durations/related lists required')
    rows = []
    agents = snapshot['ecosystem_data']['agents']
    if len({a['id'] for a in agents}) != len(agents):
        raise ValueError('unique original actor identities required')
    for a in sorted(agents, key=lambda v: v['id']):
        if a['can_author'] is not True: continue
        core = a['expertise']
        if (a['is_active'] is not True or type(a['project_start_year']) is not int
                or type(a['project_end_year']) is not int or a['project_start_year'] != 0 or a['project_end_year'] != 0
                or not isinstance(core, list) or not core
                or any(not isinstance(t, str) or t not in topics for t in core) or len(set(core)) != len(core)):
            raise ValueError('existing initially active idle authors with literal catalog expertise required')
        related = set().union(*(set(topics[t]['related_topics']) for t in core))
        allowed = set(core) | related
        row = {'actor_id': a['id'], 'expertise': sorted(core),
            'unresolved_legacy_allowed_topics': sorted(allowed - topics.keys())}
        for label, chosen in (('catalog_assignment', set(core)), ('legacy_native_parser', allowed & topics.keys())):
            minimum = min(topics[t]['years'] for t in chosen)
            row[label] = {'topics': sorted(chosen), 'minimum_project_years': minimum,
                'shortest_topics': sorted(t for t in chosen if topics[t]['years'] == minimum),
                'duration_only_output_envelope': papers_per_project * (years // minimum)}
        rows.append(row)
    if not rows: raise ValueError('nonempty original author population required')
    return {'schema': SCHEMA, 'initial_authors': rows, 'horizon_years': years,
        'papers_per_project': papers_per_project, 'duration_only_output_envelopes': {
            label: sum(r[label]['duration_only_output_envelope'] for r in rows)
            for label in ('catalog_assignment', 'legacy_native_parser')},
        'automatically_checked': ['empty year0 paper archive', 'all original authors active/idle at start',
            'unique expertise/catalog identities', 'exact positive duration/output-cap arithmetic'],
        'conditional_not_global_optimality_proof': True,
        'additional_assumptions_not_automatically_proved': ['no new native authors or future expertise mutation',
            'serial noninterrupted projects from the stated topic support',
            'declared cap per completed lead project', 'at most one accepted decision per actual produced paper'],
        'scope': 'Duration-only initial-support relaxation, ignoring funding, attrition, LLM choices, '
            'retrieval/collaboration and content opinions. Legacy parser allows core plus direct related topics; '
            'unresolved catalog strings remain explicit and are not repaired. A larger envelope is neither '
            'attainable performance, an observed intervention effect nor a proved whole-domain optimum.',
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_code_executions': 0,
        'loss_or_selection_changed': False, 'publication_ready': False}


def export(args):
    if (args.output.exists() or args.output.resolve().is_relative_to(args.plan.resolve().parent)
            or args.output.resolve().is_relative_to(args.source.resolve())):
        raise ValueError('fresh support output outside original run/frozen source required')
    plan_body = args.plan.read_bytes(); p = checked(json.loads(plan_body)); source = args.source.resolve()
    git = lambda *a: subprocess.check_output(['git', '-C', str(ROOT), *a], text=True).strip()
    if git('status', '--porcelain'):
        raise ValueError('clean committed analysis source required')
    analysis_source = git('rev-parse', 'HEAD')
    if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != p['source_commit']:
        raise ValueError('exact original frozen source required')
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip():
        raise ValueError('original frozen source must remain clean')
    body = subprocess.check_output(['git', '-C', str(source), 'show', p['source_commit']+':'+DIRECTIONS])
    if (source/DIRECTIONS).read_bytes() != body or literal_catalog(body) != p['catalog']['directions']:
        raise ValueError('literal catalog differs from original source or plan')
    paths = [args.plan, args.checkpoint, Path(__file__), source/DIRECTIONS,
        source/'utopia/system/native_catalog_planning.py', source/'utopia/optimization/native_workflow_domain_v4.py',
        source/'utopia/agents/researcher_agents.py', source/'utopia/system/native_kernel.py']
    before = {str(f.resolve()): file_sha256(f) for f in paths}
    import hashlib
    if before[str(args.plan.resolve())] != hashlib.sha256(plan_body).hexdigest():
        raise ValueError('plan changed between read and input binding')
    from utopia.runtime.checkpointing import read_portable_checkpoint
    state = read_portable_checkpoint(args.checkpoint)
    if state['native_system']['spec'] != p['reference_systems']['R7-original']:
        raise ValueError('checkpoint is not the exact declared original R7 policy')
    report = support(state, p['catalog'], years=p['world']['years'],
        papers_per_project=p['world']['world_conditions']['papers_per_project'])
    if (before != {str(f.resolve()): file_sha256(f) for f in paths}
            or git('rev-parse', 'HEAD') != analysis_source or git('status', '--porcelain')
            or subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != p['source_commit']
            or subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip()):
        raise ValueError('original support inputs changed during read')
    return save(args.output, {'schema': SCHEMA+'.export', 'analysis': report,
        'analysis_source_commit': analysis_source,
        'scientific_source_commit': p['source_commit'], 'plan_content_sha256': p['content_sha256'],
        'input_file_sha256': before, 'original_bound_inputs_unchanged': True,
        'native_execution_or_whole_study_audit_claimed': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('plan', 'checkpoint', 'source', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    r = export(parser.parse_args())
    print(json.dumps(r['analysis']['duration_only_output_envelopes']))


if __name__ == '__main__': main()
