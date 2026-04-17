"""
Beaver Calculator Agent - 海狸计算师
负责费用计算和合规性检查
"""
from typing import Dict, Optional
from openai import OpenAI
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from knowledge.retriever import get_retriever


class BeaverCalculator:
    """海狸计算师 - 费用计算和合规性检查"""

    def __init__(self):
        # 使用 DeepSeek API（兼容 OpenAI SDK）
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.model = settings.deepseek_model

        # 初始化知识库检索器（用于水电费标准）
        try:
            self.retriever = get_retriever()
            self.use_rag = True
            print("[OK] Beaver Calculator: 知识库已加载")
        except FileNotFoundError:
            print("[WARN] Beaver Calculator: 知识库未构建，使用默认数据")
            self.retriever = None
            self.use_rag = False
        # 官方价格数据 (简化版,后续从数据库读取)
        self.official_prices = {
            "beijing": {
                "water": 5.0,
                "electricity": 0.5583,
                "gas": 2.63
            },
            "shanghai": {
                "water": 3.45,
                "electricity": 0.617,
                "gas": 3.0
            },
            "guangzhou": {
                "water": 3.5,
                "electricity": 0.68,
                "gas": 3.45
            },
            "shenzhen": {
                "water": 3.2,
                "electricity": 0.68,
                "gas": 3.5
            }
        }

        # 合规性阈值
        self.compliance_thresholds = {
            "deposit_multiplier": 1.0,  # 押金不超过月租金
            "utility_markup_limit": 1.5  # 水电费加价不超过50%
        }

    def calculate(self, entities: Dict, location: str = "beijing") -> Dict:
        """
        计算费用并检查合规性

        Args:
            entities: 提取的实体信息
            location: 地理位置

        Returns:
            {
                "deposit_check": {...},
                "utilities_check": {...},
                "total_cost_analysis": {...}
            }
        """
        monthly_rent = entities.get("monthly_rent", 0)
        deposit = entities.get("deposit", 0)
        utilities = entities.get("utilities", {})

        # 1. 押金检查
        deposit_check = self._check_deposit(deposit, monthly_rent)

        # 2. 水电费检查
        utilities_check = self._check_utilities(utilities, location)

        # 3. 总成本分析
        total_cost = self._calculate_total_cost(monthly_rent, utilities_check)

        return {
            "deposit_check": deposit_check,
            "utilities_check": utilities_check,
            "total_cost_analysis": total_cost
        }

    def _check_deposit(self, deposit: float, monthly_rent: float) -> Dict:
        """检查押金合规性"""
        if monthly_rent <= 0:
            return {
                "amount": deposit,
                "legal_limit": 0,
                "compliant": True,
                "overcharge_amount": 0,
                "issue": None,
                "suggestion": None
            }

        legal_limit = monthly_rent * self.compliance_thresholds["deposit_multiplier"]
        compliant = deposit <= legal_limit
        overcharge = max(0, deposit - legal_limit)

        return {
            "amount": deposit,
            "legal_limit": legal_limit,
            "compliant": compliant,
            "overcharge_amount": round(overcharge, 2),
            "issue": f"押金超过法定上限{overcharge:.0f}元" if not compliant else None,
            "suggestion": f"建议修改为{legal_limit:.0f}元(一个月租金)" if not compliant else None
        }

    def _check_utilities(self, utilities: Dict, location: str) -> Dict:
        """检查水电费"""
        # 获取官方价格,默认使用北京价格
        official = self.official_prices.get(
            location.lower(),
            self.official_prices["beijing"]
        )

        result = {}
        utility_types = ["water", "electricity", "gas"]

        for utility_type in utility_types:
            charged = utilities.get(utility_type, 0)
            official_price = official.get(utility_type, 0)

            if charged > 0 and official_price > 0:
                overcharge_rate = (charged - official_price) / official_price * 100
                markup_limit = official_price * self.compliance_thresholds["utility_markup_limit"]
                overcharged = charged > markup_limit

                result[utility_type] = {
                    "charged": charged,
                    "official": official_price,
                    "overcharge_rate": round(overcharge_rate, 1),
                    "overcharged": overcharged,
                    "issue": f"{utility_type}费加价{overcharge_rate:.0f}%" if overcharged else None,
                    "suggestion": f"要求按官方价格{official_price}元收取" if overcharged else None
                }
            else:
                result[utility_type] = {
                    "charged": charged,
                    "official": official_price,
                    "overcharge_rate": 0,
                    "overcharged": False,
                    "issue": None,
                    "suggestion": None
                }

        return result

    def _calculate_total_cost(self, monthly_rent: float, utilities_check: Dict) -> Dict:
        """计算总成本"""
        # 预估水电费 (基于官方价格)
        estimated_utilities = 0
        for utility_type, check_result in utilities_check.items():
            if check_result.get("official", 0) > 0:
                # 假设平均用量: 水10吨, 电200度, 气30立方
                usage_estimates = {
                    "water": 10,
                    "electricity": 200,
                    "gas": 30
                }
                estimated_utilities += check_result["official"] * usage_estimates.get(utility_type, 0)

        # 如果没有官方价格数据,使用固定预估值
        if estimated_utilities == 0:
            estimated_utilities = 200

        monthly_total = monthly_rent + estimated_utilities
        yearly_total = monthly_total * 12

        # 市场比较 (简化版)
        market_comparison = self._get_market_comparison(monthly_rent)

        return {
            "monthly_base": monthly_rent,
            "estimated_utilities": round(estimated_utilities, 2),
            "monthly_total": round(monthly_total, 2),
            "yearly_total": round(yearly_total, 2),
            "market_comparison": market_comparison
        }

    def _get_market_comparison(self, monthly_rent: float) -> str:
        """获取市场比较结果"""
        # 简化的市场比较逻辑
        if monthly_rent < 3000:
            return "低于市场平均水平"
        elif monthly_rent < 6000:
            return "符合市场平均水平"
        elif monthly_rent < 10000:
            return "略高于市场平均水平"
        else:
            return "明显高于市场平均水平"


if __name__ == "__main__":
    calculator = BeaverCalculator()

    # 测试用例1: 押金超标 + 水电费加价
    test_entities_1 = {
        "monthly_rent": 5000,
        "deposit": 10000,
        "utilities": {
            "water": 9.0,
            "electricity": 1.5,
            "gas": 4.5
        }
    }

    print("=== 测试用例1: 押金超标 + 水电费加价 ===")
    result_1 = calculator.calculate(test_entities_1, "beijing")
    print(json.dumps(result_1, ensure_ascii=False, indent=2))

    # 测试用例2: 合规案例
    test_entities_2 = {
        "monthly_rent": 4000,
        "deposit": 4000,
        "utilities": {
            "water": 5.0,
            "electricity": 0.6,
            "gas": 2.7
        }
    }

    print("\n=== 测试用例2: 合规案例 ===")
    result_2 = calculator.calculate(test_entities_2, "beijing")
    print(json.dumps(result_2, ensure_ascii=False, indent=2))

    # 测试用例3: 上海地区
    test_entities_3 = {
        "monthly_rent": 6000,
        "deposit": 6000,
        "utilities": {
            "water": 3.5,
            "electricity": 0.7,
            "gas": 3.2
        }
    }

    print("\n=== 测试用例3: 上海地区 ===")
    result_3 = calculator.calculate(test_entities_3, "shanghai")
    print(json.dumps(result_3, ensure_ascii=False, indent=2))
