"""Known-identifier/surface checks, not a proof of full anonymity or rights."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlparse

import pytest

from scripts.reports.paper_rebuild_bundle import literal_dependencies

ROOT = Path(__file__).resolve().parents[2]


def test_author_redaction_changes_no_scientific_source_or_assets():
    source = (ROOT / 'paper/submission-v2.tex').read_text()
    redacted = (ROOT / 'paper/submission-v2-anonymous.tex').read_text()
    remove = lambda body: re.sub(r'\\author\{[^\n]+\}\n', '', body)
    assert source != redacted and remove(source) == remove(redacted)
    assert 'Anonymous authors' in redacted and 'Not submitted' in redacted
    assert 'Science Utopia Lab' not in redacted
    receipt = json.loads((ROOT / 'paper/submission-anonymous-build-v1.json').read_text())
    assert receipt['author_redaction_only'] and not receipt['full_secret_rights_or_anonymity_clearance']
    assert receipt['visual_qa']['all_pages_inspected']
    for name, digest in {receipt['entrypoint']: receipt['tex_sha256'], receipt['output']: receipt['pdf_sha256'],
                         'paper/submission-v2.tex': receipt['original_tex_sha256'], **receipt['additional_dependencies']}.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_finite_paper_subset_keeps_attribution_and_omits_identified_source_and_numeric_archive():
    policy = json.loads((ROOT / 'research/publication/paper-rebuild-allowlist-anonymous-v1.json').read_text())
    assert len(policy['files']) == 13 and policy['files'] == sorted(set(policy['files']))
    bodies = {name: (ROOT / name).read_bytes() for name in policy['files']}
    assert len(literal_dependencies(bodies, policy['entrypoint'])) == 10
    assert 'LICENSE' in bodies and 'paper/neurips_2025.sty' in bodies
    assert 'paper/submission-v2.tex' not in bodies
    for name, body in bodies.items():
        assert not name.startswith(('outputs/', 'research/', '.git/', 'data/'))
        try:
            text = body.decode().lower()
        except UnicodeDecodeError:
            continue
        assert not any(token in text for token in ('/users/', '/home/', 'shiro', 'unktok', 'science utopia lab')), name
        assert not re.search(r'-----begin [a-z ]*private key-----|ghp_[a-z0-9]{30}|sk-[a-z0-9]{30}', text), name


def test_actual_pdf_surface_has_no_known_identifiers_or_embedded_payloads():
    for tool in ('pdfinfo', 'pdfdetach', 'pdftotext'):
        if not shutil.which(tool):
            pytest.skip('Poppler required for bounded PDF surface inspection')
    path = str(ROOT / 'output/pdf/institution-design-anonymous-draft.pdf')
    call = lambda tool, *args: subprocess.check_output([tool, *args, path], text=True)
    text = subprocess.check_output(['pdftotext', path, '-'], text=True).lower()
    assert 'anonymous authors' in text
    assert not any(token in text for token in ('/users/', '/home/', 'shiro', 'unktok', 'science utopia lab'))
    info = call('pdfinfo')
    assert re.search(r'^Pages:\s+12$', info, re.M)
    assert re.search(r'^Form:\s+none$', info, re.M)
    assert re.search(r'^JavaScript:\s+no$', info, re.M)
    assert not re.search(r'^Author:', info, re.M)
    assert call('pdfinfo', '-meta') == ''
    assert call('pdfdetach', '-list').strip() == '0 embedded files'
    hosts = [urlparse(u).hostname for u in re.findall(r'https?://\S+', call('pdfinfo', '-url'))]
    assert len(hosts) == 17 and set(hosts) == {'arxiv.org', 'proceedings.mlr.press'}
