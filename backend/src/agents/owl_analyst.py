"""
Owl Analyst Agent V2
Responsible for extracting entities from the contract and identifying risks.

改进：
1. 移除 few-shot examples，避免限制 LLM 识别能力
2. 使用原则导向的提示词，而非模板化示例
3. 添加规则引擎作为补充和 fallback
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from prompts import owl_analyst_prompt_v2 as owl_prompt
from agents.rule_engine import rule_based_review, merge_llm_and_rule_risks
from ai_provider_manager import ResolvedAgentConfig
from utils.agent_config import apply_llm_config
from utils.json_payload import extract_json_payload
from utils.llm_client import LLMClient


class OwlAnalyst:
    """Extract contract entities and detect risk items."""

    def __init__(self, llm_config: ResolvedAgentConfig | None = None):
        # 优先使用 Claude API，如果没有则使用千问
        if settings.claude_api_key_opus:
            self.api_key = settings.claude_api_key_opus
            self.base_url = settings.claude_base_url
            self.model = settings.claude_model_opus
            self.temperature = 0.3
            self.timeout = 180
            self.use_llm = True
            self.api_type = "claude"
            print(f"[OK] Owl Analyst: 使用 Claude {settings.claude_model_opus} 模型 (temperature={self.temperature})")
        elif settings.qwen_api_key:
            self.api_key = settings.qwen_api_key
            self.base_url = settings.qwen_base_url
            self.model = settings.qwen_model
            self.temperature = 0.3
            self.timeout = 180
            self.use_llm = True
            self.api_type = "qwen"
            print(f"[OK] Owl Analyst: 使用千问 {settings.qwen_model} 模型 (temperature={self.temperature})")
        else:
            print("[WARN] Owl Analyst: 未配置 API Key，使用 fallback 模式")
            self.api_key = None
            self.use_llm = False
            self.api_type = None

        if llm_config is not None:
            apply_llm_config(self, llm_config)
            self.temperature = 0.3
            self.timeout = 180
            print(
                f"[OK] Owl Analyst: using user provider "
                f"{llm_config.provider_name}/{llm_config.model_name}"
            )

        self._llm: LLMClient | None = None

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
                agent_name="owl",
            )
        return self._llm

    def analyze(self, contract_text: str) -> Dict:
        """分析合同，提取实体和识别风险"""
        if not contract_text or not contract_text.strip():
            raise ValueError("合同文本为空")

        if not self.use_llm or not self.api_key:
            raise RuntimeError("Owl Analyst: API Key 未配置，无法进行分析")

        # 添加调试日志
        print(f"[Owl Analyst] 开始分析合同")
        print(f"[Owl Analyst] 合同文本长度: {len(contract_text)} 字符")
        print(f"[Owl Analyst] 合同文本前200字符: {contract_text[:200]}")

        # 如果合同文本较长（>1500字符），使用分块策略
        if len(contract_text) > 1500:
            print(f"[Owl Analyst] 合同较长，使用分块分析策略")
            return self._analyze_in_chunks(contract_text)

        # 短合同直接分析
        user_prompt = owl_prompt.USER_PROMPT_TEMPLATE.format(
            contract_text=contract_text
        )
        messages = [
            {"role": "system", "content": owl_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response_text = self.llm.call(messages)
        result = extract_json_payload(response_text)

        if not isinstance(result, dict):
            raise ValueError(f"LLM 返回格式错误: {type(result)}")

        result.setdefault("entities", {})
        result.setdefault("risk_items", [])

        # 使用规则引擎补充风险识别
        entities = result.get("entities", {})
        llm_risks = result.get("risk_items", [])
        rule_risks = rule_based_review(contract_text, entities)

        # 合并 LLM 和规则引擎的结果
        merged_risks = merge_llm_and_rule_risks(llm_risks, rule_risks)
        result["risk_items"] = merged_risks

        # 添加更详细的日志
        print(f"[Owl Analyst] 分析完成:")
        print(f"  - 出租方: {entities.get('lessor')}")
        print(f"  - 承租方: {entities.get('lessee')}")
        print(f"  - 月租金: {entities.get('monthly_rent')}")
        print(f"  - 押金: {entities.get('deposit')}")
        print(f"  - LLM 识别风险: {len(llm_risks)} 个")
        print(f"  - 规则引擎补充: {len(rule_risks)} 个")
        print(f"  - 合并后总风险: {len(merged_risks)} 个")

        return result

    def _analyze_in_chunks(self, contract_text: str) -> Dict:
        """分块分析长合同"""
        print("[Owl Analyst] 执行分块分析")

        # 第一步：提取实体信息（使用简化的 prompt）
        entity_prompt = f"""从以下合同中提取关键信息，返回JSON格式：
{{
  "lessor": "出租方",
  "lessee": "承租方",
  "property_address": "地址",
  "monthly_rent": 数字,
  "deposit": 数字,
  "lease_term": "租期",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "utilities": {{"water": 数字, "electricity": 数字, "gas": 数字}}
}}

合同文本：
{contract_text[:1000]}

只返回JSON，不加其他内容。"""

        messages = [{"role": "user", "content": entity_prompt}]

        try:
            response_text = self.llm.call(messages)
            entities = extract_json_payload(response_text)
            print(f"[Owl Analyst] 实体提取成功")
        except Exception as e:
            print(f"[WARN] 实体提取失败: {e}，使用规则引擎")
            entities = self._extract_entities_by_rules(contract_text)

        # 第二步：分块识别风险
        # 将合同按段落分块，每块约800字符
        chunks = self._split_into_chunks(contract_text, chunk_size=800)
        print(f"[Owl Analyst] 合同分为 {len(chunks)} 块")

        all_risks = []
        for i, chunk in enumerate(chunks):
            print(f"[Owl Analyst] 分析第 {i+1}/{len(chunks)} 块...")
            risk_prompt = f"""识别以下合同片段中的风险条款，返回JSON数组：
[
  {{
    "clause": "原文",
    "risk_level": "high|medium|low",
    "issue": "风险说明",
    "legal_basis": "法律依据",
    "suggestion": "修改建议"
  }}
]

合同片段：
{chunk}

只返回JSON数组，如无风险返回[]。"""

            try:
                messages = [{"role": "user", "content": risk_prompt}]
                response_text = self.llm.call(messages)

                # 尝试提取 JSON，如果失败则跳过这个分块
                try:
                    chunk_risks = extract_json_payload(response_text)
                    if isinstance(chunk_risks, list):
                        all_risks.extend(chunk_risks)
                        print(f"  - 发现 {len(chunk_risks)} 个风险")
                    else:
                        print(f"  - 响应不是列表格式，跳过")
                except ValueError as json_err:
                    print(f"  - JSON 解析失败: {json_err}，响应预览: {response_text[:100]}")
                    continue
            except Exception as e:
                print(f"  - 分析失败: {e}")
                continue

        # 使用规则引擎补充
        rule_risks = rule_based_review(contract_text, entities)
        merged_risks = merge_llm_and_rule_risks(all_risks, rule_risks)

        print(f"[Owl Analyst] 分块分析完成:")
        print(f"  - LLM 识别风险: {len(all_risks)} 个")
        print(f"  - 规则引擎补充: {len(rule_risks)} 个")
        print(f"  - 合并后总风险: {len(merged_risks)} 个")

        return {
            "entities": entities,
            "risk_items": merged_risks
        }

    def _split_into_chunks(self, text: str, chunk_size: int = 800) -> List[str]:
        """将文本分块，尽量按段落分割"""
        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _extract_entities_by_rules(self, contract_text: str) -> Dict:
        """使用规则引擎提取实体"""
        start_date, end_date = self._extract_date_range(contract_text)
        monthly_rent = self._extract_number(
            contract_text,
            [r"月租金[：:]\s*([0-9]+(?:\.[0-9]+)?)", r"月租[：:]\s*([0-9]+(?:\.[0-9]+)?)"],
        )
        deposit = self._extract_number(
            contract_text,
            [r"押金[：:]\s*([0-9]+(?:\.[0-9]+)?)", r"保证金[：:]\s*([0-9]+(?:\.[0-9]+)?)"],
        )

        return {
            "lessor": self._extract_first_group(
                contract_text,
                [r"甲方[（(][^）)]*[）)][：:]\s*([^\n\r]+)", r"甲方[：:]\s*([^\n\r]+)"],
            ),
            "lessee": self._extract_first_group(
                contract_text,
                [r"乙方[（(][^）)]*[）)][：:]\s*([^\n\r]+)", r"乙方[：:]\s*([^\n\r]+)"],
            ),
            "monthly_rent": monthly_rent,
            "deposit": deposit,
            "lease_term": self._extract_first_group(
                contract_text,
                [r"租期[：:]\s*([^\n\r]+)", r"共\s*([0-9]+个月)"],
            ),
            "property_address": self._extract_first_group(
                contract_text,
                [r"(?:地址|房屋地址)[：:]\s*([^\n\r]+)"],
            ),
            "start_date": start_date,
            "end_date": end_date,
            "utilities": {
                "water": self._extract_number(contract_text, [r"水费[：:\s]*([0-9]+(?:\.[0-9]+)?)"]),
                "electricity": self._extract_number(
                    contract_text, [r"(?:电费|电价)[：:\s]*([0-9]+(?:\.[0-9]+)?)"]
                ),
                "gas": self._extract_number(contract_text, [r"(?:燃气费|燃气)[：:\s]*([0-9]+(?:\.[0-9]+)?)"]),
            },
        }

    def _build_fallback_result(self, contract_text: str) -> Dict:
        """使用规则引擎构建 fallback 结果"""
        print("[Owl Analyst] 使用规则引擎 fallback 模式")

        # 提取基本实体
        start_date, end_date = self._extract_date_range(contract_text)
        monthly_rent = self._extract_number(
            contract_text,
            [r"月租金[：:]\s*([0-9]+(?:\.[0-9]+)?)", r"月租[：:]\s*([0-9]+(?:\.[0-9]+)?)"],
        )
        deposit = self._extract_number(
            contract_text,
            [r"押金[：:]\s*([0-9]+(?:\.[0-9]+)?)", r"保证金[：:]\s*([0-9]+(?:\.[0-9]+)?)"],
        )

        entities = {
            "lessor": self._extract_first_group(
                contract_text,
                [r"甲方[（(][^）)]*[）)][：:]\s*([^\n\r]+)", r"甲方[：:]\s*([^\n\r]+)"],
            ),
            "lessee": self._extract_first_group(
                contract_text,
                [r"乙方[（(][^）)]*[）)][：:]\s*([^\n\r]+)", r"乙方[：:]\s*([^\n\r]+)"],
            ),
            "monthly_rent": monthly_rent,
            "deposit": deposit,
            "lease_term": self._extract_first_group(
                contract_text,
                [r"租期[：:]\s*([^\n\r]+)", r"共\s*([0-9]+个月)"],
            ),
            "property_address": self._extract_first_group(
                contract_text,
                [r"(?:地址|房屋地址)[：:]\s*([^\n\r]+)"],
            ),
            "start_date": start_date,
            "end_date": end_date,
            "utilities": {
                "water": self._extract_number(contract_text, [r"水费[：:\s]*([0-9]+(?:\.[0-9]+)?)"]),
                "electricity": self._extract_number(
                    contract_text, [r"(?:电费|电价)[：:\s]*([0-9]+(?:\.[0-9]+)?)"]
                ),
                "gas": self._extract_number(contract_text, [r"(?:燃气费|燃气)[：:\s]*([0-9]+(?:\.[0-9]+)?)"]),
            },
        }

        # 使用规则引擎识别风险
        risk_items = rule_based_review(contract_text, entities)

        return {
            "entities": entities,
            "risk_items": risk_items,
        }

    def _extract_first_group(self, contract_text: str, patterns: List[str]) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, contract_text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_number(self, contract_text: str, patterns: List[str]) -> Optional[float]:
        for pattern in patterns:
            match = re.search(pattern, contract_text)
            if match:
                value = match.group(1).replace(",", "")
                return float(value) if "." in value else int(value)
        return None

    def _extract_date_range(self, contract_text: str) -> tuple[Optional[str], Optional[str]]:
        match = re.search(
            r"(\d{4})年(\d{1,2})月(\d{1,2})日(?:至|-|到)(\d{4})年(\d{1,2})月(\d{1,2})日",
            contract_text,
        )
        if not match:
            return None, None

        start_date = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        end_date = f"{match.group(4)}-{int(match.group(5)):02d}-{int(match.group(6)):02d}"
        return start_date, end_date

    def _extract_clause(self, contract_text: str, keyword: str) -> Optional[str]:
        for line in contract_text.splitlines():
            if keyword in line:
                return line.strip()
        return None
