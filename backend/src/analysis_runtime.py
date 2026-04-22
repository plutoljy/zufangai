"""
Shared analysis event stream used by direct SSE and background queue workers.
"""

from __future__ import annotations

import asyncio
import copy
import json
from typing import Any, AsyncGenerator, Callable, Optional

from agents.cat_reporter import CatReporter, split_report_paragraphs
from agents.beaver_calculator import BeaverCalculator
from agents.dog_retriever import DogRetriever
from agents.owl_analyst import OwlAnalyst
from prompts import dog_retriever_prompt
from streaming import stream_agent_step

# 全局默认实例（用于向后兼容）
owl = OwlAnalyst()
dog = DogRetriever()
beaver = BeaverCalculator()
cat = CatReporter()

# These are soft thresholds used for progress messaging only.
# We no longer fail the analysis just because a step takes longer than expected.
AGENT_TIMEOUTS = {
    "owl": 35.0,
    "dog_retrieve": 20.0,
    "dog_format": 20.0,
    "beaver_deterministic": 10.0,
    "beaver_refine": 20.0,
    "cat": 30.0,
}
HEARTBEAT_INTERVAL_S = 5.0


def _log_risk_snapshot(label: str, state: dict[str, Any]) -> None:
    risk_items = state.get("risk_items", [])
    source_counts: dict[str, int] = {}
    for item in risk_items:
        source = item.get("source", "llm")
        source_counts[source] = source_counts.get(source, 0) + 1
    print(
        f"[risk_snapshot] {label}: "
        f"risk_items={len(risk_items)} source_counts={source_counts}"
    )


async def _run_step(
    *,
    agent: str,
    step: str,
    message: str,
    state: dict[str, Any],
    func: Callable[[dict[str, Any]], dict[str, Any]],
    timeout_s: float,
    fallback_timeout_s: float | None = None,
    fallback_func: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    next_state = state
    failed = False

    async for envelope in stream_agent_step(
        agent=agent,
        step=step,
        message=message,
        state=state,
        func=func,
        timeout_s=timeout_s,
        heartbeat_interval_s=HEARTBEAT_INTERVAL_S,
        fallback_timeout_s=fallback_timeout_s,
        fallback_func=fallback_func,
    ):
        result = envelope.pop("_result", None)
        failed = envelope.pop("_failed", False)
        if result is not None:
            next_state = result
        yield {**envelope, "_state": next_state, "_failed": failed}


def _owl_step(state: dict[str, Any]) -> dict[str, Any]:
    owl_instance = owl

    result = owl_instance.analyze(state["contract_text"])
    return {
        **state,
        "entities": result.get("entities", {}),
        "risk_items": result.get("risk_items", []),
        "is_template": False,  # 强制禁用模板检测，确保所有 Agent 都被调用
        "template_reason": result.get("template_reason"),
        "personalized_summary": result.get("personalized_summary"),
    }


def _owl_fallback_step(state: dict[str, Any]) -> dict[str, Any]:
    owl_instance = owl

    result = owl_instance._build_fallback_result(state["contract_text"])
    return {
        **state,
        "entities": result.get("entities", {}),
        "risk_items": result.get("risk_items", []),
        "is_template": False,  # 强制禁用模板检测，确保所有 Agent 都被调用
        "template_reason": result.get("template_reason"),
        "personalized_summary": result.get("personalized_summary"),
    }


def _dog_retrieve_step(state: dict[str, Any]) -> dict[str, Any]:
    try:
        legal_docs, cases = dog.retrieve_sources(
            state.get("risk_items", []),
            state.get("location", "beijing"),
        )
    except Exception as exc:
        print(f"Dog Retriever retrieve_sources failed: {exc}")
        legal_docs = dog_retriever_prompt.MOCK_LEGAL_DOCS
        cases = dog_retriever_prompt.MOCK_CASES
    return {**state, "_dog_legal_docs": legal_docs, "_dog_cases": cases}


def _dog_format_step(state: dict[str, Any]) -> dict[str, Any]:
    legal_docs = state.get("_dog_legal_docs", [])
    cases = state.get("_dog_cases", [])
    try:
        formatted = dog.format_results(
            state.get("risk_items", []),
            legal_docs,
            cases,
        )
    except Exception as exc:
        print(f"Dog Retriever format_results failed: {exc}")
        formatted = dog._build_fallback_result(legal_docs, cases)
    return {
        **state,
        "legal_references": formatted.get("legal_references", []),
        "case_references": formatted.get("case_references", []),
        "suggestions": formatted.get("suggestions", []),
        "negotiation_tips": formatted.get("negotiation_tips", []),
    }


def _dog_format_fallback_step(state: dict[str, Any]) -> dict[str, Any]:
    legal_docs = state.get("_dog_legal_docs", [])
    cases = state.get("_dog_cases", [])
    formatted = dog._build_fallback_result(legal_docs, cases)
    return {
        **state,
        "legal_references": formatted.get("legal_references", []),
        "case_references": formatted.get("case_references", []),
        "suggestions": formatted.get("suggestions", []),
        "negotiation_tips": formatted.get("negotiation_tips", []),
    }


def _beaver_deterministic_step(state: dict[str, Any]) -> dict[str, Any]:
    print(
        "[Beaver Calculator] starting deterministic calculation "
        f"(contract_text_len={len(state.get('contract_text', ''))}, "
        f"use_llm={beaver.use_llm})"
    )
    calculations = beaver.calculate_deterministic(
        state.get("entities", {}),
        state.get("location", "beijing"),
        contract_text=state.get("contract_text"),
    )
    calculations.setdefault("analysis_metadata", {})
    calculations["analysis_metadata"].update(
        {
            "mode": "deterministic",
            "llm_attempted": False,
            "llm_success": False,
        }
    )
    return {**state, "calculations": calculations}


def _beaver_refine_step(state: dict[str, Any]) -> dict[str, Any]:
    if not beaver.use_llm:
        print("[Beaver Calculator] skipping LLM refinement because use_llm=False")
        calculations = dict(state.get("calculations", {}))
        calculations.setdefault("analysis_metadata", {})
        calculations["analysis_metadata"].update(
            {
                "mode": "deterministic",
                "llm_attempted": False,
                "llm_success": False,
                "llm_error": "use_llm=False",
            }
        )
        return {**state, "calculations": calculations}

    contract_text = state.get("contract_text", "")
    location = state.get("location", "beijing")

    if contract_text.strip():
        try:
            print(
                "[Beaver Calculator] starting full-text LLM analysis "
                f"(contract_text_len={len(contract_text)})"
            )
            calculations = beaver.analyze_from_text(contract_text, location)
            calculations.setdefault("analysis_metadata", {})
            calculations["analysis_metadata"].update(
                {
                    "mode": "llm_full_text",
                    "llm_attempted": True,
                    "llm_success": True,
                }
            )
            print("[Beaver Calculator] full-text LLM analysis completed successfully")
            return {**state, "calculations": calculations}
        except Exception as exc:
            print(
                "[Beaver Calculator] full-text analysis failed, "
                f"falling back to refinement: {exc}"
            )

    try:
        print(
            "[Beaver Calculator] starting LLM refinement "
            f"(contract_text_len={len(contract_text)})"
        )
        calculations = beaver.refine_with_llm(
            state.get("entities", {}),
            location,
            state.get("calculations", {}),
            contract_text,
        )
        calculations.setdefault("analysis_metadata", {})
        calculations["analysis_metadata"].update(
            {
                "mode": "llm_refine",
                "llm_attempted": True,
                "llm_success": True,
            }
        )
        print("[Beaver Calculator] LLM refinement completed successfully")
    except Exception as exc:
        print(f"Beaver Calculator refine_with_llm failed: {exc}")
        calculations = dict(state.get("calculations", {}))
        calculations.setdefault("analysis_metadata", {})
        calculations["analysis_metadata"].update(
            {
                "mode": "deterministic_fallback",
                "llm_attempted": True,
                "llm_success": False,
                "llm_error": str(exc),
            }
        )
        return {**state, "calculations": calculations}
    return {**state, "calculations": calculations}


def _beaver_refine_fallback_step(state: dict[str, Any]) -> dict[str, Any]:
    return state


def _cat_step(state: dict[str, Any]) -> dict[str, Any]:
    report = cat.generate_report(
        entities=state.get("entities", {}),
        risk_items=state.get("risk_items", []),
        legal_references=state.get("legal_references", []),
        case_references=state.get("case_references", []),
        calculations=state.get("calculations", {}),
        is_template=False,  # 强制使用真实分析结果，不使用模板
    )
    return {**state, "report": report}


async def run_contract_analysis_events(
    *,
    contract_id: str,
    contract_text: str,
    location: str,
    user_id: Optional[str] = None,
) -> AsyncGenerator[dict[str, Any], None]:
    yield {"event": "analysis_started", "data": {}}
    await asyncio.sleep(0.05)

    state: dict[str, Any] = {
        "contract_text": contract_text,
        "location": location,
        "user_id": user_id,  # 添加 user_id 到 state
    }

    async for envelope in _run_step(
        agent="owl",
        step="extract_entities",
        message="正在提取合同实体与风险条款...",
        state=state,
        func=_owl_step,
        timeout_s=AGENT_TIMEOUTS["owl"],
    ):
        state = envelope["_state"]
        failed = envelope["_failed"]
        yield {"event": envelope["event"], "data": envelope["data"]}
    if failed:
        return

    yield {
        "event": "owl_analysis",
        "data": {
            "data": {
                "entities": state.get("entities", {}),
                "risk_count": len(state.get("risk_items", [])),
            }
        },
    }
    _log_risk_snapshot("after_owl", state)
    await asyncio.sleep(0.05)

    if state.get("is_template"):
        yield {
            "event": "template_detected",
            "data": {
                "message": "检测到这是一个合同模板，将只分析条款风险",
                "reason": state.get("template_reason"),
            },
        }
        yield {"event": "progress", "data": {"message": "正在生成模板分析报告..."}}
    else:
        yield {"event": "progress", "data": {"message": "正在检索法律文档..."}}

        async for envelope in _run_step(
            agent="dog",
            step="retrieve_sources",
            message="正在检索法律文档...",
            state=state,
            func=_dog_retrieve_step,
            timeout_s=AGENT_TIMEOUTS["dog_retrieve"],
        ):
            state = envelope["_state"]
            failed = envelope["_failed"]
            yield {"event": envelope["event"], "data": envelope["data"]}
        if failed:
            return

        async for envelope in _run_step(
            agent="dog",
            step="format_references",
            message="正在整理法律依据与案例...",
            state=state,
            func=_dog_format_step,
            timeout_s=AGENT_TIMEOUTS["dog_format"],
        ):
            state = envelope["_state"]
            failed = envelope["_failed"]
            yield {"event": envelope["event"], "data": envelope["data"]}
        if failed:
            return

        yield {
            "event": "dog_retrieval",
            "data": {
                "data": {
                    "legal_docs": len(state.get("legal_references", [])),
                    "cases": len(state.get("case_references", [])),
                }
            },
        }
        _log_risk_snapshot("after_dog", state)
        await asyncio.sleep(0.05)

        yield {"event": "progress", "data": {"message": "正在核算押金与费用..."}}

        async for envelope in _run_step(
            agent="beaver",
            step="calculate_deterministic",
            message="正在进行基础费用核算...",
            state=state,
            func=_beaver_deterministic_step,
            timeout_s=AGENT_TIMEOUTS["beaver_deterministic"],
        ):
            state = envelope["_state"]
            failed = envelope["_failed"]
            yield {"event": envelope["event"], "data": envelope["data"]}
        if failed:
            return

        async for envelope in _run_step(
            agent="beaver",
            step="refine_calculation",
            message="正在用模型复核费用结论...",
            state=state,
            func=_beaver_refine_step,
            timeout_s=AGENT_TIMEOUTS["beaver_refine"],
        ):
            state = envelope["_state"]
            failed = envelope["_failed"]
            yield {"event": envelope["event"], "data": envelope["data"]}
        if failed:
            return

        yield {
            "event": "beaver_calculation",
            "data": {
                "data": {
                    "compliant": state.get("calculations", {})
                    .get("deposit_check", {})
                    .get("compliant", False),
                    "mode": state.get("calculations", {})
                    .get("analysis_metadata", {})
                    .get("mode"),
                    "llm_attempted": state.get("calculations", {})
                    .get("analysis_metadata", {})
                    .get("llm_attempted"),
                    "llm_success": state.get("calculations", {})
                    .get("analysis_metadata", {})
                    .get("llm_success"),
                    "llm_error": state.get("calculations", {})
                    .get("analysis_metadata", {})
                    .get("llm_error"),
                }
            },
        }
        _log_risk_snapshot("after_beaver", state)
        await asyncio.sleep(0.05)

        yield {"event": "progress", "data": {"message": "正在生成分析报告..."}}

    async for envelope in _run_step(
        agent="cat",
        step="generate_report",
        message="正在生成分析报告...",
        state=state,
        func=_cat_step,
        timeout_s=AGENT_TIMEOUTS["cat"],
    ):
        state = envelope["_state"]
        failed = envelope["_failed"]
        yield {"event": envelope["event"], "data": envelope["data"]}
    if failed:
        return

    paragraphs = split_report_paragraphs(
        state.get("report", {}).get("report_markdown", "")
    )
    for index, paragraph in enumerate(paragraphs):
        yield {
            "event": "report_paragraph",
            "data": {
                "agent": "cat",
                "index": index,
                "total": len(paragraphs),
                "paragraph": paragraph,
            },
        }
        await asyncio.sleep(0.03)

    yield {
        "event": "cat_report",
        "data": {"data": state.get("report", {}).get("summary", {})},
    }
    _log_risk_snapshot("after_cat", state)
    await asyncio.sleep(0.05)

    yield {
        "event": "analysis_complete",
        "data": {"contract_id": contract_id, "state": copy.deepcopy(state)},
    }
