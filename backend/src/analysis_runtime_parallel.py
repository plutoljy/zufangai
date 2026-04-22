"""
并行执行版本的分析流程
架构: Owl + Dog 并行 → Beaver → Cat
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Callable, Optional

from agents.cat_reporter import CatReporter, split_report_paragraphs
from agents.beaver_calculator import BeaverCalculator
from agents.dog_retriever import DogRetriever
from agents.owl_analyst import OwlAnalyst
from prompts import dog_retriever_prompt
from streaming import stream_agent_step

# 全局默认实例
owl = OwlAnalyst()
dog = DogRetriever()
beaver = BeaverCalculator()
cat = CatReporter()

# 超时配置
AGENT_TIMEOUTS = {
    "owl": 35.0,
    "dog_analyze": 30.0,  # Dog 独立分析
    "beaver": 40.0,  # Beaver 完整分析（包含隐藏费用）
    "cat": 30.0,
}
HEARTBEAT_INTERVAL_S = 5.0


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
    """Owl Agent: 风险识别"""
    owl_instance = owl

    result = owl_instance.analyze(state["contract_text"])
    return {
        **state,
        "owl_entities": result.get("entities", {}),
        "owl_risk_items": result.get("risk_items", []),
        "is_template": result.get("is_template", False),
        "template_reason": result.get("template_reason"),
        "personalized_summary": result.get("personalized_summary"),
    }


def _dog_step(state: dict[str, Any]) -> dict[str, Any]:
    """Dog Agent: 法律检索（基于 Owl 的风险识别）"""
    risk_items = state.get("owl_risk_items", [])
    location = state.get("location", "beijing")

    # 不再捕获异常，让错误直接抛出
    result = dog.retrieve(risk_items, location)
    return {
        **state,
        "dog_legal_references": result.get("legal_references", []),
        "dog_case_references": result.get("case_references", []),
        "dog_suggestions": result.get("suggestions", []),
        "dog_negotiation_tips": result.get("negotiation_tips", []),
    }


def _beaver_step(state: dict[str, Any]) -> dict[str, Any]:
    """Beaver Agent: 财务分析 + 隐藏费用识别"""
    contract_text = state.get("contract_text", "")
    location = state.get("location", "beijing")

    # 不再捕获异常，让错误直接抛出
    result = beaver.analyze_from_text(contract_text, location)
    return {
        **state,
        "beaver_deposit_check": result.get("deposit_check", {}),
        "beaver_utilities_check": result.get("utilities_check", {}),
        "beaver_hidden_costs": result.get("hidden_costs", []),
        "beaver_ambiguous_clauses": result.get("ambiguous_clauses", {}),
        "beaver_total_cost": result.get("total_cost_analysis", {}),
        "beaver_explicit_values": result.get("explicit_values", {}),
        "beaver_implicit_values": result.get("implicit_values", {}),
    }


def _cat_step(state: dict[str, Any]) -> dict[str, Any]:
    """Cat Agent: 汇总三个 Agent 的报告"""
    owl_report = {
        "entities": state.get("owl_entities", {}),
        "risk_items": state.get("owl_risk_items", []),
    }

    dog_report = {
        "legal_references": state.get("dog_legal_references", []),
        "case_references": state.get("dog_case_references", []),
        "suggestions": state.get("dog_suggestions", []),
        "negotiation_tips": state.get("dog_negotiation_tips", []),
    }

    beaver_report = {
        "deposit_check": state.get("beaver_deposit_check", {}),
        "utilities_check": state.get("beaver_utilities_check", {}),
        "hidden_costs": state.get("beaver_hidden_costs", {}),
        "ambiguous_clauses": state.get("beaver_ambiguous_clauses", {}),
        "total_cost_analysis": state.get("beaver_total_cost", {}),
    }

    report = cat.generate_comprehensive_report(
        owl_report=owl_report,
        dog_report=dog_report,
        beaver_report=beaver_report,
        is_template=False,  # 强制使用真实分析结果，不使用模板
    )

    # 确保所有 Agent 的数据都被正确映射到最终结果
    return {
        **state,
        "report": report,
        # Owl 数据
        "risk_items": state.get("owl_risk_items", []),
        "entities": state.get("owl_entities", {}),
        # Dog 数据
        "legal_references": state.get("dog_legal_references", []),
        "case_references": state.get("dog_case_references", []),
        "suggestions": state.get("dog_suggestions", []),
        "negotiation_tips": state.get("dog_negotiation_tips", []),
        # Beaver 数据
        "calculations": {
            "deposit_check": state.get("beaver_deposit_check", {}),
            "utilities_check": state.get("beaver_utilities_check", {}),
            "hidden_costs": state.get("beaver_hidden_costs", []),
            "ambiguous_clauses": state.get("beaver_ambiguous_clauses", {}),
            "total_cost_analysis": state.get("beaver_total_cost", {}),
            "explicit_values": state.get("beaver_explicit_values", {}),
            "implicit_values": state.get("beaver_implicit_values", {}),
        },
    }


async def run_parallel_analysis_events(
    *,
    contract_id: str,
    contract_text: str,
    location: str,
    user_id: Optional[str] = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    并行执行分析流程:
    1. Owl + Dog 并行执行
    2. Beaver 独立执行
    3. Cat 汇总报告
    """
    yield {"event": "analysis_started", "data": {}}
    await asyncio.sleep(0.05)

    state: dict[str, Any] = {
        "contract_text": contract_text,
        "location": location,
        "user_id": user_id,
    }

    # ========== Phase 1: Owl + Dog 并行执行 ==========
    yield {"event": "progress", "data": {"message": "正在并行分析合同（Owl + Dog）..."}}

    # 创建两个并行任务
    owl_task = asyncio.create_task(_run_parallel_agent(
        agent="owl",
        step="analyze_risks",
        message="Owl: 正在识别风险条款...",
        state=state,
        func=_owl_step,
        timeout_s=AGENT_TIMEOUTS["owl"],
    ))

    dog_task = asyncio.create_task(_run_parallel_agent(
        agent="dog",
        step="analyze_legal",
        message="Dog: 正在检索法律依据...",
        state=state,
        func=_dog_step,
        timeout_s=AGENT_TIMEOUTS["dog_analyze"],
    ))

    # 等待两个任务完成
    owl_result, dog_result = await asyncio.gather(owl_task, dog_task)

    # 合并结果
    state.update(owl_result)
    state.update(dog_result)

    yield {
        "event": "parallel_complete",
        "data": {
            "owl_risks": len(state.get("owl_risk_items", [])),
            "dog_laws": len(state.get("dog_legal_references", [])),
        },
    }
    await asyncio.sleep(0.05)

    # ========== Phase 2: Beaver 独立执行 ==========
    yield {"event": "progress", "data": {"message": "正在分析财务和隐藏费用（Beaver）..."}}

    async for envelope in _run_step(
        agent="beaver",
        step="analyze_finance",
        message="Beaver: 正在分析财务和隐藏费用...",
        state=state,
        func=_beaver_step,
        timeout_s=AGENT_TIMEOUTS["beaver"],
    ):
        state = envelope["_state"]
        failed = envelope["_failed"]
        yield {"event": envelope["event"], "data": envelope["data"]}

    if failed:
        return

    yield {
        "event": "beaver_complete",
        "data": {
            "hidden_costs": len(state.get("beaver_hidden_costs", {}).get("items", [])),
            "ambiguous_clauses": len(state.get("beaver_ambiguous_clauses", {}).get("items", [])),
        },
    }
    await asyncio.sleep(0.05)

    # ========== Phase 3: Cat 汇总报告 ==========
    yield {"event": "progress", "data": {"message": "正在生成综合报告（Cat）..."}}

    async for envelope in _run_step(
        agent="cat",
        step="generate_report",
        message="Cat: 正在汇总三个 Agent 的分析结果...",
        state=state,
        func=_cat_step,
        timeout_s=AGENT_TIMEOUTS["cat"],
    ):
        state = envelope["_state"]
        failed = envelope["_failed"]
        yield {"event": envelope["event"], "data": envelope["data"]}

    if failed:
        return

    # 输出报告段落
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
    await asyncio.sleep(0.05)

    yield {
        "event": "analysis_complete",
        "data": {"contract_id": contract_id, "state": state},
    }


async def _run_parallel_agent(
    *,
    agent: str,
    step: str,
    message: str,
    state: dict[str, Any],
    func: Callable[[dict[str, Any]], dict[str, Any]],
    timeout_s: float,
) -> dict[str, Any]:
    """
    并行执行单个 Agent，返回结果状态
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(func, state),
            timeout=timeout_s
        )
        return result
    except asyncio.TimeoutError:
        print(f"{agent} 执行超时 ({timeout_s}s)")
        return state
    except Exception as exc:
        print(f"{agent} 执行失败: {exc}")
        return state
