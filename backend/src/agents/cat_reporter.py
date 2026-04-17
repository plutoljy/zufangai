from openai import OpenAI
from typing import Dict, List
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from prompts import cat_reporter_prompt

class CatReporter:
    """橘猫报告师 - 生成分析报告"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"  # 使用最新模型生成高质量报告
        self.temperature = 0.3  # 稍高一点,让报告更自然
        print("[OK] Cat Reporter: 使用 OpenAI GPT-4o")

    def generate_report(
        self,
        entities: Dict,
        risk_items: List[Dict],
        legal_references: List[Dict],
        calculations: Dict
    ) -> Dict:
        """
        生成分析报告

        Args:
            entities: 合同实体
            risk_items: 风险条款
            legal_references: 法律依据
            calculations: 费用分析

        Returns:
            {
                "report_markdown": str,
                "summary": {...}
            }
        """
        # 1. 构建prompt
        prompt = cat_reporter_prompt.REPORT_GENERATION_PROMPT.format(
            entities_json=json.dumps(entities, ensure_ascii=False, indent=2),
            risk_count=len(risk_items),
            risk_items_json=json.dumps(risk_items, ensure_ascii=False, indent=2),
            legal_references_json=json.dumps(legal_references, ensure_ascii=False, indent=2),
            calculations_json=json.dumps(calculations, ensure_ascii=False, indent=2)
        )

        # 2. 调用LLM生成报告
        try:
            messages = [
                {"role": "system", "content": cat_reporter_prompt.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                timeout=60  # 报告生成可能需要更长时间
            )

            report_markdown = response.choices[0].message.content

            # 3. 生成摘要
            summary = self._generate_summary(risk_items, calculations)

            return {
                "report_markdown": report_markdown,
                "summary": summary
            }
        except Exception as e:
            print(f"Cat Reporter error: {e}")
            # 返回简化版报告
            return {
                "report_markdown": self._generate_fallback_report(entities, risk_items),
                "summary": self._generate_summary(risk_items, calculations)
            }

    def _generate_summary(self, risk_items: List[Dict], calculations: Dict) -> Dict:
        """生成摘要统计"""
        high_risks = [r for r in risk_items if r.get("risk_level") == "high"]
        medium_risks = [r for r in risk_items if r.get("risk_level") == "medium"]
        low_risks = [r for r in risk_items if r.get("risk_level") == "low"]

        deposit_compliant = calculations.get("deposit_check", {}).get("compliant", True)

        return {
            "total_risks": len(risk_items),
            "high_risks": len(high_risks),
            "medium_risks": len(medium_risks),
            "low_risks": len(low_risks),
            "compliant": deposit_compliant and len(high_risks) == 0
        }

    def _generate_fallback_report(self, entities: Dict, risk_items: List[Dict]) -> str:
        """生成简化版报告 (LLM失败时使用)"""
        report = f"""# 租房合同分析报告

## 合同概况
- 出租方: {entities.get('lessor', '未知')}
- 承租方: {entities.get('lessee', '未知')}
- 月租金: {entities.get('monthly_rent', 0)}元
- 押金: {entities.get('deposit', 0)}元

## 风险警示
发现 {len(risk_items)} 项风险:

"""
        for i, risk in enumerate(risk_items, 1):
            report += f"{i}. {risk.get('issue', '未知风险')}\n"

        return report


if __name__ == "__main__":
    reporter = CatReporter()

    test_data = {
        "entities": {"lessor": "张三", "monthly_rent": 5000, "deposit": 10000},
        "risk_items": [{"risk_level": "high", "issue": "押金超限"}],
        "legal_references": [],
        "calculations": {"deposit_check": {"compliant": False}}
    }

    result = reporter.generate_report(**test_data)
    print(result["report_markdown"])
