"""Source/citation scope checks, not PDF layout or new scientific evidence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_both_bibliography_inputs_are_considered_without_duplicate_amd_llm():
    entry = (ROOT/'paper/integrated.tex').read_text()
    assert r'\bibliography{references,submission-sources}' in entry
    bodies = [(ROOT/'paper'/name).read_text() for name in ('references.bib','submission-sources.bib')]
    assert sum(body.count('{liu2025mechanism,') for body in bodies)==1
    assert sum(body.count('{narayanaswami2022programmatic,') for body in bodies)==1
    related = (ROOT/'paper/integrated/discussion.tex').read_text()
    assert r'\citep{liu2025mechanism}' in related
    assert r'\citep{narayanaswami2022programmatic}' in related
    assert 'neither representing institutions as programs' in related


def test_new_staged_paragraph_is_software_scope_not_a_repaired_real_experiment():
    body = (ROOT/'paper/integrated/native-workflow-feedback.tex').read_text()
    assert 'ten SCRIPTED native worlds and 48 real' in body
    assert 'zero actual model calls' in body
    assert '20 uniquely attributed historical R7' in body
    assert 'At this software-proof snapshot' in body
    assert 'had not passed the shared-resource gate' in body
    assert 'No model-authored repair' in body
    assert '16 designer calls and 64 component probes' in body


def test_actual_staged_results_remain_distinct_from_software_and_unused_scores():
    entry = (ROOT/'paper/integrated.tex').read_text()
    body = (ROOT/'paper/integrated/native-staged-construction.tex').read_text()
    assert r'\input{integrated/native-staged-construction}' in entry
    assert 'all six proposals: five' in entry
    assert 'All six proposals and eight native worlds complete' in body
    assert 'for 84 total' in body and 'The 64 probe returns' in body
    assert 'No new mechanism or connection is' in body
    assert 'worsens by $4/3$' in body
    assert '937 complete' in body and '1,117,688 prompt and 98,457 completion' in body
    assert 'not independent optimizer replications' in body
    assert 'normally closes all three worlds' in body
    assert 'not proof that a target was absent' in body


def test_staged_unused_results_and_direction_support_limits_are_in_the_body():
    import hashlib
    import json
    from utopia.optimization.native_numeric_designer import checked
    r = checked(json.loads((ROOT/'research/results/native-open-staged-fixed-closed-v1.json').read_text()))
    figure = ROOT/'paper/figures/native-staged-fixed-v1/report.json'
    assert hashlib.sha256(figure.read_bytes()).hexdigest() == r['readouts']['report']['report_file_sha256']
    body = (ROOT/'paper/integrated/native-staged-construction.tex').read_text()
    for literal in ('498 completed responses', '757,983 prompt and 44,296 completion',
                    '132 physical calls', '3,381.233 seconds', 'same ordered 161 full scientist',
                    'corresponding relaxation 36', 'not an', 'global optimum'):
        assert literal in body
    assert 'figures/native-staged-fixed-v1/fixed-policy-seed-scores.png' in body


def test_actual_staged_figure_is_the_original_paired_export_not_a_new_simulation():
    import hashlib
    import json
    from utopia.optimization.native_numeric_designer import checked
    r = checked(json.loads((ROOT/'research/results/native-open-staged-institution-closed-v1.json').read_text()))
    directory = ROOT/'paper/figures/native-staged-construction-v1'
    report = checked(json.loads((directory/'report.json').read_text()))
    assert hashlib.sha256((directory/'report.json').read_bytes()).hexdigest() == r['readouts']['report']['report_file_sha256']
    assert report['plan_sha256'] == r['plan_sha256']
    assert [s['cross_scores'] for s in report['slots']] == [s['cross_scores'] for s in r['slots']]
    body = (ROOT/'paper/integrated/native-staged-construction.tex').read_text()
    assert 'figures/native-staged-construction-v1/objective-loss-paths.png' in body
    assert 'one development history without independent error bars' in body


def test_behavioral_redundancy_precedent_is_cited_without_a_priority_or_cause_claim():
    sources = [(ROOT/'paper'/name).read_text() for name in ('references.bib', 'submission-sources.bib')]
    assert sum(body.count('{el2025inefficiencies,') for body in sources) == 1
    body = (ROOT/'paper/integrated/discussion.tex').read_text()
    assert r'\citet{el2025inefficiencies}' in body
    assert 'not a priority claim' in body
    assert 'do not establish the cause of our local stagnation' in body


def test_reference_absence_correction_is_explicit_and_old_receipt_preserved():
    note = (ROOT/'research/publication/novelty-addendum-programmatic-institutions-v1.md').read_text()
    assert 'AMD-LLM already appears' in note and 'earlier statement' in note
    assert 'both `.bib` files' in note
    assert (ROOT/'paper/integrated-open-institutions-build-v1.json').is_file()
