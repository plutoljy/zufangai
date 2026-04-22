"""
Cat Reporter Agent
Responsible for generating the final Markdown report.
"""

from __future__ import annotations

import json
import os
import sys
import time
from math import ceil
from typing import Dict, List

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from prompts import cat_reporter_prompt


def split_report_paragraphs(markdown: str) -> list[str]:
    paragraphs: list[str] = []
    current_lines: list[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if current_lines:
                paragraphs.append("\n".join(current_lines).strip())
                current_lines = []
            continue

        if line.startswith("#") and current_lines:
          paragraphs.append("\n".join(current_lines).strip())
          current_lines = [line]
          continue

        current_lines.append(line)

    if current_lines:
        paragraphs.append("\n".join(current_lines).strip())

    return [paragraph for paragraph in paragraphs if paragraph]


class CatReporter:
    """Generate final contract analysis reports."""

    def __init__(self):
        # 优先使用 Claude Sonnet API（速度优先，报告生成）
        if settings.claude_api_key_sonnet:
            self.api_key = settings.claude_api_key_sonnet
            self.base_url = settings.claude_base_url
            self.model = settings.claude_model_sonnet
            self.temperature = 0.3
            self.timeout = 180
            self.use_llm = True
            self.api_type = "claude"
            print(f"[OK] Cat Reporter: 使用 Claude {settings.claude_model_sonnet} 模型")
        elif settings.claude_api_key_opus:
            self.api_key = settings.claude_api_key_opus
            self.base_url = settings.claude_base_url
            self.model = settings.claude_model_opus
            self.temperature = 0.3
            self.timeout = 180
            self.use_llm = True
            self.api_type = "claude"
            print(f"[OK] Cat Reporter: 使用 Claude {settings.claude_model_opus} 模型")
        else:
            print("[WARN] Cat Reporter: Claude API Key 未配置，使用 fallback 模式")
            self.api_key = None
            self.use_llm = False
            self.api_type = None

    def generate_report(
        self,
        entities: Dict,
        risk_items: List[Dict],
        legal_references: List[Dict] = None,
        case_references: List[Dict] = None,
        calculations: Dict = None,
        is_template: bool = False,
    ) -> Dict:
        legal_references = legal_references or []
        case_references = case_references or []
        calculations = calculations or {}

        if is_template:
            return {
                "report_markdown": self._generate_template_report(risk_items),
                "summary": self._generate_summary(risk_items, calculations),
            }

        if not self.use_llm:
            print("[Cat Reporter] using fallback mode")
            return {
                "report_markdown": self._generate_fallback_report(entities, risk_items),
                "summary": self._generate_summary(risk_items, calculations),
            }

        category_summaries = self._build_category_summaries(
            entities=entities,
            risk_items=risk_items,
            legal_references=legal_references,
            case_references=case_references,
            calculations=calculations,
        )
        prompt = self._build_final_prompt(category_summaries)

        try:
            # 使用统一的 API 调用方法
            response_text = self._call_llm_with_retry(self._build_llm_messages(prompt))

            report_markdown = response_text
            summary = self._generate_summary(risk_items, calculations)
            return {"report_markdown": report_markdown, "summary": summary}
        except Exception as exc:
            print(f"Cat Reporter error: {exc}")
            return {
                "report_markdown": self._generate_fallback_report(entities, risk_items),
                "summary": self._generate_summary(risk_items, calculations),
            }

    def _generate_summary(self, risk_items: List[Dict], calculations: Dict) -> Dict:
        high_risks = [risk for risk in risk_items if risk.get("risk_level") == "high"]
        medium_risks = [risk for risk in risk_items if risk.get("risk_level") == "medium"]
        low_risks = [risk for risk in risk_items if risk.get("risk_level") == "low"]
        deposit_compliant = calculations.get("deposit_check", {}).get("compliant", True)

        return {
            "total_risks": len(risk_items),
            "high_risks": len(high_risks),
            "medium_risks": len(medium_risks),
            "low_risks": len(low_risks),
            "compliant": deposit_compliant and len(high_risks) == 0,
        }

    def _generate_template_report(self, risk_items: List[Dict]) -> str:
        report_lines = [
            "# 租房合同模板风险分析报告",
            "",
            "## 模板提示",
            "以下风险分析仅针对模板条款本身，实际风险需要在填写后重新评估。",
            "",
        ]

        grouped_risks = {
            "high": ("## 高风险条款", []),
            "medium": ("## 中风险条款", []),
            "low": ("## 低风险条款", []),
        }

        for item in risk_items:
            risk_level = item.get("risk_level", "low")
            grouped_risks.setdefault(risk_level, (f"## {risk_level} 风险条款", []))
            grouped_risks[risk_level][1].append(item)

        if not risk_items:
            report_lines.extend(
                [
                    "当前未识别出明确风险条款，但由于合同仍是模板文本，填写完整后仍需重新评估。",
                    "",
                ]
            )
        else:
            for _, (section_title, items) in grouped_risks.items():
                if not items:
                    continue
                report_lines.extend([section_title, ""])
                for index, item in enumerate(items, 1):
                    report_lines.extend(
                        [
                            f"### 风险{index}: {item.get('issue', '待补充风险说明')}",
                            f"- 原文条款: {item.get('clause', '未提供')}",
                            f"- 法律依据: {item.get('legal_basis', '未提供')}",
                            f"- 修改建议: {item.get('suggestion', '待补充')}",
                            "",
                        ]
                    )

        return "\n".join(report_lines)

    def _generate_fallback_report(self, entities: Dict, risk_items: List[Dict]) -> str:
        report = f"""# 租房合同分析报告

## 合同概况
- 出租方: {entities.get('lessor', '未知')}
- 承租方: {entities.get('lessee', '未知')}
- 月租金: {entities.get('monthly_rent', 0)}元
- 押金: {entities.get('deposit', 0)}元

## 风险警示
发现 {len(risk_items)} 项风险
"""
        for index, risk in enumerate(risk_items, 1):
            report += f"{index}. {risk.get('issue', '未知风险')}\n"
        return report

    def _build_llm_messages(self, prompt: str) -> List[Dict]:
        # 与 Owl 对齐：在当前 Claude relay 上单条 user 消息更稳定。
        if self.api_type == "claude":
            return [
                {
                    "role": "user",
                    "content": f"{cat_reporter_prompt.COMPACT_SYSTEM_PROMPT}\n\n{prompt}",
                }
            ]

        return [
            {"role": "system", "content": cat_reporter_prompt.COMPACT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

    def _build_final_prompt(self, category_summaries: Dict) -> str:
        entities_json = json.dumps(
            category_summaries["entities"], ensure_ascii=False, separators=(",", ":")
        )
        risk_items_json = json.dumps(
            category_summaries["owl"], ensure_ascii=False, separators=(",", ":")
        )
        legal_references_json = json.dumps(
            category_summaries["dog"], ensure_ascii=False, separators=(",", ":")
        )
        calculations_json = json.dumps(
            category_summaries["beaver"], ensure_ascii=False, separators=(",", ":")
        )

        prompt = cat_reporter_prompt.COMPACT_REPORT_PROMPT.format(
            entities_json=entities_json,
            risk_items_json=risk_items_json,
            legal_references_json=legal_references_json,
            calculations_json=calculations_json,
        )
        print(
            "[Cat Reporter] Summary sizes:",
            f"entities={len(entities_json.encode('utf-8'))}",
            f"owl={len(risk_items_json.encode('utf-8'))}",
            f"dog={len(legal_references_json.encode('utf-8'))}",
            f"beaver={len(calculations_json.encode('utf-8'))}",
            f"prompt={len(prompt.encode('utf-8'))}",
        )
        return prompt

    def _build_category_summaries(
        self,
        *,
        entities: Dict,
        risk_items: List[Dict],
        legal_references: List[Dict],
        case_references: List[Dict],
        calculations: Dict,
    ) -> Dict:
        return {
            "entities": self._compact_entities(entities),
            "owl": self._build_owl_summary(risk_items),
            "dog": self._build_dog_summary(legal_references, case_references),
            "beaver": self._build_beaver_summary(calculations),
        }

    def _compact_entities(self, entities: Dict) -> Dict:
        return {
            "lessor": entities.get("lessor"),
            "lessee": entities.get("lessee"),
            "property_address": entities.get("property_address"),
            "monthly_rent": entities.get("monthly_rent"),
            "deposit": entities.get("deposit"),
            "lease_term": entities.get("lease_term"),
        }

    def _build_owl_summary(self, risk_items: List[Dict]) -> Dict:
        severity_counts = {
            "high": len([item for item in risk_items if item.get("risk_level") == "high"]),
            "medium": len([item for item in risk_items if item.get("risk_level") == "medium"]),
            "low": len([item for item in risk_items if item.get("risk_level") == "low"]),
        }
        return {
            "total_risks": len(risk_items),
            "severity_counts": severity_counts,
            "chunks": self._build_chunked_groups(
                self._compact_risk_items(risk_items, limit=len(risk_items)),
                target_bytes=1000,
                groups=3,
                summary_builder=self._summarize_owl_chunk,
            ),
        }

    def _build_dog_summary(
        self,
        legal_references: List[Dict],
        case_references: List[Dict],
    ) -> Dict:
        return {
            "legal_reference_count": len(legal_references),
            "case_reference_count": len(case_references),
            "legal_reference_chunks": self._build_chunked_groups(
                self._compact_legal_references(legal_references, limit=len(legal_references)),
                target_bytes=1000,
                groups=3,
                summary_builder=self._summarize_reference_chunk,
            ),
            "case_reference_chunks": self._build_chunked_groups(
                self._compact_case_references(case_references, limit=len(case_references)),
                target_bytes=1000,
                groups=3,
                summary_builder=self._summarize_case_chunk,
            ),
        }

    def _build_beaver_summary(self, calculations: Dict) -> Dict:
        compact = self._compact_calculations(calculations)
        return {
            "core": {
                "deposit": {
                    "amount": compact.get("deposit_check", {}).get("amount"),
                    "limit": compact.get("deposit_check", {}).get("legal_limit"),
                    "ok": compact.get("deposit_check", {}).get("compliant"),
                    "issue": (compact.get("deposit_check", {}).get("issue") or "")[:80],
                },
                "utilities": [
                    {
                        "name": key,
                        "charged": value.get("charged"),
                        "official": value.get("official"),
                        "ok": not value.get("overcharged"),
                        "issue": (value.get("issue") or "")[:80],
                    }
                    for key, value in compact.get("utilities_check", {}).items()
                ],
                "cost": {
                    "monthly": compact.get("total_cost_analysis", {}).get("monthly_total"),
                    "yearly": compact.get("total_cost_analysis", {}).get("yearly_total"),
                    "market": (compact.get("total_cost_analysis", {}).get("market_comparison") or "")[:60],
                },
                "mode": compact.get("analysis_metadata", {}).get("mode"),
            },
            "hidden_cost_chunks": self._build_chunked_groups(
                compact.get("hidden_costs", []),
                target_bytes=1000,
                groups=3,
                summary_builder=self._summarize_generic_chunk,
            ),
            "ambiguous_clause_chunks": self._build_chunked_groups(
                compact.get("ambiguous_clauses", {}).get("items", []),
                target_bytes=1000,
                groups=3,
                summary_builder=self._summarize_generic_chunk,
            ),
        }

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
        for item in ordered[:limit]:
            compact.append(
                {
                    "risk_level": item.get("risk_level"),
                    "issue": item.get("issue", "")[:120],
                    "clause": item.get("clause", "")[:120],
                    "legal_basis": item.get("legal_basis", "")[:120],
                }
            )
        return compact

    def _compact_legal_references(self, legal_references: List[Dict], limit: int = 5) -> List[Dict]:
        compact = []
        for item in legal_references[:limit]:
            compact.append(
                {
                    "title": item.get("title", "")[:80],
                    "content": item.get("content", "")[:220],
                    "application": item.get("application", "")[:120],
                    "relevance": item.get("relevance", "")[:120],
                }
            )
        return compact

    def _compact_case_references(self, case_references: List[Dict], limit: int = 5) -> List[Dict]:
        compact = []
        for item in case_references[:limit]:
            compact.append(
                {
                    "title": item.get("title", "")[:80],
                    "summary": (item.get("summary") or item.get("content") or "")[:220],
                    "relevance": item.get("relevance", "")[:120],
                    "ruling": item.get("ruling", "")[:120],
                    "lesson": item.get("lesson", "")[:120],
                }
            )
        return compact

    def _compact_calculations(self, calculations: Dict) -> Dict:
        return {
            "deposit_check": calculations.get("deposit_check", {}),
            "utilities_check": calculations.get("utilities_check", {}),
            "total_cost_analysis": calculations.get("total_cost_analysis", {}),
            "analysis_metadata": calculations.get("analysis_metadata", {}),
            "hidden_costs": calculations.get("hidden_costs", [])[:5],
            "ambiguous_clauses": {
                "count": calculations.get("ambiguous_clauses", {}).get("count", 0),
                "items": calculations.get("ambiguous_clauses", {}).get("items", [])[:5],
            },
        }

    def _build_chunked_groups(
        self,
        items: List[Dict],
        *,
        target_bytes: int,
        groups: int,
        summary_builder,
    ) -> List[Dict]:
        if not items:
            return []

        pending = self._split_into_top_level_groups(items, groups=groups)
        final_groups: List[List[Dict]] = []

        while pending:
            group = pending.pop(0)
            if self._estimate_payload_size(group) <= target_bytes or len(group) == 1:
                final_groups.append(self._shrink_group_to_budget(group, target_bytes))
                continue

            midpoint = max(1, len(group) // 2)
            pending.insert(0, group[midpoint:])
            pending.insert(0, group[:midpoint])

        return [
            summary_builder(index + 1, group)
            for index, group in enumerate(final_groups)
        ]

    def _split_into_top_level_groups(
        self, items: List[Dict], *, groups: int = 3
    ) -> List[List[Dict]]:
        chunk_size = max(1, ceil(len(items) / groups))
        return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]

    def _shrink_group_to_budget(
        self, group: List[Dict], target_bytes: int
    ) -> List[Dict]:
        if len(group) != 1:
            return group

        item = dict(group[0])
        if self._estimate_payload_size([item]) <= target_bytes:
            return [item]

        for field in ("content", "summary", "clause", "issue", "legal_basis", "application", "relevance"):
            value = item.get(field)
            while isinstance(value, str) and value and self._estimate_payload_size([item]) > target_bytes:
                value = value[: max(40, len(value) - 20)]
                item[field] = value

        return [item]

    def _estimate_payload_size(self, items: List[Dict]) -> int:
        return len(json.dumps(items, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    def _summarize_owl_chunk(self, index: int, items: List[Dict]) -> Dict:
        highlights = [item.get("issue", "")[:48] for item in items[:2]]
        severity_counts = {
            "high": len([item for item in items if item.get("risk_level") == "high"]),
            "medium": len([item for item in items if item.get("risk_level") == "medium"]),
            "low": len([item for item in items if item.get("risk_level") == "low"]),
        }
        return {
            "index": index,
            "count": len(items),
            "severity_counts": severity_counts,
            "top_issues": highlights,
        }

    def _summarize_reference_chunk(self, index: int, items: List[Dict]) -> Dict:
        titles = [item.get("title", "")[:48] for item in items[:2]]
        return {
            "index": index,
            "count": len(items),
            "titles": titles,
        }

    def _summarize_case_chunk(self, index: int, items: List[Dict]) -> Dict:
        titles = [item.get("title", "")[:48] for item in items[:2]]
        return {
            "index": index,
            "count": len(items),
            "titles": titles,
        }

    def _summarize_generic_chunk(self, index: int, items: List[Dict]) -> Dict:
        highlights = []
        for item in items[:2]:
            if "description" in item:
                highlights.append(str(item.get("description", ""))[:48])
            elif "clause" in item:
                highlights.append(str(item.get("clause", ""))[:48])
            elif "issue" in item:
                highlights.append(str(item.get("issue", ""))[:48])
        return {
            "index": index,
            "count": len(items),
            "highlights": highlights,
        }

    def _call_llm_with_retry(self, messages: List[Dict], max_retries: int = 5) -> str:
        """统一的 LLM API 调用方法，支持重试"""
        last_error = None

        for attempt in range(max_retries):
            try:
                # Claude API
                api_url = f"{self.base_url}/v1/messages"
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }

                payload = {
                    "model": self.model,
                    "max_tokens": 4096,
                    "temperature": self.temperature,
                    "messages": [{"role": "user", "content": messages[0]["content"]}],
                }

                # 禁用代理
                proxies = {'http': None, 'https': None}
                print(f"[Cat Reporter] API URL: {api_url}")
                print(f"[Cat Reporter] Payload size: {len(str(payload))} bytes")

                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    verify=False,
                    proxies=proxies
                )

                response.raise_for_status()
                result = response.json()
                return result["content"][0]["text"]

            except Exception as e:
                last_error = e
                print(f"[Cat Reporter] API call attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"[Cat Reporter] Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

        raise Exception(f"All {max_retries} API call attempts failed: {last_error}")
