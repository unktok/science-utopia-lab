"""Real corpus-loader/cache/tensor-retrieval + original native phase QA.

Only the dataset payload, embedding encoder and researcher HTTP replies are
scripted. Unlike the older fixture, no retrieval/index-building code is replaced.
No live inference, model downloads or existing experiment files are touched.
"""
from collections import Counter
import hashlib
import random
import sys
from types import ModuleType

import numpy as np
import pandas as pd
import pytest
import torch

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.agents.funding_agents import FundingProgram
from utopia.data.rag import RAG, RAGConfig
from utopia.runtime.checkpointing import PortableStop, capture_rng
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.utils.data_utils import file_sha256

REAL_LOAD = RAG.load_documents
REAL_BUILD = RAG.build_knowledge_index
REAL_RETRIEVE = RAG.batch_retrieve


class DeterministicEncoder:
    def __init__(self, calls):
        self.calls = calls
    def encode(self, texts, **kwargs):
        self.calls.append(list(texts))
        array = np.asarray([[v / 255. for v in hashlib.sha256(t.encode()).digest()[:8]] for t in texts], dtype=np.float32)
        tensor = torch.from_numpy(array)
        if kwargs.get('normalize_embeddings'):
            tensor = torch.nn.functional.normalize(tensor, p=2, dim=1)
        return tensor.numpy() if kwargs.get('convert_to_numpy') else tensor


@pytest.fixture
def real_retrieval(fixed_corpus, monkeypatch):
    from datasets import Dataset
    rows = [dict(id=f'fixture-{i:03d}', title=f'Fixture paper {i}', summary=f'Fixture abstract {i}',
        tags=['cs.AI'], published=f'{2016 + i // 8}-02-01') for i in range(48)]
    monkeypatch.setattr('utopia.data.rag.load_dataset', lambda *a, **k: Dataset.from_list(rows))
    monkeypatch.setattr(RAG, 'load_documents', REAL_LOAD)
    monkeypatch.setattr(RAG, 'build_knowledge_index', REAL_BUILD)
    monkeypatch.setattr(RAG, 'batch_retrieve', REAL_RETRIEVE)
    calls = []
    module = ModuleType('sentence_transformers')
    def encoder(*args, **kwargs):
        # Even model construction that consumes global RNG must not alter the
        # restored society's scientific random trajectory on cold reconstruction.
        random.random()
        torch.rand(3)
        return DeterministicEncoder(calls)
    module.SentenceTransformer = encoder
    monkeypatch.setitem(sys.modules, 'sentence_transformers', module)
    return calls


def real_sim(root, cache, encode_calls, *, preload=True):
    sim, calls = make_sim(root, native=NativeScienceKernel(legacy_world_system()))
    sim.num_years = 3
    sim.args.rag_corpus_years = 6
    sim.rag = RAG(RAGConfig(device='cpu', n_workers=1, cache_dir=str(cache)),
        model=DeterministicEncoder(encode_calls))
    if preload:
        sim.rag.load_documents(num_years=6)
    return sim, calls


def tensor_hash(tensor):
    return hashlib.sha256(tensor.cpu().numpy().tobytes()).hexdigest()


@pytest.mark.parametrize('cache_present', [True, False])
def test_preloaded_documents_rebuild_real_derived_index_with_zero_http_and_preserved_rng(tmp_path, real_retrieval, cache_present):
    cache = tmp_path / 'derived-cache'
    sim, http = real_sim(tmp_path / 'society', cache, real_retrieval)
    try:
        sim._prepare_paper_index(1)
        expected_tensor = sim.rag.document_embeddings.clone()
        expected_identity = sim.rag.document_identity
        files = list(cache.glob('embeddings-*.pt'))
        assert len(files) == 1
        identity_name = files[0].name
        original_hash = file_sha256(files[0])
        sim.rag.document_status.loc[0, 'status'] = 'accept'
        sim.rag.document_status.loc[1, 'status'] = 'submitted'
        statuses = sim.rag.document_status.copy(deep=True)
        sim.rag.document_embeddings = None
        sim.rag.sentence_transformer_model = None
        encoded_before = len(real_retrieval)
        if not cache_present:
            files[0].unlink()  # only the exact temporary test embedding cache
        rng = capture_rng()
        sim._prepare_paper_index(2)
        assert capture_rng() == rng and not http
        assert sim.llm.response_cache.committed_count() == 0
        pd.testing.assert_frame_equal(sim.rag.document_status, statuses)
        assert sim.rag.document_identity == expected_identity
        assert torch.equal(sim.rag.document_embeddings, expected_tensor)
        assert tensor_hash(sim.rag.document_embeddings) == tensor_hash(expected_tensor)
        assert [p.name for p in cache.glob('embeddings-*.pt')] == [identity_name]
        assert len(real_retrieval) == encoded_before + (not cache_present)
        if cache_present:
            assert file_sha256(files[0]) == original_hash
        result = sim.rag.batch_retrieve(['replication measurement'], retrieval_type='submission')
        assert result['topk_indices'].shape == (1, 8)
        assert set(result['topk_indices'][0]) == set(range(8, 16))
        assert not http
    finally:
        sim.llm.response_cache.close()


@pytest.mark.parametrize('preload', [True, False])
def test_real_native_cold_resume_matches_continuous_requests_and_scientific_state(tmp_path, real_retrieval, monkeypatch, preload):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    reference, full_calls = real_sim(tmp_path / 'continuous', tmp_path / 'cache', real_retrieval)
    reference.run()
    expected_state = original_science_at_three(reference)
    expected_requests = [p for _, p in full_calls]
    expected_counts = Counter(ctx[1] for (ctx, _, _), p in full_calls)
    assert expected_counts[1] == 29  # 4 directions/intents/submissions/apps, 12 reviews, 1 grant evaluation
    expected_index = tensor_hash(reference.rag.document_embeddings)
    reference.llm.response_cache.close()
    seed()
    stopped, before_calls = real_sim(tmp_path / 'resumed', tmp_path / 'cache', real_retrieval)
    original = stopped.checkpoint_callback
    def boundary(path):
        original(path)
        if stopped.native_system.last_year == 1:
            raise PortableStop('cold restart at completed year1')
    stopped.checkpoint_callback = boundary
    with pytest.raises(PortableStop):
        stopped.run()
    assert before_calls and {ctx[1] for (ctx, _, _), p in before_calls} == {1}
    year1_responses = stopped.llm.response_cache.committed_count()
    assert year1_responses == len(before_calls)
    stopped.llm.response_cache.close()
    seed()
    resumed, after_calls = real_sim(tmp_path / 'resumed', tmp_path / 'cache', real_retrieval, preload=preload)
    assert resumed.rag.document_embeddings is None
    assert bool(resumed.rag.documents) == preload
    resumed.run()
    assert all(ctx[1] > 1 for (ctx, _, _), p in after_calls)
    assert [p for _, p in before_calls + after_calls] == expected_requests
    assert Counter(ctx[1] for (ctx, _, _), p in before_calls + after_calls) == expected_counts
    assert resumed.llm.response_cache.committed_count() == len(expected_requests)
    assert tensor_hash(resumed.rag.document_embeddings) == expected_index
    assert original_science_at_three(resumed) == expected_state
    resumed.llm.response_cache.close()


def original_science_at_three(sim):
    # Same scientific inventory/normalization as the established six-year helper,
    # against a genuinely three-year checkpoint (including full agent/RNG state).
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from pathlib import Path
    state = read_portable_checkpoint(Path(sim.output_dir) / 'portable_checkpoint_year_3.json.gz')
    ignored = {'timestamp', 'submission_time', 'review_time', 'decision_time', 'elapsed_seconds'}
    def normalize(value):
        if isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items() if k not in ignored}
        if isinstance(value, (list, tuple)): return [normalize(v) for v in value]
        if isinstance(value, set): return sorted(normalize(v) for v in value)
        if hasattr(value, 'to_dict'): return normalize(value.to_dict())
        if isinstance(value, FundingProgram): return normalize(vars(value))
        return value
    state['portable'].pop('outputs')
    state['paper_tracker'].pop('output_dir')
    state.pop('cost_experiment_binding', None)
    return normalize(state)
