#!/usr/bin/env python3
"""Read-only active-document link and historical-snapshot checks; stdlib only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'research/results/repository-docs-reset-v1.json'
DOCUMENTS = ('README.md', 'RESEARCH.md', 'CONTRIBUTING.md', 'docs/README.md',
    'docs/repository.md', 'docs/development.md', 'docs/testing.md',
    'docs/research-workflow.md', 'research/INDEX.md', 'research/STATUS.md',
    'research/roadmap.md', 'research/program-map.md')
# Inline code is a separate alternative so a literal `[x](y)` inside it is not
# a link. A Markdown link whose label contains backticks still starts at '['.
INLINE = re.compile(r'''(?P<code>`+[^`\n]*`+)|\[[^\]\n]*\]\((?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))(?:\s+["'][^\n]*?["'])?\)''')


def local_links(text):
    fence = None
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in ('```', '~~~'):
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is not None:
            continue
        for match in INLINE.finditer(line):
            if match.group('code') is None:
                yield line_number, match.group('angle') or match.group('plain')


def check(root, *, documents=DOCUMENTS, manifest=MANIFEST):
    root = Path(root).resolve()
    errors, checked_links = [], 0
    for name in documents:
        source = root / name
        if not source.is_file():
            errors.append(f'{name}: missing active document')
            continue
        for number, href in local_links(source.read_text(encoding='utf-8')):
            parsed = urlsplit(href)
            if parsed.scheme in ('http', 'https', 'mailto', 'data', 'tel'):
                continue
            if parsed.scheme or parsed.netloc or parsed.path.startswith('/'):
                errors.append(f'{name}:{number}: nonportable or unsupported link: {href}')
                continue
            if not parsed.path:  # Anchor validation is deliberately out of scope.
                continue
            target = (source.parent / unquote(parsed.path)).resolve()
            checked_links += 1
            if not target.is_relative_to(root):
                errors.append(f'{name}:{number}: target escapes repository: {href}')
            elif not target.exists():
                errors.append(f'{name}:{number}: missing target: {href}')
    snapshot_count = 0
    if manifest is not None:
        location = root / manifest
        if not location.is_file():
            errors.append(f'{manifest}: missing snapshot manifest')
        else:
            data = json.loads(location.read_text(encoding='utf-8'))
            if data.get('schema') != 'scienceutopia.repository-docs-reset.v1':
                errors.append(f'{manifest}: unsupported manifest schema')
            for row in data.get('snapshots', []):
                path = (root / row['snapshot']).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    errors.append(f'{row["snapshot"]}: missing or escaped snapshot')
                elif hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                    errors.append(f'{row["snapshot"]}: snapshot bytes changed')
                snapshot_count += 1
    return {'status': 'failed' if errors else 'passed', 'documents': len(documents),
        'local_links': checked_links, 'snapshots': snapshot_count, 'errors': errors,
        'network_requests': 0, 'model_calls': 0, 'scientific_worlds': 0,
        'scope': 'Inline Markdown targets outside code fences; not remote URLs, anchors or reference-style links.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result = check(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
