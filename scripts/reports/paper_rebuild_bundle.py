"""Stage an explicit byte-preserving working-paper rebuild subset, never publish.

No model, TeX or subprocess code in the paper is executed by staging. This is
not a general TeX dependency parser, rights/secret clearance or anonymous bundle.
"""
import argparse
import hashlib
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.paper-rebuild-bundle.v1'
README = '''# Local working-paper rebuild subset

This is a byte-preserving, explicitly allowlisted working draft, NOT an anonymous
submission or release-cleared package. No upload/publication is authorized.
The supplied PDF is the original reviewed working draft. A rebuild may differ
in creation metadata or TeX cache/tool state; inspect the rebuilt pages.

With an already populated Tectonic cache, from paper/:

    tectonic --only-cached --untrusted --keep-logs --keep-intermediates \\
      --outdir ../tmp/pdfs/rebuild submission.tex

Create tmp/pdfs/rebuild first. No data, weights, raw replies, operator settings,
Git history, game assets or numerical-analysis runtime are bundled. The build
receipt refers to further evidence that is intentionally NOT included. Rebuilding
this PDF does not rerun or independently verify numerical results. This local
check does not establish a clean-machine build without dependencies/cache.

Preserve LICENSE and the template's upstream notices. Source attribution:
https://github.com/Ahren09/ScienceUtopia . The existing license's copyright
notice is retained, not asserted to identify this project's human authors.
Third-party data/model rights and target-cycle format/anonymity require separate
review. Do not infer blanket redistribution permission or conference readiness.
'''


def sha(body):
    return hashlib.sha256(body).hexdigest()


def relative(name):
    if not isinstance(name, str):
        raise ValueError('explicit safe repository-relative path required')
    path = PurePosixPath(name)
    if (str(path) != name or path.is_absolute()
            or any(p in ('', '.', '..') or p.startswith('.') for p in path.parts)
            or '\\' in name or not path.parts):
        raise ValueError('explicit safe repository-relative path required')
    return name


def read_file(root, name):
    relative(name); path = root / name
    if (not path.is_file() or not path.resolve().is_relative_to(root)
            or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent)):
        raise ValueError('missing, linked or outside-root allowlisted file: ' + name)
    return path.read_bytes()


def literal_dependencies(bodies, entrypoint, *, repository_parent_inputs=False):
    """Verify this manuscript's literal inputs/figures/bibs/local style, not all TeX."""
    paper = PurePosixPath(entrypoint).parent; pending = [entrypoint]; found = set()
    while pending:
        name = pending.pop()
        if name in found: continue
        if name not in bodies: raise ValueError('missing allowlisted TeX dependency: ' + name)
        found.add(name); text = re.sub(r'(?<!\\)%[^\n]*', '', bodies[name].decode())
        for command, value in re.findall(r'\\(input|include|includegraphics|bibliography|usepackage)(?:\[[^\]]*\])?\{([^}]+)\}', text):
            if any(c in value for c in ('\\', '#', '$')):
                raise ValueError('macro dependency requires explicit parser review')
            for item in value.split(','):
                item = item.strip()
                suffix = {'input': '.tex', 'include': '.tex', 'bibliography': '.bib', 'usepackage': '.sty'}.get(command)
                target = str(paper / (item + suffix if suffix and not item.endswith(suffix) else item))
                if repository_parent_inputs:
                    target = posixpath.normpath(target)
                relative(target)
                if command == 'usepackage' and target not in bodies: continue  # Cached external package.
                if target not in bodies: raise ValueError('missing allowlisted TeX dependency: ' + target)
                if command in ('input', 'include'): pending.append(target)
                else: found.add(target)
    return sorted(found)


def integrated_expected(root, receipt, entrypoint):
    """Reconstruct the exact source/figure/support manifests of an integrated build.

    No historical code or TeX is executed. Evidence/raw files are not silently
    included; the literal dependency list and explicit policy still select files.
    """
    from utopia.optimization.native_numeric_designer import checked
    checked(receipt)
    source = receipt['source_commit']
    if (not isinstance(source, str) or not re.fullmatch('[0-9a-f]{40}', source)
            or receipt['entrypoint'] != entrypoint):
        raise ValueError('exact integrated build source and entrypoint required')
    expected = {receipt['output']: receipt['pdf_sha256']}
    for group in ('source_files', 'figure_files', 'support_files'):
        names = receipt[group]['files']
        if not isinstance(names, list) or names != sorted(set(names)):
            raise ValueError('exact ordered unique integrated manifest required')
        hashes = {relative(name): sha(subprocess.check_output(
            ['git', '-C', str(root), 'show', source + ':' + relative(name)])) for name in names}
        manifest = json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()
        if sha(manifest) != receipt[group]['manifest_sha256']:
            raise ValueError('integrated build source manifest differs: ' + group)
        for name, value in hashes.items():
            if name in expected and expected[name] != value:
                raise ValueError('conflicting integrated source manifest')
            expected[name] = value
    if entrypoint not in expected: raise ValueError('integrated entrypoint absent from original source manifest')
    return expected


def priority_expected(root, receipt, entrypoint):
    """Bind the reviewed111-page receipt's explicit hashes to historical blobs.

    This receipt has a different layout from earlier integrated receipts. Do
    not mutate/reseal it or pretend that later manuscript edits were reviewed.
    Only its literal repository-parent TeX input is normalized to a safe path.
    """
    from utopia.optimization.native_numeric_designer import checked
    checked(receipt)
    source = receipt['source_commit']
    if (not isinstance(source, str) or not re.fullmatch('[0-9a-f]{40}', source)
            or receipt['entrypoint'] != entrypoint or receipt['pages'] != 111
            or receipt['visual_review']['all111_layouts_reviewed'] is not True):
        raise ValueError('exact reviewed111-page source and entrypoint required')
    expected = {relative(receipt['pdf']): receipt['pdf_sha256']}
    for group in ('source_file_sha256', 'figure_file_sha256'):
        hashes = receipt[group]
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError('explicit original source/figure hashes required')
        for literal_name, value in hashes.items():
            name = relative(posixpath.normpath(literal_name))
            if (not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)
                    or name in expected):
                raise ValueError('unique safe original hash binding required')
            original = subprocess.check_output(['git', '-C', str(root), 'show', source + ':' + name])
            if sha(original) != value:
                raise ValueError('original priority source hash differs: ' + name)
            expected[name] = value
    if entrypoint not in expected:
        raise ValueError('priority entrypoint absent from original source hashes')
    return expected


def stage(root, policy, output, *, source_commit):
    root = Path(root).resolve(); output = Path(output)
    if (policy.get('schema') != 'scienceutopia.paper-rebuild-allowlist.v1'
            or policy.get('status') != 'local-working-draft-not-anonymous-not-release-cleared'):
        raise ValueError('explicit working-draft policy required; this tool cannot clear release/anonymity')
    names = policy['files']
    if not isinstance(names, list) or names != sorted(set(names)):
        raise ValueError('sorted unique explicit allowlist required')
    if (output.exists() or output.is_symlink() or root.is_relative_to(output.resolve())):
        raise ValueError('fresh destination required; never overwrite source or evidence')
    # No globbing or recursive source directory copy. Read once and compare later.
    bodies = {relative(name): read_file(root, name) for name in names}
    receipt = json.loads(bodies[policy['receipt']])
    priority = receipt.get('schema') == 'scienceutopia.integrated-native-priority-method-paper.v1'
    integrated = priority or receipt.get('schema') in ('scienceutopia.integrated-capacity-authority-build.v1',
                                         'scienceutopia.integrated-catalog-planning-build.v1',
                                         'scienceutopia.integrated-workflow-controls-manuscript.v1',
                                         'scienceutopia.integrated-workflow-feedback-manuscript.v1',
                                         'scienceutopia.integrated-open-institutions-manuscript.v1',
                                         'scienceutopia.integrated-staged-construction-manuscript.v1',
                                         'scienceutopia.integrated-staged-actual-manuscript.v1',
                                         'scienceutopia.integrated-longitudinal-manuscript.v1',
                                         'scienceutopia.integrated-choice-resource-manuscript.v1',
                                         'scienceutopia.integrated-topic-systems-manuscript.v1',
                                         'scienceutopia.integrated-terminal-cost-manuscript.v1',
                                         'scienceutopia.integrated-consumer-source-manuscript.v1')
    if receipt.get('schema') not in ('scienceutopia.working-paper-build.v2',
                                     'scienceutopia.working-paper-build.v3') and not integrated:
        raise ValueError('bound working-paper build receipt required')
    if (receipt.get('schema') == 'scienceutopia.working-paper-build.v3'
            and receipt.get('entrypoint') != policy['entrypoint']):
        raise ValueError('V3 receipt entrypoint differs from explicit policy')
    if priority:
        expected = priority_expected(root, receipt, policy['entrypoint'])
    elif integrated:
        expected = integrated_expected(root, receipt, policy['entrypoint'])
    else:
        expected = {receipt['output']: receipt['pdf_sha256'], policy['entrypoint']: receipt['tex_sha256'],
            'paper/submission-sources.bib': receipt['additional_bibliography_sha256'],
            **receipt['additional_dependencies']}
    for name, body in bodies.items():
        if name not in ('LICENSE', policy['receipt']) and expected.get(name) != sha(body):
            raise ValueError('allowlisted file is unbound or changed from reviewed receipt: ' + name)
    artifact = receipt['pdf'] if priority else receipt['output']
    if not {'LICENSE', artifact, policy['receipt'], 'paper/neurips_2025.sty'} <= set(names):
        raise ValueError('license, template, reviewed PDF and receipt must be retained')
    dependencies = literal_dependencies(bodies, policy['entrypoint'], repository_parent_inputs=integrated)
    findings = []
    for name, body in bodies.items():
        try: text = body.decode('utf-8')
        except UnicodeDecodeError: continue
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r'/Users/|/home/|[A-Za-z]:\\Users\\', line):
                findings.append({'file': name, 'line': number, 'kind': 'possible-home-path'})
    manifest = {'schema': SCHEMA, 'status': policy['status'], 'scope': policy['scope'],
        'source_commit': source_commit, 'entrypoint': policy['entrypoint'],
        'files': {name: sha(body) for name, body in bodies.items()},
        'literal_tex_dependencies': dependencies, 'limited_text_scan_findings': findings,
        'scan_is_not_secret_or_anonymity_clearance': True,
        'raw_or_model_data_included': False, 'original_bytes_transformed': False,
        'numerical_reproduction_or_clean_machine_build_claimed': False,
        'new_model_calls': 0, 'published_or_uploaded': False}
    if integrated:
        manifest.update(original_build_source_commit=receipt['source_commit'],
                        original_build_receipt_schema=receipt['schema'])
    output.mkdir(parents=True, exist_ok=False)
    for name, body in bodies.items():
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle: handle.write(body)
    instructions = README.replace('submission.tex', PurePosixPath(policy['entrypoint']).name)
    if integrated:
        instructions = instructions.replace('No data, weights, raw replies, operator settings,\n'
            'Git history, game assets or numerical-analysis runtime are bundled.',
            'Only the explicitly listed manuscript inputs and illustrations are included,\n'
            'including the paper\'s UI screenshot. Raw worlds, weights, raw replies, operator\n'
            'settings, Git history, unlisted game assets and numerical-analysis runtime\n'
            'are not bundled.')
    (output / 'REBUILD.md').write_text(instructions)
    if any(read_file(root, name) != body for name, body in bodies.items()):
        raise ValueError('source evidence changed while staging; retain incomplete destination for diagnosis')
    manifest['generated_instructions_sha256'] = sha((output / 'REBUILD.md').read_bytes())
    manifest['content_sha256'] = sha(json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                                               separators=(',', ':'), allow_nan=False).encode())
    (output / 'bundle-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    if {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()} != set(names) | {'REBUILD.md', 'bundle-manifest.json'}:
        raise ValueError('staged inventory differs from explicit allowlist')
    if any((output / name).is_symlink() or (output / name).read_bytes() != body for name, body in bodies.items()):
        raise ValueError('staged bytes differ from exact source subset')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    git = lambda *a: subprocess.check_output(['git', '-C', str(ROOT), *a], text=True).strip()
    source = git('rev-parse', 'HEAD')
    if git('status', '--porcelain'): raise ValueError('commit source/allowlist before staging')
    policy_path = args.policy.resolve()
    if not policy_path.is_relative_to(ROOT): raise ValueError('tracked in-repository policy required')
    policy_name = str(policy_path.relative_to(ROOT)); policy_body = read_file(ROOT, policy_name)
    policy = json.loads(policy_body)
    for name in [policy_name, *policy['files']]:
        blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', source + ':' + relative(name)])
        if read_file(ROOT, name) != blob: raise ValueError('source differs from exact committed bytes: ' + name)
    result = stage(ROOT, policy, args.output, source_commit=source)
    if git('rev-parse', 'HEAD') != source or git('status', '--porcelain'):
        raise ValueError('source changed during staging; no completed-source receipt is claimed')
    print(json.dumps({'status': result['status'], 'files': len(result['files']),
                      'content_sha256': result['content_sha256']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
