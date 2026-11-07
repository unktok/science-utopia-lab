"""Exact, read-only source closure for prospective benchmark protocols."""
import ast
import hashlib
from pathlib import Path
import re
import subprocess


def source_proofs(root, source, *, scripts, resources):
    root = Path(root)
    if not isinstance(source, str) or not re.fullmatch('[a-f0-9]{40}', source):
        raise ValueError('exact benchmark source commit required')
    def blob(name):
        return subprocess.check_output(['git', 'show', source+':'+name], cwd=root)
    names = {n for n in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source,
        '--', 'utopia'], cwd=root, text=True).splitlines() if n.endswith('.py')}
    pending = list(scripts)
    while pending:
        name = pending.pop()
        if name in names:
            continue
        names.add(name)
        for node in ast.walk(ast.parse(blob(name))):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            if isinstance(node, ast.ImportFrom) and node.module == 'scripts':
                modules = ['scripts.'+a.name for a in node.names]
            for module in modules:
                if module.startswith('scripts.'):
                    dependency = module.replace('.', '/')+'.py'
                    if dependency not in names:
                        pending.append(dependency)
    names.update(resources)
    proofs = {}
    for name in sorted(names):
        path = root/name
        expected = hashlib.sha256(blob(name)).hexdigest()
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('benchmark replay-critical source differs: '+name)
        proofs[name] = expected
    return {'status': 'verified-exact-source-closure', 'files': proofs}
