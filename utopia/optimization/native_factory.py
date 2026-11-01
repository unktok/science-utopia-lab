"""Pinned local-Qwen factory for native design and gradient evaluations."""
from __future__ import annotations

from pathlib import Path
import os
import subprocess

from utopia.utils.data_utils import write_json_atomic


class LocalQwenNativeFactory:
    """Same real native world for every method; per-suggestion caches/outputs.

    Original public corpus and original phases are used, never test fixtures.
    Durable response/year replay is owned by Simulation/CompletedResponseCache.
    """
    def __init__(self, directory, data_cache, *, years=4, model='qwen3:8b', max_tokens=768,
                 experiment_binding=None, allow_dirty=False, corpus_years=None, record_wire=False, record_code=False,
                 inference_lock=None):
        import requests
        from utopia.utils.paths import project_root
        self.source_root = project_root(__file__)
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=self.source_root) and not allow_dirty:
            raise ValueError('native design experiments require clean commit-pinned source')
        self.source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.source_root, text=True).strip()
        self.allow_dirty = allow_dirty
        self.directory, self.data_cache = Path(directory), Path(data_cache)
        self.years, self.model, self.max_tokens = years, model, max_tokens
        self.corpus_years = years if corpus_years is None else corpus_years
        if type(self.corpus_years) is not int or self.corpus_years < years:
            raise ValueError('corpus horizon must contain every native simulation year')
        self.experiment_binding = experiment_binding or {}
        self.runtime_seed_binding = {'python_hash_seed_environment': os.environ.get('PYTHONHASHSEED'),
            'python_hash_probe': hash('scienceutopia.native-world.v1')}
        hash_seed = self.runtime_seed_binding['python_hash_seed_environment']
        if not isinstance(hash_seed, str) or not hash_seed.isdecimal() or not 0 <= int(hash_seed) < 2**32:
            raise ValueError('launch native Python with a fixed numeric PYTHONHASHSEED; runtime set_seed cannot configure Python hashing')
        self.record_wire = record_wire
        self.record_code = record_code
        self.inference_lock = Path(inference_lock).resolve() if inference_lock else None
        response = requests.get('http://127.0.0.1:11434/api/tags', timeout=10)
        response.raise_for_status()
        self.model_digest = next(m['digest'] for m in response.json()['models'] if m['name'] == model)
        # Bind the actual data BEFORE constructing the outer campaign, so two
        # candidates cannot silently use different corpora under one label.
        from utopia.data.rag import RAG, RAGConfig
        from utopia.runtime.checkpointing import capture_rng, restore_rng
        rng = capture_rng()
        try:
            rag = RAG(RAGConfig(device='cpu', cache_dir=str(self.data_cache / 'rag')))
            rag.load_documents(num_years=self.corpus_years)
            self.corpus_sha256, self.dataset_identity = rag.document_identity, rag.dataset_identity
        finally:
            restore_rng(rng)

    def __call__(self, spec, seed, run_id):
        from utopia.arguments import parse_arguments
        from utopia.models.models import VLLMServerModel
        from utopia.models.response_cache import CompletedResponseCache
        from utopia.runtime.checkpointing import capture_rng, restore_rng
        from utopia.simulation import Simulation
        from utopia.utils.seeding import set_seed
        if (subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.source_root, text=True).strip() != self.source_commit
                or (not self.allow_dirty and subprocess.check_output(['git', 'status', '--porcelain'], cwd=self.source_root))):
            raise ValueError('native experiment source changed since factory construction')
        if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in run_id):
            raise ValueError('native run id must be a safe single directory name')
        root = self.directory / run_id
        system_path = root / 'system.json'
        if system_path.exists():
            import json
            if json.loads(system_path.read_text()) != spec.to_dict():
                raise ValueError('run path already belongs to another native design')
        else:
            write_json_atomic(system_path, spec.to_dict(), sort_keys=True, allow_nan=False)
        args = parse_arguments([
            '--model', self.model, '--vllm_url', 'http://127.0.0.1:11434/v1', '--api-backend', 'ollama',
            '--num_years', str(self.years), '--seed', str(seed), '--population_mode', 'university_only',
            '--num_institutions', '5', '--researchers_per_institution', '1', '--num_conferences', '1',
            '--experiment_stage', 'smoke', '--run-id', 'native-design', '--strategy_mix', 'balanced',
            '--funding_allocation_mode', 'fixed', '--experiment_name', 'default_native_design',
            '--output-dir', str(root / 'simulation'), '--data-cache-dir', str(self.data_cache),
            '--science-system-spec', str(system_path), '--rag_device', 'cpu', '--batch_size', '1', '--max_retries', '2',
        ], create_dirs=True)
        args.rag_corpus_years = self.corpus_years
        model = VLLMServerModel(self.model, base_url='http://127.0.0.1:11434/v1', server_backend='ollama',
            max_concurrent_requests=1, run_seed=seed, model_revision=self.model_digest,
            max_tokens_override=self.max_tokens, thinking_override=False, sdk_max_retries=0, request_timeout=120)
        set_seed(seed)
        sim = Simulation(model, num_years=self.years, output_dir=args.output_dir, args=args,
                         funding_allocation_mode='fixed', experiment_name=args.experiment_name, max_retries=2)
        rng = capture_rng()
        sim.rag.load_documents(num_years=self.corpus_years)
        restore_rng(rng)
        if sim.rag.document_identity != self.corpus_sha256:
            raise ValueError('native corpus changed between design evaluations')
        binding = {'protocol': 'native-design-loops-v1', 'cell': spec.fingerprint, 'model': self.model,
            'model_revision': self.model_digest, 'corpus_sha256': sim.rag.document_identity, 'seed': seed,
            'science_config': {'source_commit': self.source_commit, 'years': self.years, 'corpus_years': self.corpus_years,
                'population': {'institutions': 5, 'per_institution': 1, 'strategy': 'balanced'},
                'runtime_seed_binding': self.runtime_seed_binding,
                'lab_inference_serialized': bool(self.inference_lock),
                'thinking_override': False, 'max_tokens': self.max_tokens, 'experiment': self.experiment_binding}}
        model.response_cache = CompletedResponseCache(root / 'replies' / 'responses.sqlite', binding=binding)
        try:
            sim.enable_portable_checkpoints(binding)
        except BaseException:
            model.response_cache.close()
            raise
        if self.record_wire:
            record_native_http(model, sim, root / 'wire-requests.jsonl')
        if self.inference_lock:
            serialize_native_http(model, self.inference_lock)
        from utopia.system.native_process import IMPLEMENTATION as PROCESS_IMPLEMENTATION, _validate_parameters
        code_nodes = [(_validate_parameters(n.parameters) if n.implementation == PROCESS_IMPLEMENTATION else n)
                      for n in spec.mechanisms]
        code_nodes = [n for n in code_nodes if n.implementation == 'code.python.v1']
        if self.record_code and code_nodes:
            from utopia.optimization.native_code_trace import RecordingCodeExecutor
            from utopia.system.code_mechanisms import DockerCodeExecutor
            images = {n.parameters['runtime_image_id'] for n in code_nodes}
            try:
                if len(images) != 1:
                    raise ValueError('native code recording requires one explicitly pinned image')
                sim.native_system.code_executor = RecordingCodeExecutor(DockerCodeExecutor(next(iter(images))),
                    root / 'code-contexts.jsonl', binding={'source_commit': self.source_commit,
                        'system_fingerprint': spec.fingerprint, 'run_id': run_id})
            except BaseException:
                model.response_cache.close()
                raise
        return sim


def record_native_http(model, simulation, path):
    """Record actual cache-miss payloads, never credentials or cache replays.

    Raw local evidence only. Existing response journals independently retain
    payload/response hashes. Failed requests can leave extra input records.
    """
    import hashlib
    import json
    import threading
    from utopia.runtime.checkpointing import canonical_json
    path = Path(path)
    lock = threading.Lock()
    callback = model.client.chat.completions.create
    def recorded(**payload):
        frame = simulation.native_system._frame
        record = {'year': frame['year'] if frame else None,
                  'payload_sha256': hashlib.sha256(canonical_json(payload).encode()).hexdigest(), 'payload': payload}
        with lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a') as handle:
                handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                handle.flush()
        return callback(**payload)
    model.client.chat.completions.create = recorded


def serialize_native_http(model, path):
    """One resident endpoint, concurrent lab pipelines, one active HTTP call.

    Every participating worker uses the same explicit local lock file. This
    does not govern unrelated applications or claim an inference speedup.
    """
    import fcntl
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    callback = model.client.chat.completions.create
    def serialized(**payload):
        with path.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                return callback(**payload)
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
    model.client.chat.completions.create = serialized
