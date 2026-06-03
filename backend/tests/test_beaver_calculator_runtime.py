from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def test_beaver_calculator_raises_when_vectorstore_load_crashes():
    fake_retriever_module = types.ModuleType("knowledge.retriever")

    def broken_retriever():
        raise RuntimeError("faiss index missing")

    fake_retriever_module.get_retriever = broken_retriever
    original_module = sys.modules.get("knowledge.retriever")
    sys.modules["knowledge.retriever"] = fake_retriever_module

    try:
        from agents.beaver_calculator import BeaverCalculator

        with pytest.raises(RuntimeError, match="faiss index missing"):
            BeaverCalculator()
    finally:
        if original_module is None:
            sys.modules.pop("knowledge.retriever", None)
        else:
            sys.modules["knowledge.retriever"] = original_module
