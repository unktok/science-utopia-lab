"""Literal transcription and claim boundaries; PDF layout is checked separately."""
import json
from pathlib import Path
import re

from tests.reports.test_current_manuscript_estimands import bodies

ROOT = Path(__file__).resolve().parents[2]
SECTION = 'paper/integrated/native-consumer-source.tex'


def retained():
    return json.loads((ROOT / 'research/results/native-consumer-source-comparison-closed-v1.json').read_text())


def test_every_original_slot_cross_score_and_frozen_selection_is_transcribed():
    record = retained(); text = (ROOT / SECTION).read_text()
    rows = [line for line in text.splitlines() if re.match(r'^[1-8](?:\$\^\\star\$)? & ', line)]
    assert len(rows) == 8
    selected = {s['selected_id'] for s in record['own_only_selection'].values()}
    for original, line in zip(record['slots'], rows):
        fields = line.removesuffix('\\\\').split(' & ')
        assert len(fields) == 8
        assert fields[0] == str(original['slot_index'] + 1) + (
            '$^\\star$' if original['physical_job'] in selected else '')
        assert fields[1:4] == [
            'I' if original['arm'] == 'interface-only' else 'S',
            'U' if original['objective'] == 'content-utility' else 'C', str(original['generation'])]
        if original['status'] != 'complete':
            assert fields[4:] == ['---'] * 4 and original['loss'] is None
        else:
            values = original['cross_scores']
            assert fields[4:] == [f"${values['throughput']:.0f}$", f"${values['content-utility']:.2f}$",
                                   f"${values['resource-aware-content']:.2f}$", '200']
    assert 'not zero or a\nnumeric failure penalty' in text


def test_physical_role_counts_and_tokens_match_complete_cost_journals():
    costs = retained()['physical_costs']; text = (ROOT / SECTION).read_text()
    usage = costs['scientist']['provider_usage']
    scientist = [costs['scientist']['completed_responses'],
                 *[usage[k]['recorded_sum'] for k in ('prompt_tokens', 'completion_tokens', 'cached_prompt_tokens')]]
    assert 'Scientists & ' + ' & '.join(f'{v:,}' for v in scientist) + '\\\\' in text
    for label, role in [('Designer readiness', 'editor-readiness'), ('Designer proposals', 'staged-proposal')]:
        group = costs['auxiliary_groups'][role]; tokens = group['token_measurements']
        values = [group['recorded_POST_attempt'],
                  *[tokens[k]['recorded_sum'] for k in ('native_prompt_eval_count', 'native_eval_count',
                                                        'native_prompt_eval_cached_count')]]
        assert label + ' & ' + ' & '.join(f'{v:,}' for v in values) + '\\\\' in text
    assert 'Content critics & 198 & 94,806 & 29,111 & ---' in text
    assert 'Designer loads & 18 & --- & --- & ---' in text
    assert 'Scientist loads & 11 & --- & --- & ---' in text
    assert 'subsets, not added' in text


def test_prior_tracks_labels_figures_and_current_limits_remain_explicit():
    current = bodies(); body = '\n'.join(current.values()); section = current[SECTION]
    for name in ('paper/integrated/native-terminal-cost.tex', 'paper/integrated/native-topic-system-search.tex',
                 'paper/integrated/native-longitudinal-comparison.tex', SECTION):
        assert name in current
    labels = re.findall(r'\\label\{([^}]+)\}', body)
    assert len(labels) == len(set(labels))
    assert set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}', body)) <= set(labels)
    assert section.count('{') == section.count('}')
    assert 'figures/native-consumer-source-loss-paths-v1.png' in section
    for phrase in ('not a new\nbest-known institution', 'not duration shortening',
                   'no general method ranking', 'not main-track readiness',
                   'No new unused-condition evaluation', 'same frozen\nreader code'):
        assert phrase in section
    assert retained()['literal_consumers_minus_interface_own_best'] == {
        'content-utility': 0.0, 'resource-aware-content': 0.0}
