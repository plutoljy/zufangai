"""
规则引擎：基于正则表达式的风险识别
作为 LLM 分析的补充和 fallback
参考 Contract-Review-Copilot 的 PATTERN_RULES 设计
"""

import re
from typing import List, Dict, Optional

# 风险关键词
RISK_KEYWORDS = (
    "押金", "保证金", "违约金", "违约", "自动续租", "自动续约", "续租", "续约",
    "解约", "解除", "提前解除", "提前退租", "退租", "逾期", "滞纳金", "利息",
    "租金调整", "调整租金", "变更租金", "服务费", "管理费", "转租", "二房东",
    "租金贷", "贷款", "分期", "征信", "委托扣款", "维修", "修缮", "免责",
    "现状出租", "现有状态", "断水断电", "中介费", "水电", "返还", "通知",
    "原房东", "托管协议", "仲裁", "甲方所在地", "随时进入", "入户检查",
    "养宠", "宠物", "禁止转租", "口头承诺", "解释权", "交付", "设施清单"
)

# 风险识别规则
PATTERN_RULES = [
    {
        "name": "租金调整条款",
        "pattern": re.compile(r"甲方.{0,10}(有权|可以).{0,20}(调整|变更|上调).{0,12}(租金|服务费|管理费)"),
        "risk_level": "high",
        "issue": "合同赋予甲方单方调整租金或相关费用的权利，缺少乙方同意机制，属于明显不对等约定。",
        "suggestion": "改为：租金和服务费用调整须经双方协商一致并书面确认后生效。",
        "legal_basis": "《民法典》第496条、第497条（格式条款规制）",
    },
    {
        "name": "自动续租条款",
        "pattern": re.compile(
            r"(到期前\d+日(?:内)?|期满前\d+日(?:内)?)"
            r".{0,40}(未.*通知|不.*书面)"
            r".{0,30}(视为|自动)(续租|续约)"
        ),
        "risk_level": "medium",
        "issue": "合同存在'未通知即自动续租/续约'的安排，若只约束承租人，容易形成续租陷阱。",
        "suggestion": "改为：双方在到期前明确书面确认是否续租，不能以沉默视为同意。",
        "legal_basis": "《民法典》第730条（租赁期限届满的处理）",
    },
    {
        "name": "维修责任条款",
        "pattern": re.compile(r"(房屋|设施|主体结构|管道|家电).{0,20}(维修|修缮).{0,20}(由乙方|承租方).{0,10}(承担|负责)"),
        "risk_level": "medium",
        "issue": "合同将房屋或主要设施维修责任转由乙方承担，可能免除了出租人的法定维修义务。",
        "suggestion": "明确：主体结构、管道、家电大修等由出租方负责，乙方仅承担日常合理使用中的小额维护。",
        "legal_basis": "《民法典》第733条（出租人维修义务）",
    },
    {
        "name": "解约权条款",
        "pattern": re.compile(r"甲方.{0,10}(有权|可以).{0,10}(随时|任意|单方).{0,10}(解除合同|解约|收回房屋)"),
        "risk_level": "high",
        "issue": "合同赋予甲方随时单方解除或收回房屋的权利，解约权明显偏向一方。",
        "suggestion": "将解约条件限定为明确违约情形，并补充乙方对应的法定或约定解约权。",
        "legal_basis": "《民法典》第563条（合同解除）、第497条",
    },
    {
        "name": "禁止转租违约条款",
        "pattern": re.compile(r"禁止.*转租.{0,100}(违约金|罚款|不予退还)"),
        "risk_level": "medium",
        "issue": "合同将禁止转租与高额违约责任绑定，可能超过合理损失范围。",
        "suggestion": "保留转租需经同意的要求，但违约责任应以实际损失为基础，不宜直接设置高额罚款。",
        "legal_basis": "《民法典》第716条（转租）、第585条（违约金调整）",
    },
    {
        "name": "禁止养宠违约条款",
        "pattern": re.compile(r"(禁止|不得).{0,15}(养宠|饲养宠物).{0,80}(违约金|罚款|押金不退)"),
        "risk_level": "medium",
        "issue": "合同对特定禁止行为直接配套较高违约金或押金不退，可能构成过度惩罚。",
        "suggestion": "如确需限制养宠，应明确管理要求和实际损害赔偿标准，避免直接设置高额罚款。",
        "legal_basis": "《民法典》第585条、第497条",
    },
    {
        "name": "入户检查条款",
        "pattern": re.compile(r"甲方.{0,10}(有权|可以).{0,10}(随时|任意).{0,12}(进入|检查|查看|入户)"),
        "risk_level": "medium",
        "issue": "合同允许甲方随时入户检查，可能侵犯承租人的安宁居住与隐私权益。",
        "suggestion": "改为：甲方需基于合理事由并提前通知后方可入户，紧急情况除外。",
        "legal_basis": "《民法典》第509条（合同履行的诚信原则）",
    },
    {
        "name": "租金贷条款",
        "pattern": re.compile(r"(金融机构|贷款|分期|征信|委托扣款|租金贷|消费贷)"),
        "risk_level": "high",
        "issue": "合同中出现贷款、分期、征信或委托扣款安排，存在\"租金贷\"或隐性消费信贷风险。",
        "suggestion": "要求明确租金支付方式，不接受未经充分说明的贷款、分期或征信授权条款。",
        "legal_basis": "《民法典》第496条",
    },
    {
        "name": "现状交付条款",
        "pattern": re.compile(r"(现状|现有状态).{0,20}(出租|交付).{0,40}(不.*维修|不.*负责)"),
        "risk_level": "medium",
        "issue": "合同以\"现状出租/交付\"为由排除甲方维修责任，可能导致后续维权困难。",
        "suggestion": "签约前补充房屋现状和设施清单，并明确交付后非乙方原因造成的问题由甲方负责维修。",
        "legal_basis": "《民法典》第733条",
    },
    {
        "name": "提前退租赔偿条款",
        "pattern": re.compile(r"提前退租.{0,60}(全部|全额|剩余).{0,20}租金"),
        "risk_level": "high",
        "issue": "合同要求提前退租时支付全部或剩余租期租金，明显超出合理损失范围。",
        "suggestion": "改为：按照实际空置损失或不超过一个月租金的合理违约责任处理。",
        "legal_basis": "《民法典》第585条",
    },
    {
        "name": "口头承诺条款",
        "pattern": re.compile(r"口头.*承诺.*无效|以本合同.*为准.*口头"),
        "risk_level": "low",
        "issue": "合同通过\"口头承诺无效\"兜底，可能掩盖签约前的重要口头说明或营销承诺。",
        "suggestion": "将关键口头承诺补充写入书面合同或附件，避免后续举证困难。",
        "legal_basis": "《民法典》第496条",
    },
    {
        "name": "押金退还条款",
        "pattern": re.compile(r"押金不予退还|押金不退"),
        "risk_level": "high",
        "issue": "合同写明押金不予退还，属于明显加重承租人责任的格式条款。",
        "suggestion": "改为：押金在扣除实际欠费和合理损失后退还，并明确退还时限与依据。",
        "legal_basis": "《民法典》第497条",
    },
    {
        "name": "断水断电免责条款",
        "pattern": re.compile(r"断水断电.*不构成违约|可断水断电"),
        "risk_level": "high",
        "issue": "合同允许甲方通过断水断电处理争议，并宣称不构成违约，涉嫌以自力救济限制乙方基本居住使用权。",
        "suggestion": "删除断水断电免责条款，改为通过催告、协商、仲裁或诉讼方式解决争议。",
        "legal_basis": "《民法典》第509条",
    },
    {
        "name": "出租权限与房东身份条款",
        "pattern": re.compile(r"无需联系原房东|托管协议|原房东不再另行确认"),
        "risk_level": "high",
        "issue": "合同中出现\"无需联系原房东\"或托管协议等表述，存在无权出租、二房东或授权不明风险。",
        "suggestion": "签约前核验房东身份、产权证明、授权委托书和托管协议原件，并确认原房东知情同意。",
        "legal_basis": "《民法典》第716条、第717条",
    },
    {
        "name": "争议解决条款",
        "pattern": re.compile(r"甲方所在地.*仲裁委员会|提交甲方所在地"),
        "risk_level": "medium",
        "issue": "合同将争议解决地固定在甲方所在地，可能显著增加乙方维权成本。",
        "suggestion": "改为：房屋所在地、合同履行地或双方另行协商确定的争议解决地。",
        "legal_basis": "《消费者权益保护法》第26条",
    },
    {
        "name": "自动退租条款",
        "pattern": re.compile(r"逾期.{0,20}(视为|自动).{0,10}(退租|解除合同|收回房屋)"),
        "risk_level": "high",
        "issue": "合同约定逾期即自动退租或自动解除，容易导致乙方在未充分催告的情况下失去居住权。",
        "suggestion": "改为：先书面催告并给予合理补救期限，再依据违约情形处理。",
        "legal_basis": "《民法典》第563条、第721条",
    },
    {
        "name": "最终解释权条款",
        "pattern": re.compile(r"(最终解释权|解释权).{0,10}归甲方"),
        "risk_level": "medium",
        "issue": "合同将最终解释权单方归属于甲方，属于常见不公平格式条款。",
        "suggestion": "删除单方解释权条款，争议解释应以合同文义、补充协议和法律规定为准。",
        "legal_basis": "《民法典》第496条、第497条",
    },
    {
        "name": "强制搭售条款",
        "pattern": re.compile(r"(必须|应当).{0,20}(接受|购买|使用).{0,30}(物业服务|保洁服务|网络服务|增值服务)"),
        "risk_level": "medium",
        "issue": "合同将租赁与其他服务捆绑，存在强制搭售风险。",
        "suggestion": "将附加服务改为可选项，并单独列明收费标准与是否同意。",
        "legal_basis": "《消费者权益保护法》第26条",
    },
]


def rule_based_review(contract_text: str, entities: Optional[Dict] = None) -> List[Dict]:
    """
    基于规则的风险识别
    作为 LLM 分析的补充或 fallback

    Args:
        contract_text: 合同文本
        entities: 已提取的实体信息（可选）

    Returns:
        风险列表
    """
    risks = []

    # 1. 模式匹配风险
    for rule in PATTERN_RULES:
        if rule["pattern"].search(contract_text):
            # 提取匹配的原文
            match = rule["pattern"].search(contract_text)
            matched_text = _extract_clause_context(contract_text, match.start(), match.end())

            risks.append({
                "clause": matched_text,
                "risk_level": rule["risk_level"],
                "issue": rule["issue"],
                "legal_basis": rule["legal_basis"],
                "suggestion": rule["suggestion"],
                "source": "rule_engine"
            })

    # 2. 基于实体的数值风险检查
    if entities:
        risks.extend(_check_numeric_risks(contract_text, entities))

    # 3. 去重
    risks = _deduplicate_risks(risks)

    return risks


def _extract_clause_context(text: str, start: int, end: int, context_chars: int = 100) -> str:
    """
    提取匹配位置的上下文作为条款原文

    Args:
        text: 完整文本
        start: 匹配开始位置
        end: 匹配结束位置
        context_chars: 上下文字符数

    Returns:
        条款原文
    """
    # 向前找到句子开始
    clause_start = max(0, start - context_chars)
    for i in range(start - 1, clause_start, -1):
        if text[i] in '。；\n':
            clause_start = i + 1
            break

    # 向后找到句子结束
    clause_end = min(len(text), end + context_chars)
    for i in range(end, clause_end):
        if text[i] in '。；\n':
            clause_end = i + 1
            break

    return text[clause_start:clause_end].strip()


def _check_numeric_risks(contract_text: str, entities: Dict) -> List[Dict]:
    """
    基于数值的风险检查

    Args:
        contract_text: 合同文本
        entities: 实体信息

    Returns:
        风险列表
    """
    risks = []

    monthly_rent = entities.get("monthly_rent") or 0
    deposit = entities.get("deposit") or 0
    utilities = entities.get("utilities") or {}

    # 押金超标检查
    if monthly_rent > 0 and deposit > 0:
        if deposit > 3 * monthly_rent:
            risks.append({
                "clause": _find_clause_by_keyword(contract_text, "押金"),
                "risk_level": "high",
                "issue": f"押金（{deposit:.0f}元）超过3个月租金（{3*monthly_rent:.0f}元），明显偏高，可能违反地方租赁管理规定。",
                "legal_basis": "《商品房屋租赁管理办法》第七条、《民法典》第721条",
                "suggestion": f"要求将押金下调至不超过2个月租金（{2*monthly_rent:.0f}元），并明确退还时限。",
                "source": "numeric_check"
            })
        elif deposit > 2 * monthly_rent:
            risks.append({
                "clause": _find_clause_by_keyword(contract_text, "押金"),
                "risk_level": "medium",
                "issue": f"押金（{deposit:.0f}元）超过2个月租金（{2*monthly_rent:.0f}元），存在偏高风险。",
                "legal_basis": "《商品房屋租赁管理办法》第七条、《民法典》第721条",
                "suggestion": f"结合当地住房租赁规则核对押金上限，建议调整为不超过1个月租金（{monthly_rent:.0f}元）。",
                "source": "numeric_check"
            })

    # 水费检查（参考价格：北京5元/立方米，上海4元/立方米）
    water_price = utilities.get("water") or 0
    if water_price > 7:
        markup_rate = ((water_price - 5) / 5) * 100
        risks.append({
            "clause": _find_clause_by_keyword(contract_text, "水费"),
            "risk_level": "medium",
            "issue": f"水费单价（{water_price:.1f}元/立方米）明显偏高，加价约{markup_rate:.0f}%，远超合理范围。",
            "legal_basis": "《价格法》第十四条",
            "suggestion": "要求按实际缴费金额收取，甲方应每月出示水费缴费凭证。如存在公摊损耗，损耗比例不得超过10%。",
            "source": "numeric_check"
        })

    # 电费检查（参考价格：居民电价0.5元/度）
    electricity_price = utilities.get("electricity") or 0
    if electricity_price > 1.0:
        markup_rate = ((electricity_price - 0.5) / 0.5) * 100
        risk_level = "high" if markup_rate > 100 else "medium"
        risks.append({
            "clause": _find_clause_by_keyword(contract_text, "电费"),
            "risk_level": risk_level,
            "issue": f"电费单价（{electricity_price:.1f}元/度）明显偏高，加价约{markup_rate:.0f}%，严重超出合理范围。",
            "legal_basis": "《价格法》第十四条",
            "suggestion": "要求按实际缴费金额收取，甲方应每月出示电费缴费凭证。如存在公摊损耗，损耗比例不得超过10%。",
            "source": "numeric_check"
        })

    return risks


def _find_clause_by_keyword(text: str, keyword: str) -> str:
    """
    根据关键词查找条款原文

    Args:
        text: 合同文本
        keyword: 关键词

    Returns:
        条款原文
    """
    lines = text.split('\n')
    for line in lines:
        if keyword in line and len(line.strip()) > 10:
            return line.strip()

    # 如果没找到完整行，返回包含关键词的片段
    import re
    pattern = re.compile(f'.{{0,50}}{re.escape(keyword)}.{{0,50}}')
    match = pattern.search(text)
    if match:
        return match.group(0).strip()

    return f"{keyword}条款"


def _deduplicate_risks(risks: List[Dict]) -> List[Dict]:
    """
    风险去重

    Args:
        risks: 风险列表

    Returns:
        去重后的风险列表
    """
    seen = set()
    unique_risks = []

    for risk in risks:
        # 使用条款和问题描述的组合作为唯一标识
        key = f"{risk.get('clause', '')[:50]}|{risk.get('issue', '')[:50]}"
        if key not in seen:
            seen.add(key)
            unique_risks.append(risk)

    return unique_risks


def merge_llm_and_rule_risks(llm_risks: List[Dict], rule_risks: List[Dict]) -> List[Dict]:
    """
    合并 LLM 识别的风险和规则引擎识别的风险

    Args:
        llm_risks: LLM 识别的风险
        rule_risks: 规则引擎识别的风险

    Returns:
        合并后的风险列表
    """
    # 先添加所有 LLM 风险
    merged = list(llm_risks)

    # 添加规则引擎发现的新风险
    llm_clauses = {risk.get('clause', '')[:50] for risk in llm_risks}

    for rule_risk in rule_risks:
        clause_key = rule_risk.get('clause', '')[:50]
        if clause_key not in llm_clauses:
            # 移除 source 字段，保持输出一致性
            rule_risk_clean = {k: v for k, v in rule_risk.items() if k != 'source'}
            merged.append(rule_risk_clean)

    return merged
