import importlib
import sys
import types
from pathlib import Path

import numpy as np


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def load_vectorize(monkeypatch, model_cls):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = model_cls
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    sys.modules.pop("knowledge.vectorize", None)
    return importlib.import_module("knowledge.vectorize")


def test_vector_store_uses_cached_local_model_and_dimension_384(monkeypatch):
    created_models = []

    class FakeModel:
        def __init__(self, model_name):
            created_models.append(model_name)

        def encode(self, texts, **_kwargs):
            return np.zeros((len(texts), 384), dtype=np.float32)

    vectorize = load_vectorize(monkeypatch, FakeModel)

    store_a = vectorize.VectorStore()
    store_b = vectorize.VectorStore()

    assert store_a.dimension == 384
    assert created_models == ["paraphrase-multilingual-MiniLM-L12-v2"]
    assert store_a.model is store_b.model
    assert not hasattr(store_a, "client")


def test_embed_texts_retries_and_returns_float32_embeddings(monkeypatch):
    class FakeModel:
        def __init__(self, _model_name):
            self.calls = 0

        def encode(self, texts, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary failure")
            return [[float(i + 1)] * 384 for i, _ in enumerate(texts)]

    vectorize = load_vectorize(monkeypatch, FakeModel)
    monkeypatch.setattr(vectorize.time, "sleep", lambda _seconds: None)

    store = vectorize.VectorStore()
    embeddings = store.embed_texts(["甲", "乙"], max_retries=2)

    assert embeddings.dtype == np.float32
    assert embeddings.shape == (2, 384)
    assert embeddings[0, 0] == 1.0
    assert embeddings[1, 0] == 2.0
    assert store.model.calls == 2
