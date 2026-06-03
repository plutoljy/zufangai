"""
Session-scoped follow-up chat helper for workspace agents.
"""

from __future__ import annotations

import json
from typing import Any

from config import settings
from utils.dynamic_llm_client import DynamicLLMClient
from utils.llm_client import LLMClient


AGENT_PROMPTS: dict[str, str] = {
    "owl": (
        "你是 Owl 条款分析师。只围绕当前合同条款风险作答，解释风险点、"
        "法律逻辑、谈判重点，不要脱离合同事实做泛泛建议。"
    ),
    "dog": (
        "你是 Dog 法律检索师。只围绕当前合同对应的法律依据、案例线索、"
        "协商建议作答，优先引用报告里已有依据。"
    ),
    "beaver": (
        "你是 Beaver 费用核算师。只围绕当前合同里的租金、押金、水电燃气、"
        "隐藏费用和计算逻辑作答，明确区分已写明的信息与需补充确认的信息。"
    ),
}


def _build_client(
    user_id: str | None = None, access_token: str | None = None, agent_key: str = "owl"
) -> LLMClient | None:
    if user_id and access_token:
        try:
            dynamic_client = DynamicLLMClient(access_token=access_token)
            config = dynamic_client.get_client_config_for_agent(user_id, agent_key)
            print(
                f"[AgentChat] {agent_key}: using custom config "
                f"{config.provider_name}/{config.model_name}"
            )
            return LLMClient(
                api_key=config.api_key,
                base_url=config.base_url or "",
                model=config.model_name,
                api_type=config.api_type,
                temperature=0.2,
                timeout=90,
                agent_name=f"chat_{agent_key}",
            )
        except Exception as exc:
            print(f"[AgentChat] {agent_key}: custom config failed ({exc}), falling back to default")

    if settings.claude_api_key_sonnet:
        return LLMClient(
            api_key=settings.claude_api_key_sonnet,
            base_url=settings.claude_base_url,
            model=settings.claude_model_sonnet,
            api_type="claude",
            temperature=0.2,
            timeout=90,
            agent_name=f"chat_{agent_key}",
        )
    if settings.qwen_api_key:
        return LLMClient(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            model=settings.qwen_model,
            api_type="qwen",
            temperature=0.2,
            timeout=90,
            agent_name=f"chat_{agent_key}",
        )
    return None


def _compact_report_context(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": report.get("summary", {}),
        "risk_items": report.get("risk_items", [])[:8],
        "legal_references": report.get("legal_references", [])[:4],
        "case_references": report.get("case_references", [])[:4],
        "suggestions": report.get("suggestions", [])[:4],
        "calculations": report.get("calculations", {}),
        "report_excerpt": (report.get("report_markdown", "") or "")[:2000],
    }


def _format_messages(messages: list[dict[str, str]]) -> str:
    if not messages:
        return "无历史对话。"

    lines: list[str] = []
    for message in messages[-6:]:
        role = "用户" if message.get("role") == "user" else "助手"
        content = (message.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "无历史对话。"


def _build_fallback_reply(agent_key: str, report: dict[str, Any], question: str) -> str:
    if agent_key == "beaver":
        calculations = report.get("calculations", {})
        utilities = calculations.get("utilities_check", {})
        highlighted = []
        for utility_key in ("water", "electricity", "gas"):
            detail = utilities.get(utility_key, {})
            issue = detail.get("issue")
            if issue:
                highlighted.append(issue)
        if highlighted:
            return f"基于当前费用分析，先重点看这几项：{'；'.join(highlighted)}。你刚问的是“{question}”，如果你愿意，我可以继续按收费依据、是否超标、和怎么跟房东沟通三部分给你拆开说。"

    risk_items = report.get("risk_items", [])
    if risk_items:
        first_issue = risk_items[0].get("issue") or "当前合同存在风险项"
        return f"我会基于当前合同继续回答。先给你一个结论：{first_issue}。你刚问的是“{question}”，我建议结合当前报告里的风险点继续追问具体条款或应对话术。"

    return f"我会继续基于这份合同回答你的问题。你刚问的是“{question}”，当前报告里没有更多结构化结论时，我建议先确认具体条款原文或补充你最担心的场景。"


def generate_agent_chat_reply(
    *,
    agent_key: str,
    contract_text: str,
    report: dict[str, Any],
    messages: list[dict[str, str]],
    question: str,
    user_id: str | None = None,
    access_token: str | None = None,
) -> str:
    if agent_key not in AGENT_PROMPTS:
        raise ValueError(f"Unsupported agent: {agent_key}")

    client = _build_client(user_id, access_token, agent_key)
    if client is None:
        return _build_fallback_reply(agent_key, report, question)

    system_prompt = (
        f"{AGENT_PROMPTS[agent_key]}\n"
        "回答要求：\n"
        "1. 只基于给定合同与报告上下文回答。\n"
        "2. 结论先行，随后补一句原因。\n"
        "3. 如果信息不足，明确指出缺了什么，不要编造。\n"
        "4. 控制在 180 中文字以内。"
    )

    user_prompt = (
        "当前合同原文（必要片段）:\n"
        f"{contract_text[:6000]}\n\n"
        "当前报告摘要:\n"
        f"{json.dumps(_compact_report_context(report), ensure_ascii=False)}\n\n"
        "最近对话:\n"
        f"{_format_messages(messages)}\n\n"
        f"当前用户问题: {question}"
    )

    return client.call_with_prompts(system_prompt=system_prompt, user_prompt=user_prompt).strip()
