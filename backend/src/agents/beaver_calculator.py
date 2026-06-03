"""
Beaver Calculator Agent.
Responsible for cost calculation, compliance checks, and deposit inference.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from ai_provider_manager import ResolvedAgentConfig
from prompts import beaver_calculator_prompt_v3 as beaver_calculator_prompt
from utils.agent_config import apply_llm_config
from utils.json_payload import extract_json_payload
from utils.llm_client import LLMClient


class BeaverCalculator:
    """Compute cost and compliance metrics for the uploaded rental contract."""

    def __init__(self, llm_config: ResolvedAgentConfig | None = None):
        # 优先使用 Beaver 专用 API Key（避免并发冲突）
        if settings.claude_api_key_beaver:
            self.api_key = settings.claude_api_key_beaver
            self.base_url = settings.claude_base_url_beaver or settings.claude_base_url
            self.model = settings.claude_model_beaver or settings.claude_model_opus
            self.temperature = 0.3
            self.timeout = 180
            self.use_llm = True
            # 判断 API 类型：如果 base_url 包含 yescode/codex，则为 OpenAI 兼容
            if self.base_url and ('yescode' in self.base_url or 'codex' in self.base_url):
                self.api_type = "openai"
            else:
                self.api_type = "claude"
            # 与 Owl 对齐，降低单次负载，减少 relay 解析失败概率
            self.chunk_size = 800
            print(f"[OK] Beaver Calculator: 使用 {self.model} 模型 (temperature={self.temperature}, timeout={self.timeout}s, chunk_size={self.chunk_size})")
        elif settings.claude_api_key_opus:
            self.api_key = settings.claude_api_key_opus
            self.base_url = settings.claude_base_url
            self.model = settings.claude_model_opus
            self.temperature = 0.3
            self.timeout = 180
            self.use_llm = True
            self.api_type = "claude"
            self.chunk_size = 800
            print(f"[OK] Beaver Calculator: 使用 Claude {self.model} 模型 (temperature={self.temperature}, timeout={self.timeout}s)")
        elif settings.claude_api_key_sonnet:
            self.api_key = settings.claude_api_key_sonnet
            self.base_url = settings.claude_base_url
            self.model = settings.claude_model_sonnet
            self.temperature = 0.3
            self.timeout = 180
            self.use_llm = True
            self.api_type = "claude"
            self.chunk_size = 800
            print(f"[OK] Beaver Calculator: 使用 Claude {self.model} 模型 (temperature={self.temperature}, timeout={self.timeout}s)")
        else:
            print("[WARN] Beaver Calculator: API Key 未配置，使用确定性模式")
            self.api_key = None
            self.use_llm = False
            self.api_type = None
            self.chunk_size = 800

        if llm_config is not None:
            apply_llm_config(self, llm_config)
            self.temperature = 0.3
            self.timeout = 180
            self.chunk_size = 800
            print(
                f"[OK] Beaver Calculator: using user provider "
                f"{llm_config.provider_name}/{llm_config.model_name}"
            )

        self._llm: LLMClient | None = None

        self.web_search_enabled = False

        from knowledge.retriever import get_retriever

        self.retriever = get_retriever()
        self.use_rag = True
        print("[OK] Beaver Calculator: knowledge base loaded")

        self.official_prices = {
            "beijing": {"water": 5.0, "electricity": 0.5583, "gas": 2.63},
            "shanghai": {"water": 3.45, "electricity": 0.617, "gas": 3.0},
            "guangzhou": {"water": 3.5, "electricity": 0.68, "gas": 3.45},
            "shenzhen": {"water": 3.2, "electricity": 0.68, "gas": 3.5},
        }
        self.compliance_thresholds = {
            "deposit_multiplier": 1.0,
            "utility_markup_limit": 1.5,
        }

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
                agent_name="beaver",
            )
        return self._llm

    def analyze_from_text(self, contract_text: str, location: str = "beijing") -> Dict:
        """
        直接从合同文本分析，不依赖 entities
        当 Owl Agent 失败时使用此方法
        支持分块处理长文本
        """
        if not self.use_llm:
            # 没有 LLM 配置，直接抛出错误
            raise RuntimeError("Beaver Calculator: API Key 未配置，无法进行分析")

        official = self.official_prices.get(location.lower(), self.official_prices["beijing"])

        print(f"[Beaver Calculator] 合同文本长度: {len(contract_text)} 字符")

        # 如果文本较短，直接分析
        if len(contract_text) <= self.chunk_size:
            print(f"[Beaver Calculator] 文本较短，直接分析")
            return self._analyze_single_chunk(contract_text, location, official)

        # 文本较长，使用分块策略
        print(f"[Beaver Calculator] 文本较长，使用分块分析")
        chunks = self._split_into_chunks(contract_text, self.chunk_size)
        print(f"[Beaver Calculator] 合同分为 {len(chunks)} 块")

        # 分析每个块
        all_results = []
        for i, chunk in enumerate(chunks, 1):
            print(f"[Beaver Calculator] 分析第 {i}/{len(chunks)} 块...")
            try:
                result = self._analyze_single_chunk(chunk, location, official)
                all_results.append(result)
                print(f"  - 分析成功")
            except Exception as e:
                print(f"  - 分析失败: {e}")
                continue

        # 合并所有结果
        if not all_results:
            # 所有块分析失败，抛出错误
            raise RuntimeError(f"[Beaver Calculator] 所有 {len(chunks)} 个文本块分析失败")

        print(f"[Beaver Calculator] 合并 {len(all_results)} 个分析结果")
        return self._merge_analysis_results(all_results, contract_text, location)

    def _split_into_chunks(self, text: str, chunk_size: int) -> List[str]:
        """将文本分块，尽量按段落分割"""
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

    def _analyze_single_chunk(self, chunk_text: str, location: str, official: Dict) -> Dict:
        """分析单个文本块"""
        # 使用简化的提示词模板
        prompt = beaver_calculator_prompt.ANALYSIS_PROMPT_TEMPLATE.format(
            contract_text=chunk_text,
            location=location,
            official_water=official["water"],
            official_electricity=official["electricity"],
            official_gas=official["gas"]
        )

        response_text = self.llm.call(self._build_llm_messages(prompt))

        result = extract_json_payload(response_text)
        if not self._validate_result(result):
            raise ValueError("Beaver Calculator returned an incomplete payload.")
        return result

    def _merge_analysis_results(
        self,
        results: List[Dict],
        contract_text: str = "",
        location: str = "beijing",
    ) -> Dict:
        """合并多个分析结果"""
        if not results:
            return {
                "deposit_check": {"amount": 0, "legal_limit": 0, "compliant": None},
                "utilities_check": {"water": {}, "electricity": {}, "gas": {}},
                "total_cost_analysis": {}
            }

        # 取第一个有效结果作为基础
        merged = results[0].copy()

        # 合并隐藏费用（新格式：hidden_costs 是 list）
        all_hidden_items = []
        for result in results:
            hidden_costs = result.get("hidden_costs", [])
            # 兼容新格式（list）和旧格式（dict）
            if isinstance(hidden_costs, list):
                all_hidden_items.extend(hidden_costs)
            elif isinstance(hidden_costs, dict) and hidden_costs.get("found"):
                all_hidden_items.extend(hidden_costs.get("items", []))

        if all_hidden_items:
            merged["hidden_costs"] = all_hidden_items

        # 合并模糊条款（新格式：ambiguous_clauses 是 dict with items）
        all_ambiguous_items = []
        for result in results:
            ambiguous = result.get("ambiguous_clauses", {})
            if isinstance(ambiguous, dict):
                all_ambiguous_items.extend(ambiguous.get("items", []))

        if all_ambiguous_items:
            merged["ambiguous_clauses"] = {
                "count": len(all_ambiguous_items),
                "items": all_ambiguous_items
            }

        # 合并关键警告
        all_warnings = []
        for result in results:
            warnings = result.get("critical_warnings", [])
            if warnings:
                all_warnings.extend(warnings)

        if all_warnings:
            merged["critical_warnings"] = all_warnings

        # 合并立即行动建议
        all_actions = []
        for result in results:
            actions = result.get("immediate_actions_required", [])
            if actions:
                all_actions.extend(actions)

        if all_actions:
            merged["immediate_actions_required"] = list(set(all_actions))  # 去重

        fee_context = self._extract_fee_context(contract_text, {}) if contract_text else {}
        explicit_values = self._merge_explicit_values(
            results,
            fee_context.get("explicit_values", {}),
        )
        merged["explicit_values"] = explicit_values
        merged["utilities_check"] = self._merge_utilities_check(
            results,
            fee_context.get("utilities", {}),
            location,
        )
        merged["deposit_check"] = self._merge_deposit_check(results, explicit_values)
        merged["total_cost_analysis"] = self._merge_total_cost_analysis(
            results,
            explicit_values,
            merged["utilities_check"],
        )

        return merged

    def _merge_explicit_values(self, results: List[Dict], extracted: Dict) -> Dict:
        merged = dict(extracted)
        for result in results:
            values = result.get("explicit_values", {}) or {}
            for key, value in values.items():
                if value in (None, "", 0, 0.0):
                    continue
                if merged.get(key) in (None, "", 0, 0.0):
                    merged[key] = value
        return merged

    def _merge_utilities_check(
        self,
        results: List[Dict],
        extracted_utilities: Dict,
        location: str,
    ) -> Dict:
        merged = self._check_utilities(extracted_utilities, location)

        for utility_key in ("water", "electricity", "gas"):
            best = merged.get(utility_key, {}).copy()
            for result in results:
                current = (result.get("utilities_check", {}) or {}).get(utility_key, {}) or {}
                if self._score_utility_check(current) > self._score_utility_check(best):
                    best = current
            merged[utility_key] = best

        return merged

    def _score_utility_check(self, utility: Dict) -> tuple[int, float]:
        charged = self._coerce_number(utility.get("charged"))
        explicit_score = 2 if charged > 0 else 0
        issue_score = 1 if utility.get("issue") else 0
        return explicit_score + issue_score, charged

    def _merge_deposit_check(self, results: List[Dict], explicit_values: Dict) -> Dict:
        best = {}
        best_amount = -1.0
        for result in results:
            current = result.get("deposit_check", {}) or {}
            amount = self._coerce_number(current.get("amount"))
            if amount > best_amount:
                best = current
                best_amount = amount

        if best_amount > 0:
            return best

        amount = self._coerce_number(explicit_values.get("deposit"))
        monthly_rent = self._coerce_number(explicit_values.get("monthly_rent"))
        return self._check_deposit(amount, monthly_rent)

    def _merge_total_cost_analysis(
        self,
        results: List[Dict],
        explicit_values: Dict,
        utilities_check: Dict,
    ) -> Dict:
        monthly_rent = self._coerce_number(explicit_values.get("monthly_rent"))
        recalculated = self._calculate_total_cost(monthly_rent, utilities_check)
        best = {}
        best_monthly_total = -1.0
        for result in results:
            current = result.get("total_cost_analysis", {}) or {}
            monthly_total = self._coerce_number(current.get("monthly_total"))
            if monthly_total > best_monthly_total:
                best = current
                best_monthly_total = monthly_total

        merged = dict(best or {})
        merged.update(
            {
                "monthly_base": recalculated.get("monthly_base"),
                "estimated_utilities": recalculated.get("estimated_utilities"),
                "monthly_total": recalculated.get("monthly_total"),
                "yearly_total": recalculated.get("yearly_total"),
                "market_comparison": recalculated.get("market_comparison"),
            }
        )
        return merged

    def calculate(
        self,
        entities: Dict,
        location: str = "beijing",
        contract_text: Optional[str] = None,
    ) -> Dict:
        fee_context = self._extract_fee_context(contract_text or "", entities)
        monthly_rent = self._coerce_number(
            fee_context.get("monthly_rent") or entities.get("monthly_rent")
        )
        deposit, inferred, inference_method, inference_source = self._resolve_deposit(
            entities=entities,
            contract_text=contract_text,
            monthly_rent=monthly_rent,
        )

        deterministic_result = self._calculate_deterministic_with_deposit(
            monthly_rent=monthly_rent,
            deposit=deposit,
            utilities=fee_context.get("utilities") or {},
            location=location,
            deposit_inferred=inferred,
            inference_method=inference_method,
            inference_source=inference_source,
            explicit_values=fee_context.get("explicit_values"),
            implicit_values=fee_context.get("implicit_values"),
            hidden_costs=fee_context.get("hidden_costs"),
            ambiguous_clauses=fee_context.get("ambiguous_clauses"),
        )

        if not self.use_llm:
            return deterministic_result

        try:
            # 传递 contract_text 参数给 refine_with_llm
            return self.refine_with_llm(entities, location, deterministic_result, contract_text or "")
        except Exception as exc:
            print(f"Beaver Calculator LLM refinement failed: {exc}")
            return deterministic_result

    def calculate_deterministic(
        self,
        entities: Dict,
        location: str,
        contract_text: Optional[str] = None,
    ) -> Dict:
        """Backward-compatible deterministic path, now with optional contract text."""
        fee_context = self._extract_fee_context(contract_text or "", entities)
        monthly_rent = self._coerce_number(
            fee_context.get("monthly_rent") or entities.get("monthly_rent")
        )
        deposit, inferred, inference_method, inference_source = self._resolve_deposit(
            entities=entities,
            contract_text=contract_text,
            monthly_rent=monthly_rent,
        )
        return self._calculate_deterministic_with_deposit(
            monthly_rent=monthly_rent,
            deposit=deposit,
            utilities=fee_context.get("utilities") or {},
            location=location,
            deposit_inferred=inferred,
            inference_method=inference_method,
            inference_source=inference_source,
            explicit_values=fee_context.get("explicit_values"),
            implicit_values=fee_context.get("implicit_values"),
            hidden_costs=fee_context.get("hidden_costs"),
            ambiguous_clauses=fee_context.get("ambiguous_clauses"),
        )

    def refine_with_llm(self, entities: Dict, location: str, deterministic_result: Dict, contract_text: str = "") -> Dict:
        """
        使用 LLM 复核确定性分析结果
        注意：此方法需要 contract_text 参数以匹配新的 prompt 模板
        """
        official = self.official_prices.get(location.lower(), self.official_prices["beijing"])

        # 如果没有提供 contract_text，尝试从 entities 构建简化文本
        if not contract_text:
            utilities = entities.get("utilities") or {}
            contract_text = f"""
月租金: {entities.get("monthly_rent", "未知")}元
押金: {entities.get("deposit", "未知")}元
租期: {entities.get("lease_term", "未知")}
付款方式: {entities.get("payment_method", "未知")}
水费: {utilities.get("water", "未知")}元
电费: {utilities.get("electricity", "未知")}元
燃气费: {utilities.get("gas", "未知")}元
违约条款: {entities.get("penalty_clause", "未明确")}
            """.strip()

        # 使用新的 prompt 模板格式
        print(
            "[Beaver Calculator] invoking LLM for refinement "
            f"(location={location}, contract_text_len={len(contract_text)})"
        )
        prompt = beaver_calculator_prompt.ANALYSIS_PROMPT_TEMPLATE.format(
            contract_text=contract_text,
            location=location,
            official_water=official["water"],
            official_electricity=official["electricity"],
            official_gas=official["gas"]
        )

        # 使用统一的 API 调用方法
        response_text = self.llm.call(self._build_llm_messages(prompt))

        result = extract_json_payload(response_text)
        if not self._validate_result(result):
            raise ValueError("Beaver Calculator returned an incomplete payload.")
        print("[Beaver Calculator] LLM returned a valid refinement payload")
        return result

    def _validate_result(self, result: Dict) -> bool:
        return all(key in result for key in ["deposit_check", "utilities_check", "total_cost_analysis"])

    def _build_llm_messages(self, prompt: str) -> List[Dict]:
        # Owl 在当前 Claude relay 上使用单 user prompt 更稳定，这里与之对齐。
        if self.api_type == "claude":
            return [
                {
                    "role": "user",
                    "content": f"{beaver_calculator_prompt.SYSTEM_PROMPT}\n\n{prompt}",
                }
            ]

        return [
            {"role": "system", "content": beaver_calculator_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

    def _coerce_number(self, value) -> float:
        try:
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    def _extract_fee_context(self, contract_text: str, entities: Dict) -> Dict:
        monthly_rent = self._extract_monthly_rent(contract_text) or self._coerce_number(
            entities.get("monthly_rent")
        )
        utilities = (
            self._extract_utility_values(contract_text)
            if contract_text.strip()
            else self._normalize_entity_utilities(entities.get("utilities") or {})
        )
        explicit_values = {
            "monthly_rent": monthly_rent,
            "deposit": self._coerce_number(entities.get("deposit")),
            "payment_method": self._extract_payment_method(contract_text),
            "water_price": self._coerce_number(utilities["water"].get("charged")),
            "electricity_price": self._coerce_number(
                utilities["electricity"].get("charged")
            ),
            "gas_price": self._coerce_number(utilities["gas"].get("charged")),
            "lease_term": entities.get("lease_term") or "",
        }

        ambiguous_items = []
        for utility_key, detail in utilities.items():
            if detail.get("pricing_mode") != "ambiguous":
                continue
            ambiguous_items.append(
                {
                    "clause": detail.get("source") or f"{utility_key} 收费条款",
                    "issue": detail.get("issue")
                    or f"{utility_key} 收费标准未明确",
                    "inference": "合同提到了收费，但没有给出明确单价，需要补充确认。",
                }
            )

        return {
            "monthly_rent": monthly_rent,
            "utilities": utilities,
            "explicit_values": explicit_values,
            "implicit_values": {},
            "hidden_costs": [],
            "ambiguous_clauses": {
                "count": len(ambiguous_items),
                "items": ambiguous_items,
            },
        }

    def _normalize_entity_utilities(self, utilities: Dict) -> Dict[str, Dict]:
        normalized: Dict[str, Dict] = {}
        for utility_key in ("water", "electricity", "gas"):
            charged = self._coerce_number(utilities.get(utility_key))
            normalized[utility_key] = {
                "charged": charged,
                "pricing_mode": "explicit" if charged > 0 else "missing",
                "source": "",
            }
        return normalized

    def _extract_monthly_rent(self, contract_text: str) -> float:
        patterns = [
            r"(?:月租金|租金(?:标准)?)(?:为|是|:|：)?\s*([0-9]+(?:\.[0-9]+)?)\s*元",
            r"每月租金(?:为|是|:|：)?\s*([0-9]+(?:\.[0-9]+)?)\s*元",
        ]
        for pattern in patterns:
            match = re.search(pattern, contract_text)
            if match:
                return self._coerce_number(match.group(1))
        return 0.0

    def _extract_payment_method(self, contract_text: str) -> str:
        match = re.search(
            r"(押[一二三四五六七八九十1234567890]+付[一二三四五六七八九十1234567890]+)",
            contract_text,
        )
        return match.group(1) if match else ""

    def _extract_utility_values(self, contract_text: str) -> Dict[str, Dict]:
        return {
            "water": self._extract_single_utility(
                contract_text,
                utility_key="water",
                aliases=["水费", "水价", "水费单价", "水费标准", "水电费", "水电"],
                explicit_patterns=[
                    r"(?:水费|水价|水费单价|水费标准)[^\n，。；;]{0,12}?([0-9]+(?:\.[0-9]+)?)\s*元\s*(?:/|每)?\s*(?:吨|方|立方米|立方|m3)",
                ],
                ambiguous_markers=["按实际", "实际用量", "按民用", "民用标准", "另计", "据实"],
                issue_label="水费收费标准未明确，需补充确认单价",
            ),
            "electricity": self._extract_single_utility(
                contract_text,
                utility_key="electricity",
                aliases=["电费", "电价", "电费单价", "电费标准", "水电费", "水电"],
                explicit_patterns=[
                    r"(?:电费|电价|电费单价|电费标准)[^\n，。；;]{0,12}?([0-9]+(?:\.[0-9]+)?)\s*元\s*(?:/|每)?\s*(?:度|千瓦时|kwh|KWH)",
                ],
                ambiguous_markers=["按实际", "实际用量", "按民用", "民用标准", "另计", "据实"],
                issue_label="电费收费标准未明确，需补充确认单价",
            ),
            "gas": self._extract_single_utility(
                contract_text,
                utility_key="gas",
                aliases=["燃气费", "燃气", "天然气费", "天然气", "燃气单价", "燃气标准"],
                explicit_patterns=[
                    r"(?:燃气费|燃气|天然气费|天然气|燃气单价|燃气标准)[^\n，。；;]{0,12}?([0-9]+(?:\.[0-9]+)?)\s*元\s*(?:/|每)?\s*(?:方|立方米|立方|m3)",
                ],
                ambiguous_markers=["按实际", "实际用量", "按民用", "民用标准", "另计", "据实"],
                issue_label="燃气费收费标准未明确，需补充确认单价",
            ),
        }

    def _extract_single_utility(
        self,
        contract_text: str,
        *,
        utility_key: str,
        aliases: List[str],
        explicit_patterns: List[str],
        ambiguous_markers: List[str],
        issue_label: str,
    ) -> Dict:
        for pattern in explicit_patterns:
            match = re.search(pattern, contract_text, flags=re.IGNORECASE)
            if match:
                return {
                    "charged": self._coerce_number(match.group(1)),
                    "pricing_mode": "explicit",
                    "source": match.group(0),
                }

        fragments = re.split(r"[。；;\n\r]", contract_text)
        for fragment in fragments:
            normalized = fragment.strip()
            if not normalized:
                continue
            if not any(alias in normalized for alias in aliases):
                continue
            if any(marker in normalized for marker in ambiguous_markers):
                return {
                    "charged": 0.0,
                    "pricing_mode": "ambiguous",
                    "source": normalized[:180],
                    "issue": issue_label,
                }

        return {
            "charged": 0.0,
            "pricing_mode": "missing",
            "source": "",
        }

    def _resolve_deposit(
        self,
        *,
        entities: Dict,
        contract_text: Optional[str],
        monthly_rent: float,
    ) -> tuple[float, bool, Optional[str], Optional[str]]:
        deposit = self._coerce_number(entities.get("deposit"))
        inferred = False
        inference_method = None
        inference_source = None

        if deposit == 0 and contract_text and monthly_rent > 0:
            inferred_result = self._infer_deposit(contract_text, monthly_rent)
            if inferred_result:
                deposit = inferred_result["amount"]
                inferred = True
                inference_method = inferred_result["method"]
                inference_source = inferred_result["source"]
                print(
                    "[Beaver] inferred deposit "
                    f"{deposit} from contract text via {inference_method}: {inference_source}"
                )

        return deposit, inferred, inference_method, inference_source

    def _check_deposit(self, deposit: float, monthly_rent: float) -> Dict:
        if monthly_rent <= 0:
            return {
                "amount": deposit,
                "legal_limit": 0,
                "compliant": True,
                "overcharge_amount": 0,
                "issue": None,
                "suggestion": None,
            }

        legal_limit = monthly_rent * self.compliance_thresholds["deposit_multiplier"]
        compliant = deposit <= legal_limit
        overcharge = max(0, deposit - legal_limit)

        return {
            "amount": deposit,
            "legal_limit": legal_limit,
            "compliant": compliant,
            "overcharge_amount": round(overcharge, 2),
            "issue": f"押金超过法定上限 {overcharge:.0f} 元" if not compliant else None,
            "suggestion": f"建议修改为 {legal_limit:.0f} 元（一个月租金）" if not compliant else None,
        }

    def _check_utilities(self, utilities: Dict, location: str) -> Dict:
        official = self.official_prices.get(
            location.lower(), self.official_prices["beijing"]
        )
        result = {}

        for utility_type in ["water", "electricity", "gas"]:
            utility_value = utilities.get(utility_type, {})
            if isinstance(utility_value, dict):
                charged = self._coerce_number(utility_value.get("charged"))
                pricing_mode = utility_value.get(
                    "pricing_mode", "explicit" if charged > 0 else "missing"
                )
                source = utility_value.get("source")
                preset_issue = utility_value.get("issue")
            else:
                charged = self._coerce_number(utility_value)
                pricing_mode = "explicit" if charged > 0 else "missing"
                source = None
                preset_issue = None

            official_price = official.get(utility_type, 0)

            if pricing_mode == "explicit" and charged > 0 and official_price > 0:
                overcharge_rate = (charged - official_price) / official_price * 100
                markup_limit = (
                    official_price * self.compliance_thresholds["utility_markup_limit"]
                )
                overcharged = charged > markup_limit
                result[utility_type] = {
                    "charged": charged,
                    "official": official_price,
                    "pricing_mode": pricing_mode,
                    "overcharge_rate": round(overcharge_rate, 1),
                    "overcharged": overcharged,
                    "issue": f"{utility_type} 加价 {overcharge_rate:.0f}%"
                    if overcharged
                    else None,
                    "suggestion": f"要求按官方价格 {official_price} 元收费"
                    if overcharged
                    else None,
                    "source": source,
                }
            else:
                result[utility_type] = {
                    "charged": charged,
                    "official": official_price,
                    "pricing_mode": pricing_mode,
                    "overcharge_rate": 0,
                    "overcharged": False,
                    "issue": preset_issue,
                    "suggestion": "要求补充明确收费单价或计费标准"
                    if pricing_mode == "ambiguous"
                    else None,
                    "source": source,
                }

        return result

    def _calculate_total_cost(self, monthly_rent: float, utilities_check: Dict) -> Dict:
        estimated_utilities = 0.0
        usage_estimates = {"water": 10, "electricity": 200, "gas": 30}
        for utility_type, check_result in utilities_check.items():
            if check_result.get("official", 0) > 0:
                estimated_utilities += check_result["official"] * usage_estimates.get(utility_type, 0)

        if estimated_utilities == 0:
            estimated_utilities = 200

        monthly_total = monthly_rent + estimated_utilities
        yearly_total = monthly_total * 12
        return {
            "monthly_base": monthly_rent,
            "estimated_utilities": round(estimated_utilities, 2),
            "monthly_total": round(monthly_total, 2),
            "yearly_total": round(yearly_total, 2),
            "market_comparison": self._get_market_comparison(monthly_rent),
        }

    def _get_market_comparison(self, monthly_rent: float) -> str:
        if monthly_rent < 3000:
            return "低于市场平均水平"
        if monthly_rent < 6000:
            return "符合市场平均水平"
        if monthly_rent < 10000:
            return "略高于市场平均水平"
        return "明显高于市场平均水平"

    def _infer_deposit(self, contract_text: str, monthly_rent: float) -> Optional[Dict]:
        """Infer deposit amount from contract text using regex first, then web search."""
        digit_pattern = r"押\s*(\d+)\s*付\s*(\d+)"
        match = re.search(digit_pattern, contract_text)
        if match:
            deposit_months = int(match.group(1))
            return {
                "amount": monthly_rent * deposit_months,
                "method": "regex_pattern",
                "source": f"押{match.group(1)}付{match.group(2)}",
            }

        chinese_number_map = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
        }
        chinese_pattern = r"押\s*([一二三四五六123456])\s*付\s*([一二三四五六123456])"
        match = re.search(chinese_pattern, contract_text)
        if match:
            deposit_months = chinese_number_map[match.group(1)]
            payment_months = chinese_number_map[match.group(2)]
            return {
                "amount": monthly_rent * deposit_months,
                "method": "regex_pattern",
                "source": f"押{deposit_months}付{payment_months}",
            }

        # 直接金额模式（优先级最高）
        amount_patterns = [
            (r"(?:履约)?保证金[为:]?\s*(?:人民币)?(\d+(?:,\d{3})*(?:\.\d+)?)\s*元", "保证金金额"),
            (r"押金[为:]?\s*(?:人民币)?(\d+(?:,\d{3})*(?:\.\d+)?)\s*元", "押金金额"),
            (r"(?:履约)?保证金\s*(\d+(?:,\d{3})*(?:\.\d+)?)", "保证金金额"),
            (r"押金\s*(\d+(?:,\d{3})*(?:\.\d+)?)", "押金金额"),
        ]
        for pattern, source_template in amount_patterns:
            match = re.search(pattern, contract_text)
            if match:
                amount_str = match.group(1).replace(",", "")
                amount = float(amount_str)
                return {
                    "amount": amount,
                    "method": "regex_amount",
                    "source": f"{source_template}: {amount}元",
                }

        oral_patterns = [
            (r"先交(\d+)个月押金", "先交X个月押金"),
            (r"押金(\d+)个月", "押金X个月"),
            (r"按(\d+)个月作为押金", "按X个月作为押金"),
            (r"押金为(\d+)个月租金", "押金为X个月租金"),
        ]
        for pattern, source_template in oral_patterns:
            match = re.search(pattern, contract_text)
            if match:
                deposit_months = int(match.group(1))
                return {
                    "amount": monthly_rent * deposit_months,
                    "method": "regex_pattern",
                    "source": source_template.replace("X", str(deposit_months)),
                }

        search_clause = self._extract_sentence_with_keywords(
            contract_text,
            ["押金", "保证金", "押", "付款方式", "付"],
        )
        if not search_clause:
            return None

        return self._search_deposit_meaning(search_clause, monthly_rent)

    def _extract_sentence_with_keywords(self, contract_text: str, keywords: list[str]) -> Optional[str]:
        compact_text = re.sub(r"\s+", " ", contract_text).strip()
        if not compact_text:
            return None

        fragments = re.split(r"[。；;！？!\n\r]", compact_text)
        for fragment in fragments:
            normalized = fragment.strip()
            if normalized and all(keyword in normalized for keyword in keywords[:2]):
                return normalized[:240]
        for fragment in fragments:
            normalized = fragment.strip()
            if normalized and any(keyword in normalized for keyword in keywords):
                return normalized[:240]
        return compact_text[:240]

    def _search_deposit_meaning(self, contract_text: str, monthly_rent: float) -> Optional[Dict]:
        # Web search 功能暂时禁用，因为已移除 Anthropic SDK
        # 如需启用，需要实现基于 requests 的 web search 调用
        if not self.use_llm or not self.web_search_enabled:
            return None

        # 暂时返回 None，不使用 web search
        return None

        response_text = getattr(response, "output_text", "") or ""
        if not response_text:
            return None

        try:
            payload = extract_json_payload(response_text)
        except Exception as exc:
            print(f"Beaver Calculator web search parse failed: {exc}")
            return None

        raw_deposit_months = payload.get("deposit_months")
        try:
            deposit_months = int(raw_deposit_months) if raw_deposit_months is not None else None
        except (TypeError, ValueError):
            return None

        confidence = payload.get("confidence", 0)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0

        should_infer = payload.get("should_infer")
        if should_infer is None:
            should_infer = deposit_months is not None

        if not should_infer or deposit_months is None:
            return None
        if deposit_months < 0 or deposit_months > 12:
            return None
        if confidence_value < 0.5:
            return None

        return {
            "amount": monthly_rent * deposit_months,
            "method": "web_search",
            "source": contract_text,
        }

    def _calculate_deterministic_with_deposit(
        self,
        monthly_rent: float,
        deposit: float,
        utilities: Dict,
        location: str,
        deposit_inferred: bool,
        inference_method: Optional[str],
        inference_source: Optional[str],
        explicit_values: Optional[Dict] = None,
        implicit_values: Optional[Dict] = None,
        hidden_costs: Optional[List[Dict]] = None,
        ambiguous_clauses: Optional[Dict] = None,
    ) -> Dict:
        deposit_check = self._check_deposit(deposit, monthly_rent)
        if deposit_inferred:
            deposit_check["inferred"] = True
            deposit_check["inference_method"] = inference_method
            deposit_check["inference_source"] = inference_source
        else:
            deposit_check["inferred"] = False

        utilities_check = self._check_utilities(utilities, location)
        total_cost = self._calculate_total_cost(monthly_rent, utilities_check)

        return {
            "deposit_check": deposit_check,
            "utilities_check": utilities_check,
            "total_cost_analysis": total_cost,
            "explicit_values": explicit_values or {},
            "implicit_values": implicit_values or {},
            "hidden_costs": hidden_costs or [],
            "ambiguous_clauses": ambiguous_clauses or {"count": 0, "items": []},
        }
