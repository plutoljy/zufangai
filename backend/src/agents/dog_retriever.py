"""
Dog Retriever Agent
Responsible for legal reference retrieval, case matching, and negotiation tips.
"""

from __future__ import annotations

import json
import os
import sys
from math import ceil
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from ai_provider_manager import ResolvedAgentConfig
from knowledge.retriever import get_retriever
from prompts import dog_retriever_prompt
from utils.agent_config import apply_llm_config
from utils.json_payload import extract_json_payload
from utils.llm_client import LLMClient


class DogRetriever:
    """Retrieve legal references and case support for identified risks."""

    def __init__(self, llm_config: ResolvedAgentConfig | None = None):
        # 优先使用 Claude Sonnet API（速度优先）
        if settings.claude_api_key_sonnet:
            self.api_key = settings.claude_api_key_sonnet
            self.base_url = settings.claude_base_url
            self.model = settings.claude_model_sonnet
            self.temperature = 0.1
            self.timeout = 180
            self.use_llm = True
            self.api_type = "claude"
            self.chunk_size = 800  # 统一分块大小
            print(f"[OK] Dog Retriever: 使用 Claude {self.model} 模型 (temperature={self.temperature})")
        elif settings.qwen_api_key:
            self.api_key = settings.qwen_api_key
            self.base_url = settings.qwen_base_url
            self.model = settings.qwen_model
            self.temperature = 0.1
            self.timeout = 180
            self.use_llm = True
            self.api_type = "qwen"
            self.chunk_size = 1000
            print(f"[OK] Dog Retriever: 使用千问 {settings.qwen_model} 模型 (temperature={self.temperature})")
        else:
            print("[WARN] Dog Retriever: 未配置 API Key，使用 fallback 模式")
            self.api_key = None
            self.use_llm = False
            self.api_type = None
            self.chunk_size = 1000

        if llm_config is not None:
            apply_llm_config(self, llm_config)
            self.temperature = 0.1
            self.timeout = 180
            self.chunk_size = 800 if llm_config.api_type == "claude" else 1000
            print(
                f"[OK] Dog Retriever: using user provider "
                f"{llm_config.provider_name}/{llm_config.model_name}"
            )

        self._llm: LLMClient | None = None

        self.retriever = get_retriever()
        self.use_rag = True
        print("[OK] Dog Retriever: knowledge base loaded")

    @property
    def llm(self) -> LLMClient | None:
        if self._llm is None and self.use_llm and self.api_key:
            self._llm = LLMClient(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                api_type=self.api_type,
                temperature=self.temperature,
                timeout=self.timeout,
                agent_name="dog",
            )
        return self._llm

    def retrieve(self, risk_items: List[Dict], location: str = "beijing") -> Dict:
        if not risk_items:
            raise ValueError("Dog Retriever: 没有风险项，无法进行检索")

        if not self.use_llm:
            raise RuntimeError("Dog Retriever: API Key 未配置，无法进行分析")

        return self.format_results(risk_items, location=location)

    def format_results(
        self,
        risk_items: List[Dict],
        legal_docs: List[Dict] | None = None,
        cases: List[Dict] | None = None,
        location: str = "beijing",
    ) -> Dict:
        if not risk_items:
            return {
                "legal_references": [],
                "case_references": [],
                "suggestions": [],
                "negotiation_tips": [],
            }

        compact_risks = self._compact_risk_items(risk_items, limit=len(risk_items))
        top_level_chunks = self._split_into_top_level_groups(compact_risks, groups=3)
        risk_batches = self._split_until_within_budget(top_level_chunks)
        print(
            f"[Dog Retriever] processing {len(compact_risks)} risks in "
            f"{len(risk_batches)} chunks"
        )

        merged_legal_references: List[Dict] = []
        merged_case_references: List[Dict] = []

        for index, batch in enumerate(risk_batches, start=1):
            batch_size = self._estimate_payload_size(batch)
            print(
                f"[Dog Retriever] analyzing chunk {index}/{len(risk_batches)} "
                f"(payload~{batch_size} bytes, items={len(batch)})"
            )
            batch_legal_docs, batch_cases = self.retrieve_sources(batch, location)
            if not batch_legal_docs and legal_docs:
                batch_legal_docs = legal_docs
            if not batch_cases and cases:
                batch_cases = cases
            result = self._format_batch_results(batch, batch_legal_docs, batch_cases)
            merged_legal_references.extend(result.get("legal_references", []))
            merged_case_references.extend(result.get("case_references", []))

        return {
            "legal_references": self._dedupe_reference_items(
                merged_legal_references, key_fields=("title", "content")
            ),
            "case_references": self._dedupe_reference_items(
                merged_case_references, key_fields=("title", "summary", "content")
            ),
            "suggestions": [],
            "negotiation_tips": [],
        }

    def retrieve_sources(self, risk_items: List[Dict], location: str = "beijing") -> tuple[List[Dict], List[Dict]]:
        if not risk_items:
            return dog_retriever_prompt.MOCK_LEGAL_DOCS, dog_retriever_prompt.MOCK_CASES

        if self.use_rag:
            query = " ".join(
                item.get("issue", "") if isinstance(item, dict) else str(item)
                for item in risk_items
            )
            search_results = self.retriever.search_all(query, top_k=3)
            legal_docs = self._format_legal_docs(search_results["legal_docs"])
            cases = self._format_cases(search_results["cases"])
            return legal_docs, cases

        return dog_retriever_prompt.MOCK_LEGAL_DOCS, dog_retriever_prompt.MOCK_CASES

    def _format_batch_results(
        self,
        risk_items: List[Dict],
        legal_docs: List[Dict],
        cases: List[Dict],
    ) -> Dict:
        compact_legal_docs = self._compact_legal_docs(legal_docs)
        compact_cases = self._compact_cases(cases)
        prompt = dog_retriever_prompt.REFERENCE_ONLY_FORMATTING_PROMPT_TEMPLATE.format(
            legal_docs=json.dumps(compact_legal_docs, ensure_ascii=False, separators=(",", ":")),
            cases=json.dumps(compact_cases, ensure_ascii=False, separators=(",", ":")),
            risk_items=json.dumps(risk_items, ensure_ascii=False, separators=(",", ":")),
        )

        response_text = self.llm.call_with_prompts(
            system_prompt=dog_retriever_prompt.SYSTEM_PROMPT,
            user_prompt=prompt
        )
        result = extract_json_payload(response_text)
        if not self._validate_reference_result(result):
            raise ValueError("Dog Retriever: LLM 返回的结构不完整")
        return {
            "legal_references": result.get("legal_references", []),
            "case_references": result.get("case_references", []),
        }

    def _validate_result(self, result: Dict) -> bool:
        required_keys = ["legal_references", "case_references", "suggestions", "negotiation_tips"]
        return all(key in result for key in required_keys)

    def _validate_reference_result(self, result: Dict) -> bool:
        required_keys = ["legal_references", "case_references"]
        return all(key in result for key in required_keys)

    def _compact_risk_items(self, risk_items: List[Dict], limit: int = 12) -> List[Dict]:
        severity_order = {"high": 0, "medium": 1, "low": 2}
        ordered = sorted(
            risk_items,
            key=lambda item: (
                severity_order.get(item.get("risk_level", "low"), 3),
                -len(item.get("issue", "")),
            ),
        )
        compact = []
        for index, item in enumerate(ordered[:limit], start=1):
            compact.append(
                {
                    "risk_id": item.get("risk_id", f"risk_{index}"),
                    "risk_level": item.get("risk_level"),
                    "issue": item.get("issue", "")[:120],
                    "clause": item.get("clause", "")[:120],
                }
            )
        return compact

    def _split_into_top_level_groups(
        self, compact_risks: List[Dict], groups: int = 3
    ) -> List[List[Dict]]:
        if not compact_risks:
            return []

        chunk_len = max(1, ceil(len(compact_risks) / groups))
        return [
            compact_risks[index : index + chunk_len]
            for index in range(0, len(compact_risks), chunk_len)
        ]

    def _split_until_within_budget(
        self,
        groups: List[List[Dict]],
        target_bytes: int = 1000,
    ) -> List[List[Dict]]:
        final_groups: List[List[Dict]] = []
        pending = [group for group in groups if group]

        while pending:
            group = pending.pop(0)
            if self._estimate_payload_size(group) <= target_bytes or len(group) == 1:
                final_groups.append(self._shrink_group_to_budget(group, target_bytes))
                continue

            midpoint = max(1, len(group) // 2)
            pending.insert(0, group[midpoint:])
            pending.insert(0, group[:midpoint])

        return final_groups

    def _shrink_group_to_budget(
        self, group: List[Dict], target_bytes: int
    ) -> List[Dict]:
        if len(group) != 1:
            return group

        item = dict(group[0])
        if self._estimate_payload_size([item]) <= target_bytes:
            return [item]

        clause = item.get("clause", "")
        while clause and self._estimate_payload_size([item]) > target_bytes:
            clause = clause[: max(40, len(clause) - 20)]
            item["clause"] = clause

        issue = item.get("issue", "")
        while issue and self._estimate_payload_size([item]) > target_bytes:
            issue = issue[: max(40, len(issue) - 10)]
            item["issue"] = issue

        return [item]

    def _estimate_payload_size(self, items: List[Dict]) -> int:
        return len(
            json.dumps(items, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )

    def _dedupe_reference_items(
        self,
        items: List[Dict],
        *,
        key_fields: tuple[str, ...],
    ) -> List[Dict]:
        seen: set[str] = set()
        deduped: List[Dict] = []
        for item in items:
            key = "||".join(str(item.get(field, ""))[:120] for field in key_fields)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _compact_legal_docs(self, legal_docs: List[Dict], limit: int = 3) -> List[Dict]:
        compact = []
        for item in legal_docs[:limit]:
            compact.append(
                {
                    "law_id": item.get("law_id"),
                    "title": item.get("title", "")[:80],
                    "content": item.get("content", "")[:220],
                    "relevance": item.get("relevance", "")[:120],
                    "application": item.get("application", "")[:120],
                }
            )
        return compact

    def _compact_cases(self, cases: List[Dict], limit: int = 3) -> List[Dict]:
        compact = []
        for item in cases[:limit]:
            compact.append(
                {
                    "case_id": item.get("case_id"),
                    "title": item.get("title", "")[:80],
                    "summary": (item.get("summary") or item.get("content") or "")[:220],
                    "relevance": item.get("relevance", "")[:120],
                    "ruling": item.get("ruling", "")[:120],
                    "lesson": item.get("lesson", "")[:120],
                }
            )
        return compact

    def _format_legal_docs(self, search_results: List[Dict]) -> List[Dict]:
        formatted = []
        for index, result in enumerate(search_results):
            formatted.append(
                {
                    "law_id": f"law_{index + 1}",
                    "title": f"法律条文 {index + 1}",
                    "content": result["text"][:500],
                    "source": result["metadata"]["source"],
                    "relevance": f"相似度 {result['score']:.4f}",
                }
            )
        return formatted

    def _format_cases(self, search_results: List[Dict]) -> List[Dict]:
        formatted = []
        for index, result in enumerate(search_results):
            formatted.append(
                {
                    "case_id": f"case_{index + 1}",
                    "title": f"案例 {index + 1}",
                    "content": result["text"][:500],
                    "source": result["metadata"]["source"],
                    "relevance": f"相似度 {result['score']:.4f}",
                }
            )
        return formatted

    def _build_fallback_result(self, legal_docs: List[Dict], cases: List[Dict]) -> Dict:
        return {
            "legal_references": legal_docs,
            "case_references": cases,
            "suggestions": [],
            "negotiation_tips": [],
        }

    def _build_empty_result(self) -> Dict:
        return {
            "legal_references": [],
            "case_references": [],
            "suggestions": [],
            "negotiation_tips": [],
        }
