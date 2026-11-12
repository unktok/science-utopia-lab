"""Documentation-only tests; no scientific runtime, network or model import."""
import hashlib
import json
from pathlib import Path

from scripts.check_repository_docs import ROOT, check, local_links


def test_active_repository_documents_and_snapshots():
    result = check(ROOT)
    assert not result['errors'], '\n'.join(result['errors'])
    assert result['snapshots'] == 6


def test_literal_examples_and_external_urls_are_not_local_targets(tmp_path):
    (tmp_path/'readme.md').write_text('''[web](https://example.invalid/no-network)
`[example](missing.py)`
```bash
[not-a-link](missing.py)
```
~~~
[also-not-a-link](missing.py)
~~~
[anchor](#unvalidated)
''')
    assert check(tmp_path, documents=['readme.md'], manifest=None)['errors'] == []


def test_formatted_labels_quoted_titles_spaces_images_and_missing_targets(tmp_path):
    (tmp_path/'actual file.md').write_text('ok')
    (tmp_path/'asset.png').write_bytes(b'fixture-not-an-image')
    (tmp_path/'readme.md').write_text('''[`formatted`](actual%20file.md "title")
[space](<actual file.md>)
![image](asset.png)
[missing](does-not-exist.md)
''')
    result = check(tmp_path, documents=['readme.md'], manifest=None)
    assert result['local_links'] == 4
    assert len(result['errors']) == 1 and 'does-not-exist.md' in result['errors'][0]


def test_path_escape_and_host_absolute_links_are_not_portable(tmp_path):
    (tmp_path/'readme.md').write_text('[escape](../outside.md)\n[host](/Users/person/file.md)\n')
    result = check(tmp_path, documents=['readme.md'], manifest=None)
    assert len(result['errors']) == 2


def test_changed_snapshot_is_detected_without_git_history(tmp_path):
    (tmp_path/'snapshot.md').write_text('original\n')
    manifest = {'schema': 'scienceutopia.repository-docs-reset.v1', 'snapshots': [
        {'snapshot': 'snapshot.md', 'sha256': hashlib.sha256(b'original\n').hexdigest()}]}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    assert check(tmp_path, documents=[], manifest='manifest.json')['status'] == 'passed'
    (tmp_path/'snapshot.md').write_text('rewritten\n')
    assert check(tmp_path, documents=[], manifest='manifest.json')['status'] == 'failed'


def test_missing_active_document_is_a_visible_failure(tmp_path):
    result = check(tmp_path, documents=['missing.md'], manifest=None)
    assert result['errors'] == ['missing.md: missing active document']


def test_inline_parser_reports_real_line_number():
    assert list(local_links('intro\n`[x](not-real)`\n[real](here.md)')) == [(3, 'here.md')]


def test_front_doors_distinguish_reviewed_snapshot_closed_and_live_studies():
    receipt = json.loads((ROOT / 'paper/integrated-advice-build-v1.json').read_text())
    assert receipt  # The artifact binding must exist, not just the prose link.
    for name in ('README.md', 'paper/README.md', 'RESEARCH.md'):
        value = (ROOT / name).read_text()
        assert str(receipt['pages']) in value
        assert 'native-capacity-objective-loop-v1.md' in value or 'T/P' in value
        assert 'research/STATUS.md' in value
    paper = (ROOT / 'paper/README.md').read_text()
    assert 'integrated-advice-build-v1.json' in paper
    assert '18 physical worlds/21 logical cells' in paper
    assert 'now enter this PDF' in paper
    assert 'not a submitted, anonymous or release-cleared paper' in paper
    readme = (ROOT / 'README.md').read_text()
    assert 'integrated41-page' not in readme
    assert 'Its selected-policy evaluation and final integration checks are not yet closed' not in readme
