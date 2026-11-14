"""Current reviewed manuscript subset, not scientific or clean-machine evidence."""
import json

import pytest

from scripts.reports import paper_rebuild_bundle as bundle
from utopia.optimization.native_numeric_designer import checked

POLICY = 'research/publication/paper-rebuild-allowlist-integrated-staged-construction-v1.json'


def test_staged_paper_subset_keeps_exact_reviewed_inputs_and_only_new_pdf(tmp_path):
    policy = json.loads((bundle.ROOT / POLICY).read_text())
    receipt = checked(json.loads((bundle.ROOT / policy['receipt']).read_text()))
    value = bundle.stage(bundle.ROOT, policy, tmp_path / 'subset', source_commit='SCRIPTED-staging-source')
    assert len(value['files']) == 68 and len(value['literal_tex_dependencies']) == 65
    assert (receipt['pages'], receipt['figures'], receipt['tables'], receipt['cited_references']) == (82, 42, 36, 27)
    assert receipt['output'] in value['files']
    assert 'output/pdf/science-utopia-lab-integrated-open-institutions-working-paper.pdf' not in value['files']
    assert value['original_build_source_commit'] == receipt['source_commit']
    assert receipt['scientific_scope']['new_scientific_model_calls'] == 0
    assert not receipt['scientific_scope']['real_staged_campaign_started_at_manuscript_snapshot']
    assert not receipt['publication_ready'] and not value['published_or_uploaded']


@pytest.mark.parametrize('changed', ['paper/integrated/discussion.tex',
    'paper/submission-sources.bib', 'paper/integrated/native-workflow-feedback.tex'])
def test_changed_new_inputs_cannot_inherit_the_reviewed_receipt(tmp_path, monkeypatch, changed):
    policy = json.loads((bundle.ROOT / POLICY).read_text())
    read = bundle.read_file
    def altered(root, name):
        body = read(root, name)
        return body + b'\nSCRIPTED changed input' if name == changed else body
    monkeypatch.setattr(bundle, 'read_file', altered)
    with pytest.raises(ValueError, match='changed from reviewed receipt'):
        bundle.stage(bundle.ROOT, policy, tmp_path / 'subset', source_commit='SCRIPTED')
    assert not (tmp_path / 'subset').exists()
