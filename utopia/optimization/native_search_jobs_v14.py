"""Durable, bounded, opt-in local autonomous search queue.

API processes never construct providers or execute native trials. An explicit
worker shares the old native queue's flock, so the two modes cannot overlap.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid

from utopia.optimization.native_search_v14 import NativeSearchController, make_search_plan
from utopia.system.design_patch import clone, digest


class NativeSearchQueue:
    def __init__(self, directory, *, provider_binding):
        from utopia.optimization.native_search_v14 import validate_provider_binding
        validate_provider_binding(provider_binding)
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.provider_binding = clone(provider_binding)
        self.path = self.directory / 'native-search-jobs-v14.sqlite'
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS searches (id TEXT PRIMARY KEY, plan TEXT NOT NULL, '
                'plan_hash TEXT NOT NULL UNIQUE, status TEXT NOT NULL, created REAL NOT NULL, '
                'updated REAL NOT NULL, error TEXT)')

    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def validate(self, request, *, source_commit):
        plan = make_search_plan(request, source_commit=source_commit, provider_binding=self.provider_binding)
        return {'status': 'structurally-validated-not-native-executed',
            'request_sha256': plan['request_sha256'], 'source_commit': source_commit,
            'planned_native_world_budget': request['native_budget'], 'method': request['method'],
            'plan_sha256': digest(plan), 'provider_binding': clone(self.provider_binding),
            'maximum_designer_provider_attempts': plan['maximum_designer_provider_attempts']}

    def submit(self, request, *, confirmed_request_sha256, source_commit):
        plan = make_search_plan(request, source_commit=source_commit, provider_binding=self.provider_binding)
        if confirmed_request_sha256 != plan['request_sha256']:
            raise ValueError('exact validated request SHA256 compute consent required')
        plan_hash = digest(plan)
        identity = 'search-' + uuid.uuid4().hex
        now = time.time()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT id FROM searches WHERE plan_hash=?', (plan_hash,)).fetchone()
            if existing is not None:
                identity = existing['id']
            else:
                if db.execute("SELECT count(*) FROM searches WHERE status IN ('queued','running')").fetchone()[0] >= 2:
                    raise ValueError('local search queue is full; wait for existing searches')
                NativeSearchController(self.directory / identity, plan=plan, plan_sha256=plan_hash)
                db.execute('INSERT INTO searches VALUES (?,?,?,?,?,?,?)',
                    (identity, json.dumps(plan, sort_keys=True, allow_nan=False), plan_hash, 'queued', now, now, None))
        return self.get(identity)

    def _load(self, identity):
        if not isinstance(identity, str) or not re.fullmatch(r'search-[a-f0-9]{32}', identity):
            raise ValueError('invalid search identity')
        with self.connection() as db:
            row = db.execute('SELECT * FROM searches WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise KeyError('unknown search')
        plan = json.loads(row['plan'])
        if digest(plan) != row['plan_hash']:
            raise ValueError('search plan hash mismatch')
        if plan['provider_binding'] != self.provider_binding:
            raise ValueError('operator provider binding differs from immutable search plan')
        root = self.directory / identity
        state_name = 'native-adaptive-state.json' if plan['request']['method'] == 'blackbox' else 'native-nested-state.json'
        if not (root / 'plan.json').is_file() or not (root / 'campaign' / state_name).is_file():
            raise ValueError('saved search plan/campaign is missing; cannot recreate consumed slots')
        controller = NativeSearchController(root, plan=plan, plan_sha256=row['plan_hash'])
        if row['status'] not in {'queued', 'running', 'complete', 'failed'}:
            raise ValueError('invalid persisted search status')
        if row['status'] == 'complete' and not controller.complete:
            raise ValueError('complete search missing scheduled evidence')
        return row, controller

    def get(self, identity):
        row, controller = self._load(identity)
        result = controller.projection(search_id=identity, status=row['status'],
            errors=[{'worker_error': row['error'], 'loss': None}] if row['error'] else [])
        result.update(created_at=row['created'], updated_at=row['updated'])
        return result

    def evidence(self, identity):
        # Partial, null and failed stages are evidence too. The complete flag is
        # explicit; this endpoint does not promote partial output into findings.
        return self.get(identity)

    @contextmanager
    def worker_lock(self):
        with (self.directory / 'worker.lock').open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError('another native/search worker already owns this queue') from error
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def run_one(self, factory_builder, *, generator_builder, source_commit, after_stage=None):
        """Finish one finite search; BaseException interruption leaves it resumable.

        Builder(root, request) returns the trusted native factory. The generator
        builder(root, request, provider_binding) is also operator supplied; JSON
        never chooses a module, command, path, provider endpoint or callback.
        """
        with self.worker_lock():
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute("SELECT id FROM searches WHERE status IN ('running','queued') "
                    "ORDER BY CASE status WHEN 'running' THEN 0 ELSE 1 END,created,id LIMIT 1").fetchone()
                if row is None:
                    return None
                identity = row['id']
                db.execute("UPDATE searches SET status='running',updated=? WHERE id=?", (time.time(), identity))
            try:
                row, controller = self._load(identity)
                if controller.plan['source_commit'] != source_commit:
                    raise ValueError('worker source differs from immutable submitted source')
                # An interruption after final campaign commit must not construct
                # a provider or native factory, much less execute another trial.
                if not controller.complete:
                    root = self.directory / identity
                    factory = factory_builder(root, clone(controller.request))
                    actual = {k: getattr(factory, k) for k in
                        ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'corpus_years')}
                    expected = {k: self.provider_binding[k] for k in actual}
                    if actual != expected:
                        raise ValueError('actual native factory model/corpus differs from immutable operator binding')
                    generator = generator_builder(root, clone(controller.request), clone(self.provider_binding))
                    if not callable(generator):
                        raise ValueError('operator must supply a callable local vocabulary generator')
                    while not controller.complete:
                        controller.advance(simulation_factory=factory, generator=generator)
                        with self.connection() as db:
                            db.execute('UPDATE searches SET updated=? WHERE id=?', (time.time(), identity))
                        if after_stage is not None:
                            after_stage(controller)
                with self.connection() as db:
                    db.execute("UPDATE searches SET status='complete',error=NULL,updated=? WHERE id=?",
                        (time.time(), identity))
            except Exception as error:
                with self.connection() as db:
                    db.execute("UPDATE searches SET status='failed',error=?,updated=? WHERE id=?",
                        (str(error)[:3000], time.time(), identity))
            return self.get(identity)
