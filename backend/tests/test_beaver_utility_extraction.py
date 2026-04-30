from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agents.beaver_calculator import BeaverCalculator  # noqa: E402


def build_calculator() -> BeaverCalculator:
    calculator = BeaverCalculator.__new__(BeaverCalculator)
    calculator.official_prices = {
        "beijing": {"water": 5.0, "electricity": 0.5583, "gas": 2.63},
        "shanghai": {"water": 3.45, "electricity": 0.617, "gas": 3.0},
    }
    calculator.compliance_thresholds = {
        "deposit_multiplier": 1.0,
        "utility_markup_limit": 1.5,
    }
    calculator.use_llm = False
    calculator.web_search_enabled = False
    return calculator


def test_beaver_extracts_explicit_utility_prices_from_contract_text():
    calculator = build_calculator()

    result = calculator.calculate_deterministic(
        entities={},
        location="shanghai",
        contract_text="月租金 4980 元，水费 6 元/吨，电费 0.8 元/度，燃气费 3 元/方。",
    )

    assert result["utilities_check"]["water"]["charged"] == 6.0
    assert result["utilities_check"]["water"]["overcharged"] is True
    assert result["utilities_check"]["electricity"]["charged"] == 0.8
    assert result["utilities_check"]["electricity"]["overcharged"] is False


def test_beaver_marks_ambiguous_utility_pricing_when_contract_uses_actual_usage_only():
    calculator = build_calculator()

    result = calculator.calculate_deterministic(
        entities={},
        location="shanghai",
        contract_text="月租金 4980 元，水电费按实际用量收取，燃气费按民用标准执行。",
    )

    assert result["utilities_check"]["water"]["pricing_mode"] == "ambiguous"
    assert result["utilities_check"]["electricity"]["pricing_mode"] == "ambiguous"
    assert result["utilities_check"]["gas"]["pricing_mode"] == "ambiguous"
    assert "未明确" in result["utilities_check"]["water"]["issue"]
