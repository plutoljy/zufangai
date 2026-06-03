from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


import pytest


def test_dog_retriever_raises_when_vectorstore_load_crashes(monkeypatch):
    import agents.dog_retriever as dog_retriever

    def broken_retriever():
        raise RuntimeError("faiss index missing")

    monkeypatch.setattr(dog_retriever, "get_retriever", broken_retriever)

    with pytest.raises(RuntimeError, match="faiss index missing"):
        dog_retriever.DogRetriever()
