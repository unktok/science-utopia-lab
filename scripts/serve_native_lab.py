#!/usr/bin/env python3
"""Loopback-only local UI + JSON queue, or a single pinned execution worker.

No cloud deployment, request-provided paths, command strings or host code eval.
Build game-ui-v2 first. Launch worker separately with --worker-once.
"""
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utopia.optimization.native_jobs import NativeJobQueue, pinned_revision, validate_job_request
from utopia.system import SystemSpec
from utopia.system.design_patch import digest


def make_server(queue, *, source_commit, directory, port=4591):
    static = Path(directory).resolve()
    token = secrets.token_urlsafe(32)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static), **kwargs)

        def allowed(self):
            expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            origin = self.headers.get('Origin')
            return self.headers.get('Host') in expected and (origin is None or origin in {'http://' + h for h in expected})

        def reply(self, status, value):
            raw = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            return secrets.compare_digest(self.headers.get('X-Native-Lab-Token', ''), token)

        def do_GET(self):
            if not self.allowed():
                return self.reply(403, {'error': 'loopback host/origin required'})
            path = urlsplit(self.path).path
            try:
                if path == '/native-api/session':
                    return self.reply(200, {'token': token, 'source_commit': source_commit, 'mode': 'local-development-queue'})
                if path.startswith('/native-api/'):
                    if not self.authorized():
                        return self.reply(403, {'error': 'session token required'})
                    parts = path.split('/')
                    if len(parts) == 4 and parts[2] == 'jobs':
                        return self.reply(200, queue.get(parts[3]))
                    if len(parts) == 5 and parts[2] == 'jobs' and parts[4] == 'evidence':
                        return self.reply(200, queue.evidence(parts[3]))
                    return self.reply(404, {'error': 'unknown API route'})
                translated = Path(self.translate_path(path)).resolve()
                if not translated.is_relative_to(static) or translated.is_dir():
                    return self.reply(404, {'error': 'static file not found'})
                return super().do_GET()
            except KeyError:
                return self.reply(404, {'error': 'unknown job'})
            except (ValueError, TypeError) as error:
                return self.reply(400, {'error': str(error)})

        def do_POST(self):
            if not self.allowed() or not self.authorized() or self.headers.get('Origin') is None:
                return self.reply(403, {'error': 'same-origin session token required'})
            if self.path not in {'/native-api/jobs', '/native-api/validate'}:
                return self.reply(404, {'error': 'unknown API route'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 512_000 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('bounded JSON request required')
                request = json.loads(self.rfile.read(size))
                if pinned_revision(ROOT) != source_commit:
                    raise ValueError('source changed after server startup')
                if self.path == '/native-api/validate':
                    validate_job_request(request)
                    return self.reply(200, {'status': 'structurally-validated-not-native-executed',
                        'candidate_fingerprint': SystemSpec.from_dict(request['system']).fingerprint,
                        'request_sha256': digest(request)})
                return self.reply(201, queue.submit(request, source_commit=source_commit))
            except (ValueError, TypeError, KeyError) as error:
                return self.reply(400, {'error': str(error)})

        def log_message(self, *args):
            pass  # no token, source, raw model text or request body in access logs

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue', type=Path, required=True)
    parser.add_argument('--port', type=int, default=4591)
    parser.add_argument('--worker-once', action='store_true')
    parser.add_argument('--data-cache', type=Path)
    args = parser.parse_args()
    revision = pinned_revision(ROOT)
    queue = NativeJobQueue(args.queue)
    if args.worker_once:
        if args.data_cache is None:
            parser.error('--worker-once requires --data-cache')
        from utopia.optimization.native_factory import LocalQwenNativeFactory
        def builder(root, request):
            return LocalQwenNativeFactory(root / 'runs', args.data_cache, years=request['years'], corpus_years=4,
                experiment_binding={'request_sha256': digest(request), 'loss_spec': request['loss_spec']})
        print(json.dumps(queue.run_one(builder, source_commit=revision)), flush=True)
    else:
        directory = ROOT / 'game-ui-v2/dist'
        if not (directory / 'native.html').exists():
            parser.error('build game-ui-v2 first')
        server = make_server(queue, source_commit=revision, directory=directory, port=args.port)
        print(f'Local native lab: http://127.0.0.1:{server.server_port}/native.html', flush=True)
        try:
            server.serve_forever()
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
