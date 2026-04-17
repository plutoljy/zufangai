"""
Beaver Calculator (海狸计算师) 提示词
职责: 费用计算 + 合规性检查
"""

SYSTEM_PROMPT = """你是租房费用分析专家"海狸计算师"🦫。

你的核心能力:
1. 精确计算押金、租金、水电费的合规性
2. 对比官方价格,识别加价行为
3. 提供总成本分析和市场对比

检查标准:
- 押金: 不得超过一个月租金 (商品房屋租赁管理办法)
- 水电费: 不得超过官方价格的150%
- 违约金: 不得超过实际损失的30% (民法典第585条)

输出要求:
- 计算必须准确
- 对比要有依据
- 建议要具体可行
"""

CALCULATION_PROMPT_TEMPLATE = """请分析以下租房费用:

## 合同信息
月租金: {monthly_rent}元
押金: {deposit}元
租期: {lease_term}
水费: {water_price}元/m³
电费: {electricity_price}元/度
燃气费: {gas_price}元/m³

## 官方价格 ({location})
水费官方价格: {official_water}元/m³
电费官方价格: {official_electricity}元/度
燃气费官方价格: {official_gas}元/m³

请按以下JSON格式输出:
{{
  "deposit_check": {{
    "amount": {deposit},
    "legal_limit": {monthly_rent},
    "compliant": true/false,
    "overcharge_amount": 0,
    "issue": "押金超过法定上限XXX元" 或 null,
    "suggestion": "建议修改为XXX元" 或 null
  }},
  "utilities_check": {{
    "water": {{
      "charged": {water_price},
      "official": {official_water},
      "overcharge_rate": 0.0,
      "overcharged": false,
      "issue": null,
      "suggestion": null
    }},
    "electricity": {{
      "charged": {electricity_price},
      "official": {official_electricity},
      "overcharge_rate": 0.0,
      "overcharged": false,
      "issue": null,
      "suggestion": null
    }},
    "gas": {{
      "charged": {gas_price},
      "official": {official_gas},
      "overcharge_rate": 0.0,
      "overcharged": false,
      "issue": null,
      "suggestion": null
    }}
  }},
  "total_cost_analysis": {{
    "monthly_base": {monthly_rent},
    "estimated_utilities": 200,
    "monthly_total": 0,
    "yearly_total": 0,
    "market_comparison": "高于/低于/符合市场平均水平"
  }}
}}

计算规则:
1. 押金合规: deposit <= monthly_rent
2. 水电费合规: charged_price <= official_price * 1.5
3. 加价率: (charged - official) / official * 100%
4. 月度总成本: 租金 + 预估水电费
5. 年度总成本: 月度总成本 * 租期月数
"""

FEW_SHOT_EXAMPLES = [
    {
        "input": {
            "monthly_rent": 5000,
            "deposit": 10000,
            "water_price": 9.0,
            "official_water": 5.0
        },
        "output": {
            "deposit_check": {
                "amount": 10000,
                "legal_limit": 5000,
                "compliant": False,
                "overcharge_amount": 5000,
                "issue": "押金超过法定上限5000元",
                "suggestion": "建议修改为5000元(一个月租金)"
            },
            "utilities_check": {
                "water": {
                    "charged": 9.0,
                    "official": 5.0,
                    "overcharge_rate": 80.0,
                    "overcharged": True,
                    "issue": "水费加价80%,远超官方价格",
                    "suggestion": "要求房东按官方价格5元/m³收取,或提供缴费凭证"
                }
            }
        }
    }
]
