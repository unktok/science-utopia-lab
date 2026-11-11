"""The original receipts and PDFs stay literal, while their source is versioned."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.reports.historical_paper_sources import historical_source, expected_sources, INDEX

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name',[
    'paper/submission-build-v2.json','paper/submission-build-v3.json',
    'paper/submission-anonymous-build-v1.json'])
def test_every_original_bound_asset_and_current_pdf_match_original_hashes(name):
    receipt = json.loads((ROOT/name).read_text())
    for path, expected in expected_sources(receipt).items():
        assert hashlib.sha256(historical_source(name,path)).hexdigest() == expected
    assert hashlib.sha256((ROOT/receipt['output']).read_bytes()).hexdigest() == receipt['pdf_sha256']
    index = json.loads((ROOT/INDEX).read_text())
    assert not index['original_build_commit_attested']
    assert historical_source(name,name) == (ROOT/name).read_bytes()


@pytest.mark.parametrize("name", (
    "../paper/references.bib", "/etc/passwd", ".git/config", "research/STATUS.md",
))
def test_no_unbound_or_unsafe_blob_is_opened(name):
    with pytest.raises(ValueError):
        historical_source('paper/submission-build-v3.json',name)


def test_unknown_receipt_is_not_an_arbitrary_git_reader():
    with pytest.raises(ValueError,match='unregistered'):
        historical_source('paper/integrated-build-v1.json','paper/references.bib')
