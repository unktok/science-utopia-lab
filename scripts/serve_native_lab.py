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
from utopia.runtime.checkpointing import PortableCheckpointError


def make_server(queue, *, source_commit, directory, port=4591,
                society_session=None, society_checkpoints=None, search_queue=None):
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

        def end_headers(self):
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            super().end_headers()

        def do_HEAD(self):
            if not self.allowed():
                return self.reply(403, {'error': 'loopback host/origin required'})
            translated = Path(self.translate_path(urlsplit(self.path).path)).resolve()
            if not translated.is_relative_to(static) or translated.is_dir():
                return self.reply(404, {'error': 'static file not found'})
            return super().do_HEAD()

        def do_GET(self):
            if not self.allowed():
                return self.reply(403, {'error': 'loopback host/origin required'})
            path = urlsplit(self.path).path
            try:
                if path == '/native-api/session':
                    return self.reply(200, {'token': token, 'source_commit': source_commit,
                        'mode': 'local-development-queue', 'search_enabled': search_queue is not None})
                if path.startswith('/native-api/'):
                    if not self.authorized():
                        return self.reply(403, {'error': 'session token required'})
                    parts = path.split('/')
                    if path == '/native-api/society' and society_session is not None:
                        return self.reply(200, society_session.projection())
                    if (len(parts) == 5 and parts[2:4] == ['society', 'requests']
                            and society_session is not None):
                        checkpoint = None
                        if society_checkpoints is not None:
                            import re
                            matches = [(int(m.group(1)), p) for p in Path(society_checkpoints).glob('portable_checkpoint_year_*.json.gz')
                                if (m := re.fullmatch(r'portable_checkpoint_year_(\d+)\.json\.gz', p.name))]
                            checkpoint = max(matches, default=(0, None))[1]
                        return self.reply(200, society_session.adoption_status(parts[4], checkpoint=checkpoint))
                    if len(parts) == 4 and parts[2] == 'jobs':
                        return self.reply(200, queue.get(parts[3]))
                    if len(parts) == 5 and parts[2] == 'jobs' and parts[4] == 'evidence':
                        return self.reply(200, queue.evidence(parts[3]))
                    if search_queue is not None and len(parts) == 4 and parts[2] == 'searches':
                        return self.reply(200, search_queue.get(parts[3]))
                    if search_queue is not None and len(parts) == 5 and parts[2] == 'searches' and parts[4] == 'evidence':
                        return self.reply(200, search_queue.evidence(parts[3]))
                    return self.reply(404, {'error': 'unknown API route'})
                translated = Path(self.translate_path(path)).resolve()
                if not translated.is_relative_to(static) or translated.is_dir():
                    return self.reply(404, {'error': 'static file not found'})
                return super().do_GET()
            except KeyError:
                return self.reply(404, {'error': 'unknown job or search'})
            except PortableCheckpointError:
                return self.reply(503, {'error': 'saved society checkpoint failed integrity validation; no adoption verified'})
            except (ValueError, TypeError) as error:
                return self.reply(400, {'error': str(error)})

        def do_POST(self):
            if not self.allowed() or not self.authorized() or self.headers.get('Origin') is None:
                return self.reply(403, {'error': 'same-origin session token required'})
            if self.path not in {'/native-api/jobs', '/native-api/validate', '/native-api/society/confirm',
                    '/native-api/search-validate', '/native-api/searches'}:
                return self.reply(404, {'error': 'unknown API route'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 512_000 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('bounded JSON request required')
                request = json.loads(self.rfile.read(size))
                if pinned_revision(ROOT) != source_commit:
                    raise ValueError('source changed after server startup')
                if self.path in {'/native-api/search-validate', '/native-api/searches'}:
                    if search_queue is None:
                        return self.reply(404, {'error': 'autonomous search is not enabled by the local operator'})
                    if self.path == '/native-api/search-validate':
                        return self.reply(200, search_queue.validate(request, source_commit=source_commit))
                    if not isinstance(request, dict) or set(request) != {'request', 'confirmed_request_sha256'}:
                        raise ValueError('exact request and confirmed_request_sha256 compute consent required')
                    return self.reply(201, search_queue.submit(request['request'],
                        confirmed_request_sha256=request['confirmed_request_sha256'], source_commit=source_commit))
                if self.path == '/native-api/society/confirm':
                    if society_session is None:
                        return self.reply(404, {'error': 'no native society session configured'})
                    if not isinstance(request, dict) or set(request) != {'request_id', 'confirmed_request_sha256'}:
                        raise ValueError('exact staged request ID and confirmation SHA256 required')
                    return self.reply(202, society_session.confirm(**request))
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
    parser.add_argument('--search-worker-once', action='store_true',
                        help='opt-in bounded autonomous search worker; separate from old jobs')
    parser.add_argument('--search-config', type=Path,
                        help='operator-owned JSON {provider_binding}; enables autonomous search API')
    parser.add_argument('--data-cache', type=Path)
    parser.add_argument('--society-config', type=Path,
                        help='operator-owned session config; never a request-selected checkpoint path')
    args = parser.parse_args()
    revision = pinned_revision(ROOT)
    queue = NativeJobQueue(args.queue)
    if args.worker_once and args.search_worker_once:
        parser.error('choose one worker mode')
    search_queue = None
    if args.search_config is not None:
        from utopia.optimization.native_search_jobs_v14 import NativeSearchQueue
        config = json.loads(args.search_config.read_text())
        if not isinstance(config, dict) or set(config) != {'provider_binding'}:
            parser.error('search config requires exact operator-owned provider_binding')
        search_queue = NativeSearchQueue(args.queue, provider_binding=config['provider_binding'])
    if args.search_worker_once:
        if args.data_cache is None or search_queue is None:
            parser.error('--search-worker-once requires --data-cache and --search-config')
        from utopia.optimization.native_factory import LocalQwenNativeFactory
        def search_factory(root, request):
            return LocalQwenNativeFactory(root / 'worlds', args.data_cache, years=request['years'], corpus_years=4,
                record_wire=True, record_code=True, inference_lock=args.queue / 'inference.lock',
                experiment_binding={'request_sha256': digest(request), 'loss_spec': request['loss_spec']})
        def search_generator(root, request, provider_binding):
            from utopia.optimization.native_search_generator_v14 import make_local_vocabulary_generator
            return make_local_vocabulary_generator(root / 'authoring', image_id=provider_binding['image_id'],
                provider_binding=provider_binding, max_attempts=request['designer']['max_attempts'],
                max_tokens=request['designer']['max_tokens'], inference_lock=args.queue / 'inference.lock')
        print(json.dumps(search_queue.run_one(search_factory, generator_builder=search_generator,
            source_commit=revision), allow_nan=False), flush=True)
    elif args.worker_once:
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
        session, checkpoints = None, None
        if args.society_config is not None:
            from utopia.optimization.native_society_design import NativeSocietyDesignSession
            config = json.loads(args.society_config.read_text())
            if set(config) != {'directory', 'founding_system', 'loss_spec', 'world_binding', 'checkpoint_directory'}:
                parser.error('society config requires explicit session, founding design, loss, world and checkpoint directory')
            session = NativeSocietyDesignSession(config['directory'],
                founding_system=SystemSpec.from_dict(config['founding_system']), loss_spec=config['loss_spec'],
                world_binding=config['world_binding'])
            checkpoints = Path(config['checkpoint_directory']).resolve()
        server = make_server(queue, source_commit=revision, directory=directory, port=args.port,
                             society_session=session, society_checkpoints=checkpoints, search_queue=search_queue)
        print(f'Local native lab: http://127.0.0.1:{server.server_port}/native.html', flush=True)
        try:
            server.serve_forever()
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
