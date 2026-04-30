"""Regression checks for analysis runtime orchestration."""

from __future__ import annotations

import sys
import types
import unittest
import json
from pathlib import Path
from unittest.mock import patch


BACKEND_SRC = Path(__file__).resolve().parent / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))


fake_retriever_module = types.ModuleType("knowledge.retriever")


class _FakeRetriever:
    def search_all(self, _query, top_k=3):
        return {"legal_docs": [], "cases": []}


def _get_retriever():
    return _FakeRetriever()


fake_retriever_module.get_retriever = _get_retriever
sys.modules["knowledge.retriever"] = fake_retriever_module

import analysis_runtime  # noqa: E402
from agents.beaver_calculator import BeaverCalculator  # noqa: E402
from agents.cat_reporter import CatReporter  # noqa: E402
from agents.dog_retriever import DogRetriever  # noqa: E402
from prompts import beaver_calculator_prompt_v3 as beaver_prompt  # noqa: E402
from prompts import cat_reporter_prompt  # noqa: E402
from prompts import dog_retriever_prompt  # noqa: E402


class _FakeBeaver:
    use_llm = True

    def analyze_from_text(self, contract_text, location):
        return {
            "deposit_check": {"amount": 4980},
            "utilities_check": {},
            "total_cost_analysis": {},
            "analysis_source": contract_text[:8],
            "location": location,
        }

    def refine_with_llm(self, entities, location, deterministic_result, contract_text):
        return {
            **deterministic_result,
            "refined": True,
            "contract_preview": contract_text[:8],
            "location": location,
            "monthly_rent": entities.get("monthly_rent"),
        }


class AnalysisRuntimeRegressionTests(unittest.TestCase):
    def test_dog_uses_single_user_message_for_claude_stability(self) -> None:
        dog = DogRetriever.__new__(DogRetriever)
        dog.api_type = "claude"
        dog.model = "claude-sonnet-4-6"
        dog.temperature = 0.1

        payload = dog._build_llm_payload("系统提示", "用户提示")

        self.assertNotIn("system", payload)
        self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertIn("系统提示", payload["messages"][0]["content"])
        self.assertIn("用户提示", payload["messages"][0]["content"])

    def test_cat_uses_single_user_message_for_claude_stability(self) -> None:
        cat = CatReporter.__new__(CatReporter)
        cat.api_type = "claude"
        cat.model = "claude-sonnet-4-6"
        cat.temperature = 0.3

        messages = cat._build_llm_messages("报告 prompt")

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn(cat_reporter_prompt.COMPACT_SYSTEM_PROMPT, messages[0]["content"])
        self.assertIn("报告 prompt", messages[0]["content"])

    def test_dog_compacts_risk_items_for_prompt_stability(self) -> None:
        dog = DogRetriever.__new__(DogRetriever)
        risks = [
            {
                "risk_level": "high" if i < 10 else "medium",
                "issue": f"风险说明{i}",
                "clause": "原文条款" * 40,
                "suggestion": "修改建议" * 20,
            }
            for i in range(20)
        ]

        compact = dog._compact_risk_items(risks)

        self.assertLessEqual(len(compact), 12)
        self.assertTrue(all(len(item["clause"]) <= 120 for item in compact))
        self.assertEqual(compact[0]["risk_level"], "high")

    def test_dog_splits_risks_into_budgeted_chunks(self) -> None:
        dog = DogRetriever.__new__(DogRetriever)
        risks = [
            {
                "risk_id": f"risk_{i}",
                "risk_level": "high",
                "issue": f"风险说明{i}" * 12,
                "clause": "原文条款" * 40,
            }
            for i in range(18)
        ]

        top_level = dog._split_into_top_level_groups(risks, groups=3)
        chunks = dog._split_until_within_budget(top_level, target_bytes=1000)

        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(dog._estimate_payload_size(chunk) <= 1000 for chunk in chunks))

    def test_dog_dedupes_reference_items(self) -> None:
        dog = DogRetriever.__new__(DogRetriever)
        deduped = dog._dedupe_reference_items(
            [
                {"title": "法条A", "content": "内容A"},
                {"title": "法条A", "content": "内容A"},
                {"title": "法条B", "content": "内容B"},
            ],
            key_fields=("title", "content"),
        )

        self.assertEqual(len(deduped), 2)

    def test_cat_builds_three_category_summaries(self) -> None:
        cat = CatReporter.__new__(CatReporter)
        summaries = cat._build_category_summaries(
            entities={
                "lessor": "甲方",
                "lessee": "乙方",
                "monthly_rent": 5000,
                "deposit": 5000,
                "lease_term": "12个月",
            },
            risk_items=[
                {"risk_level": "high", "issue": "风险1", "clause": "条款1", "legal_basis": "依据1"},
                {"risk_level": "medium", "issue": "风险2", "clause": "条款2", "legal_basis": "依据2"},
            ],
            legal_references=[
                {"title": "法条A", "content": "内容A", "application": "适用A", "relevance": "相关A"}
            ],
            case_references=[
                {"title": "案例A", "summary": "摘要A", "relevance": "相关案例A"}
            ],
            calculations={"deposit_check": {"compliant": True}},
        )

        self.assertIn("entities", summaries)
        self.assertIn("owl", summaries)
        self.assertIn("dog", summaries)
        self.assertIn("beaver", summaries)
        self.assertEqual(summaries["owl"]["total_risks"], 2)
        self.assertEqual(summaries["dog"]["legal_reference_count"], 1)
        self.assertEqual(summaries["dog"]["case_reference_count"], 1)
        self.assertLess(
            len(json.dumps(summaries["owl"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
            1000,
        )
        self.assertLess(
            len(json.dumps(summaries["dog"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
            1000,
        )

    def test_cat_compacts_risk_items_for_prompt_stability(self) -> None:
        cat = CatReporter.__new__(CatReporter)
        risks = [
            {
                "risk_level": "high" if i < 8 else "medium",
                "issue": f"风险说明{i}",
                "clause": "原文条款" * 40,
                "legal_basis": "法律依据" * 20,
                "suggestion": "修改建议" * 20,
            }
            for i in range(18)
        ]

        compact = cat._compact_risk_items(risks)

        self.assertLessEqual(len(compact), 12)
        self.assertTrue(all(len(item["clause"]) <= 120 for item in compact))
        self.assertEqual(compact[0]["risk_level"], "high")

    def test_beaver_uses_single_user_message_for_claude_stability(self) -> None:
        beaver = BeaverCalculator.__new__(BeaverCalculator)
        beaver.api_type = "claude"

        messages = beaver._build_llm_messages("测试 prompt")

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn(beaver_prompt.SYSTEM_PROMPT, messages[0]["content"])
        self.assertIn("测试 prompt", messages[0]["content"])

    def test_beaver_refine_step_prefers_full_text_analysis(self) -> None:
        state = {
            "contract_text": "押一付三，押金4980元，水电另计",
            "location": "shanghai",
            "entities": {"monthly_rent": 4980},
            "calculations": {"deposit_check": {"amount": 4980}},
        }

        with patch.object(analysis_runtime, "beaver", _FakeBeaver()):
            next_state = analysis_runtime._beaver_refine_step(state)

        self.assertTrue(
            next_state["calculations"]["analysis_source"].startswith("押一付三，押金")
        )
        self.assertEqual(next_state["calculations"]["location"], "shanghai")
        self.assertEqual(
            next_state["calculations"]["analysis_metadata"]["mode"], "llm_full_text"
        )
        self.assertTrue(
            next_state["calculations"]["analysis_metadata"]["llm_success"]
        )

    def test_beaver_refine_step_passes_contract_text(self) -> None:
        state = {
            "contract_text": "押一付三，押金4980元，水电另计",
            "location": "shanghai",
            "entities": {"monthly_rent": 4980},
            "calculations": {"deposit_check": {"amount": 4980}},
        }

        fake_beaver = _FakeBeaver()
        fake_beaver.analyze_from_text = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("full-text failed")
        )

        with patch.object(analysis_runtime, "beaver", fake_beaver):
            next_state = analysis_runtime._beaver_refine_step(state)

        self.assertTrue(next_state["calculations"]["refined"])
        self.assertTrue(
            next_state["calculations"]["contract_preview"].startswith("押一付三，押金")
        )
        self.assertEqual(next_state["calculations"]["location"], "shanghai")
        self.assertEqual(next_state["calculations"]["monthly_rent"], 4980)
        self.assertEqual(
            next_state["calculations"]["analysis_metadata"]["mode"], "llm_refine"
        )

    def test_beaver_merges_non_zero_utility_values_across_chunks(self) -> None:
        beaver = BeaverCalculator.__new__(BeaverCalculator)
        beaver.official_prices = {
            "beijing": {"water": 5.0, "electricity": 0.5583, "gas": 2.63}
        }
        beaver.compliance_thresholds = {
            "deposit_multiplier": 1.0,
            "utility_markup_limit": 1.5,
        }

        merged = beaver._merge_analysis_results(
            [
                {
                    "deposit_check": {"amount": 0, "legal_limit": 0, "compliant": True},
                    "utilities_check": {
                        "water": {"charged": 0, "official": 5.0, "overcharged": False, "issue": None},
                        "electricity": {"charged": 0, "official": 0.5583, "overcharged": False, "issue": None},
                        "gas": {"charged": 0, "official": 2.63, "overcharged": False, "issue": None},
                    },
                    "total_cost_analysis": {"monthly_total": 0},
                    "explicit_values": {"monthly_rent": 0},
                },
                {
                    "deposit_check": {"amount": 8400, "legal_limit": 8400, "compliant": True},
                    "utilities_check": {
                        "water": {"charged": 8.5, "official": 5.0, "overcharged": True, "issue": "水费过高"},
                        "electricity": {"charged": 1.35, "official": 0.5583, "overcharged": True, "issue": "电费过高"},
                        "gas": {"charged": 4.9, "official": 2.63, "overcharged": True, "issue": "燃气费过高"},
                    },
                    "total_cost_analysis": {"monthly_total": 9999},
                    "explicit_values": {"monthly_rent": 8400, "deposit": 8400},
                },
            ],
            "月租金8400元，押金8400元，水费8.5元/立方米，电费1.35元/度，燃气费4.9元/立方米",
            "beijing",
        )

        self.assertEqual(merged["utilities_check"]["water"]["charged"], 8.5)
        self.assertEqual(merged["utilities_check"]["electricity"]["charged"], 1.35)
        self.assertEqual(merged["deposit_check"]["amount"], 8400)


if __name__ == "__main__":
    unittest.main()
