"""Local durable design jobs. JSON requests are data, never host commands.

One pinned worker owns execution. UI/API processes only validate and enqueue.
Generated source stays inside the existing no-network container executor.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import re
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid

from utopia.optimization.loss import evaluate_loss, validate_loss_spec
from utopia.system import SystemSpec, validate_system_spec
from utopia.system.code_mechanisms import CODE_IMPLEMENTATION, validate_code_artifact
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic

RESERVED_SEEDS = {523, 541, 547, 701, 709, 719, 727, 733,
                  31001, 31013, 31019, 31033, 31039}
METRICS = {'native.accepted_decisions', 'native.rejected_decisions', 'native.review_records',
           'native.final_active_authors', 'native.final_author_resources', 'native.institutional_context_deliveries'}


def validate_job_request(request, *, measured_metrics=METRICS):
    if not isinstance(request, dict) or set(request) != {'parent_system', 'system', 'loss_spec', 'seed', 'years'}:
        raise ValueError('request requires only parent_system, system, loss_spec, seed and years')
    if type(request['seed']) is not int or not 0 <= request['seed'] < 2**31 or request['seed'] in RESERVED_SEEDS:
        raise ValueError('explicit development seed required; historical held-out seeds are reserved')
    if type(request['years']) is not int or not 1 <= request['years'] <= 4:
        raise ValueError('local interactive execution budget is 1..4 native years')
    if len(json.dumps(request, allow_nan=False).encode()) > 512_000:
        raise ValueError('job request exceeds byte budget')
    for key in ('parent_system', 'system'):
        spec = SystemSpec.from_dict(request[key])
        validate_system_spec(spec).require_valid()
        if spec.initial_state.get('seed') != request['seed']:
            raise ValueError('requested development seed must match both system initial states')
        if not any(n.implementation.startswith('native.phase.') for n in spec.mechanisms):
            raise ValueError('native world required, not a substitute numeric graph')
        for node in spec.mechanisms:
            if node.implementation == CODE_IMPLEMENTATION:
                validate_code_artifact(node.parameters['code_artifact'])
                image = node.parameters.get('runtime_image_id', '')
                if not isinstance(image, str) or len(image) != 71 or not image.startswith('sha256:') or any(c not in '0123456789abcdef' for c in image[7:]):
                    raise ValueError('generated source requires a pinned local runtime image digest')
    validate_loss_spec(request['loss_spec'])
    if request['loss_spec']['optimization_seed_role'] != 'development':
        raise ValueError('interactive jobs are development only')
    if any(t['metric_id'] not in measured_metrics or t['slice_id'] is not None for t in request['loss_spec']['per_run']['terms']):
        raise ValueError('requested loss has no implemented native measurement adapter')
    if request['loss_spec']['across_seeds']['minimum_valid_runs'] != 1:
        raise ValueError('one-seed interactive job requires minimum_valid_runs=1')


class NativeJobQueue:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'native-jobs.sqlite'
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, request TEXT NOT NULL, request_hash TEXT NOT NULL, source_commit TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, result TEXT, error TEXT)')

    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def submit(self, request, *, source_commit):
        validate_job_request(request)
        if not isinstance(source_commit, str) or len(source_commit) != 40 or any(c not in '0123456789abcdef' for c in source_commit):
            raise ValueError('clean pinned source commit required')
        identity = 'job-' + uuid.uuid4().hex
        now = time.time()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute("SELECT id FROM jobs WHERE request_hash=? AND source_commit=? AND status IN ('queued','running') ORDER BY created LIMIT 1", (digest(request), source_commit)).fetchone()
            if existing is not None:
                return self.get(existing['id'])
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0] >= 2:
                raise ValueError('local queue is full; wait for existing jobs')
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)',
                (identity, json.dumps(request, sort_keys=True, allow_nan=False), digest(request), source_commit, 'queued', now, now, None, None))
        return self.get(identity)

    def _row(self, identity):
        if not isinstance(identity, str) or len(identity) != 36 or not identity.startswith('job-') or any(c not in '0123456789abcdef' for c in identity[4:]):
            raise ValueError('invalid job identity')
        with self.connection() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise KeyError('unknown job')
        request = json.loads(row['request'])
        validate_job_request(request)
        if digest(request) != row['request_hash']:
            raise ValueError('queued request hash mismatch')
        return row, request

    def get(self, identity):
        row, request = self._row(identity)
        result = json.loads(row['result']) if row['result'] else None
        if result is not None:
            value = evaluate_loss(request['loss_spec'], result['measurements'])
            if value['status'] != 'complete' or value['loss'] != result['native_loss']:
                raise ValueError('job result differs from declared native measurements/loss')
        checkpoint_year = request['years'] if row['status'] == 'complete' else 0
        campaign = self.directory / identity / 'campaign/native-design-state.json'
        if row['status'] == 'running' and campaign.exists():
            state = json.loads(campaign.read_text())
            record = state.get('pending') or next(iter(state.get('records', [])), None)
            if record:
                suggestion_id = record['suggestion']['suggestion_id']
                if not re.fullmatch(r'native-design-[a-f0-9]{20}', suggestion_id):
                    raise ValueError('invalid persisted job suggestion identity')
                checkpoints = self.directory / identity / 'runs' / (suggestion_id + '-s' + str(request['seed'])) / 'simulation/checkpoints/native-design'
                checkpoint_year = max([0] + [int(m.group(1)) for p in checkpoints.glob('portable_checkpoint_year_*.json.gz')
                    if (m := re.fullmatch(r'portable_checkpoint_year_(\d+)\.json\.gz', p.name)) and 1 <= int(m.group(1)) <= request['years']])
        return {'job_id': identity, 'status': row['status'], 'request_sha256': row['request_hash'],
            'source_commit': row['source_commit'], 'parent_fingerprint': SystemSpec.from_dict(request['parent_system']).fingerprint,
            'candidate_fingerprint': SystemSpec.from_dict(request['system']).fingerprint,
            'seed': request['seed'], 'years': request['years'], 'result': result, 'error': row['error'],
            'checkpoint_year': checkpoint_year, 'loss_id': request['loss_spec']['id'],
            'seed_role': 'development', 'model_weights_trained': False, 'same_society_migration': False}

    def evidence(self, identity):
        row, _ = self._row(identity)
        if row['status'] != 'complete':
            raise ValueError('no completed evidence for this job')
        value = json.loads((self.directory / identity / 'viewer.json').read_text())
        if digest(value) != json.loads(row['result'])['viewer_sha256']:
            raise ValueError('job evidence hash mismatch')
        return value

    @contextmanager
    def worker_lock(self):
        with (self.directory / 'worker.lock').open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError('another worker already owns this queue') from error
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def run_one(self, factory_builder, *, source_commit):
        """Resume the same running job before claiming queued work. One writer."""
        from utopia.optimization.native_design import NativeDesignCampaign
        from utopia.replay.native_lab import native_lab_envelope
        with self.worker_lock():
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute("SELECT id FROM jobs WHERE status IN ('running','queued') ORDER BY CASE status WHEN 'running' THEN 0 ELSE 1 END,created LIMIT 1").fetchone()
                if row is None:
                    return None
                identity = row['id']
                db.execute("UPDATE jobs SET status='running',updated=? WHERE id=?", (time.time(), identity))
            try:
                row, request = self._row(identity)
                if row['source_commit'] != source_commit:
                    raise ValueError('worker source differs from pinned submitted source')
                root = self.directory / identity
                write_json_atomic(root / 'request.json', request, sort_keys=True, allow_nan=False)
                factory = factory_builder(root, request)
                binding = {'source_commit': source_commit, 'request_sha256': row['request_hash'],
                    'model': factory.model, 'model_digest': factory.model_digest,
                    'corpus_sha256': factory.corpus_sha256, 'dataset_identity': factory.dataset_identity,
                    'years': request['years'], 'corpus_years': factory.corpus_years,
                    'population': 'five-independent-balanced-researchers', 'origin': 'explicit-local-UI-submission'}
                campaign = NativeDesignCampaign(root / 'campaign', initial_system=SystemSpec.from_dict(request['system']),
                    loss_spec=request['loss_spec'], seeds=[request['seed']], world_binding=binding)
                if not campaign.state['records']:
                    campaign.advance(simulation_factory=factory)
                observation = campaign.state['records'][0]['observation']
                if observation['status'] != 'complete' or observation['metadata']['technical_failures']:
                    raise ValueError('native execution failed: ' + json.dumps(observation['metadata']['technical_failures'])[:2000])
                envelope = native_lab_envelope(root, loss_spec=request['loss_spec'])
                write_json_atomic(root / 'viewer.json', envelope, sort_keys=True, allow_nan=False)
                result = {'native_loss': observation['loss'], 'measurements': observation['metadata']['measurements'],
                          'viewer_sha256': digest(envelope), 'observation_id': observation['observation_id']}
                with self.connection() as db:
                    db.execute("UPDATE jobs SET status='complete',result=?,error=NULL,updated=? WHERE id=?",
                        (json.dumps(result, allow_nan=False), time.time(), identity))
            except Exception as error:
                with self.connection() as db:
                    db.execute("UPDATE jobs SET status='failed',result=NULL,error=?,updated=? WHERE id=?", (str(error)[:3000], time.time(), identity))
            return self.get(identity)


def pinned_revision(root):
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root):
        raise ValueError('local execution requires clean pinned source')
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
