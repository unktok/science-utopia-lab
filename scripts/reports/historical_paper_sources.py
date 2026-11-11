"""Read exact old receipt-bound bytes, not the changing working bibliography.

This proves byte reconstruction only. The original old receipts did not attest
a clean build commit. No receipt, PDF or current manuscript is rewritten here.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.reports.paper_rebuild_bundle import relative, read_file

ROOT = Path(__file__).resolve().parents[2]
INDEX = 'paper/historical-source-reconstruction-v1.json'


def expected_sources(receipt):
    result = {receipt.get('entrypoint','paper/submission.tex'):receipt['tex_sha256'],
        receipt['output']:receipt['pdf_sha256'],
        'paper/submission-sources.bib':receipt['additional_bibliography_sha256'],
        **receipt['additional_dependencies'], **receipt.get('analysis_projection_sources',{})}
    if 'strong_control_print_figure_manifest_sha256' in receipt:
        result['paper/figures/native-controls-v2-a1-print/manifest.json'] = receipt['strong_control_print_figure_manifest_sha256']
    if 'original_tex_sha256' in receipt:
        result[receipt['scientific_source_otherwise_identical_to']] = receipt['original_tex_sha256']
    return result


def historical_source(receipt_name, name, *, root=ROOT):
    """Return one explicit, checksum-verified historical blob without execution."""
    root = Path(root).resolve()
    relative(receipt_name); relative(name)
    index = json.loads(read_file(root, INDEX))
    if (index['schema'] != 'scienceutopia.historical-paper-source-reconstruction.v1'
            or index['original_build_commit_attested'] is not False
            or not re.fullmatch('[0-9a-f]{40}',index['reconstruction_commit'])):
        raise ValueError('explicit historical byte-reconstruction binding required')
    if receipt_name not in index['receipts']:
        raise ValueError('unregistered historical paper receipt')
    receipt_bytes = read_file(root, receipt_name)
    if hashlib.sha256(receipt_bytes).hexdigest() != index['receipts'][receipt_name]:
        raise ValueError('original historical receipt bytes changed')
    expected = {**index['extra_files'], **expected_sources(json.loads(receipt_bytes)),
        receipt_name:index['receipts'][receipt_name]}
    if name not in expected:
        raise ValueError('file is not explicitly bound by this historical receipt')
    blob = subprocess.check_output(['git','-C',str(root),'show',
        index['reconstruction_commit']+':'+name])
    if hashlib.sha256(blob).hexdigest() != expected[name]:
        raise ValueError('historical source differs from original receipt: '+name)
    return blob
