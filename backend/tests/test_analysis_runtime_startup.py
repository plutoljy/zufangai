from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def test_analysis_runtime_import_does_not_instantiate_agents():
    touched: list[str] = []
    saved_modules = {
        name: sys.modules.get(name)
        for name in [
            "analysis_runtime",
            "agents.owl_analyst",
            "agents.dog_retriever",
            "agents.beaver_calculator",
            "agents.cat_reporter",
            "prompts",
            "streaming",
            "utils.dynamic_llm_client",
        ]
    }

    def agent_class(name: str):
        class Agent:
            def __init__(self, *args, **kwargs):
                touched.append(name)
                raise AssertionError(f"{name} was instantiated during import")

        return Agent

    owl_module = types.ModuleType("agents.owl_analyst")
    owl_module.OwlAnalyst = agent_class("owl")
    dog_module = types.ModuleType("agents.dog_retriever")
    dog_module.DogRetriever = agent_class("dog")
    beaver_module = types.ModuleType("agents.beaver_calculator")
    beaver_module.BeaverCalculator = agent_class("beaver")
    cat_module = types.ModuleType("agents.cat_reporter")
    cat_module.CatReporter = agent_class("cat")
    cat_module.split_report_paragraphs = lambda markdown: [markdown]
    prompts_module = types.ModuleType("prompts")
    prompts_module.dog_retriever_prompt = ""
    streaming_module = types.ModuleType("streaming")
    streaming_module.stream_agent_step = None
    dynamic_client_module = types.ModuleType("utils.dynamic_llm_client")
    dynamic_client_module.DynamicLLMClient = object

    sys.modules.update(
        {
            "agents.owl_analyst": owl_module,
            "agents.dog_retriever": dog_module,
            "agents.beaver_calculator": beaver_module,
            "agents.cat_reporter": cat_module,
            "prompts": prompts_module,
            "streaming": streaming_module,
            "utils.dynamic_llm_client": dynamic_client_module,
        }
    )

    try:
        importlib.import_module("analysis_runtime")
    finally:
        for name, module in saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    assert touched == []
