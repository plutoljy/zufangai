"""
个性化风险评估器
根据用户偏好调整风险等级和建议
"""

from __future__ import annotations

from typing import Dict, List, Optional

from models.user_preferences import UserPreferences


class PersonalizedRiskEvaluator:
    """个性化风险评估器"""

    def __init__(self, user_preferences: Optional[UserPreferences] = None):
        self.preferences = user_preferences

    def evaluate_risk_level(
        self, risk_type: str, base_level: str, risk_data: Dict
    ) -> tuple[str, str]:
        """
        评估风险等级（基于用户偏好）

        Args:
            risk_type: 风险类型 (deposit_limit, penalty_excessive, etc.)
            base_level: 基础风险等级 (high/medium/low)
            risk_data: 风险相关数据 (例如押金金额、违约金比例等)

        Returns:
            (调整后的风险等级, 调整原因)
        """
        if not self.preferences:
            return base_level, ""

        # 如果用户不关注这个风险类型，降低风险等级
        if risk_type not in self.preferences.focused_risks:
            adjusted_level = self._downgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return adjusted_level, "根据您的偏好，此风险不在重点关注范围内"

        # 根据风险容忍度调整
        tolerance = self.preferences.risk_tolerance

        if risk_type == "deposit_limit":
            return self._evaluate_deposit_risk(risk_data, tolerance, base_level)
        elif risk_type == "penalty_excessive":
            return self._evaluate_penalty_risk(risk_data, tolerance, base_level)
        elif risk_type == "utility_markup":
            return self._evaluate_utility_risk(risk_data, tolerance, base_level)
        elif risk_type == "notice_period":
            return self._evaluate_notice_period_risk(risk_data, tolerance, base_level)

        return base_level, ""

    def _evaluate_deposit_risk(
        self, risk_data: Dict, tolerance, base_level: str
    ) -> tuple[str, str]:
        """评估押金风险"""
        monthly_rent = risk_data.get("monthly_rent", 0)
        deposit = risk_data.get("deposit", 0)

        if not monthly_rent or not deposit:
            return base_level, ""

        deposit_ratio = deposit / monthly_rent

        # 如果押金在用户容忍范围内，降低风险等级
        if deposit_ratio <= tolerance.deposit_tolerance:
            adjusted_level = self._downgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"押金为 {deposit_ratio:.1f} 个月租金，在您的容忍范围内（≤{tolerance.deposit_tolerance}倍）",
                )

        # 如果超出容忍范围很多，升级风险等级
        if deposit_ratio > tolerance.deposit_tolerance * 1.5:
            adjusted_level = self._upgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"押金为 {deposit_ratio:.1f} 个月租金，明显超出您的容忍范围（>{tolerance.deposit_tolerance}倍）",
                )

        return base_level, ""

    def _evaluate_penalty_risk(
        self, risk_data: Dict, tolerance, base_level: str
    ) -> tuple[str, str]:
        """评估违约金风险"""
        penalty_ratio = risk_data.get("penalty_ratio", 0)

        if not penalty_ratio:
            return base_level, ""

        # 如果违约金在用户容忍范围内，降低风险等级
        if penalty_ratio <= tolerance.penalty_tolerance:
            adjusted_level = self._downgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"违约金为 {penalty_ratio*100:.0f}%，在您的容忍范围内（≤{tolerance.penalty_tolerance*100:.0f}%）",
                )

        # 如果超出容忍范围很多，升级风险等级
        if penalty_ratio > tolerance.penalty_tolerance * 2:
            adjusted_level = self._upgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"违约金为 {penalty_ratio*100:.0f}%，明显超出您的容忍范围（>{tolerance.penalty_tolerance*100:.0f}%）",
                )

        return base_level, ""

    def _evaluate_utility_risk(
        self, risk_data: Dict, tolerance, base_level: str
    ) -> tuple[str, str]:
        """评估水电费加价风险"""
        markup_ratio = risk_data.get("markup_ratio", 0)

        if not markup_ratio:
            return base_level, ""

        # 如果加价在用户容忍范围内，降低风险等级
        if markup_ratio <= tolerance.utility_markup_tolerance:
            adjusted_level = self._downgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"水电费加价 {markup_ratio*100:.0f}%，在您的容忍范围内（≤{tolerance.utility_markup_tolerance*100:.0f}%）",
                )

        # 如果超出容忍范围很多，升级风险等级
        if markup_ratio > tolerance.utility_markup_tolerance * 2:
            adjusted_level = self._upgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"水电费加价 {markup_ratio*100:.0f}%，明显超出您的容忍范围（>{tolerance.utility_markup_tolerance*100:.0f}%）",
                )

        return base_level, ""

    def _evaluate_notice_period_risk(
        self, risk_data: Dict, tolerance, base_level: str
    ) -> tuple[str, str]:
        """评估提前退租通知期风险"""
        notice_days = risk_data.get("notice_days", 0)

        if not notice_days:
            return base_level, ""

        # 如果通知期在用户容忍范围内，降低风险等级
        if notice_days <= tolerance.notice_period_tolerance:
            adjusted_level = self._downgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"提前通知期 {notice_days} 天，在您的容忍范围内（≤{tolerance.notice_period_tolerance}天）",
                )

        # 如果超出容忍范围很多，升级风险等级
        if notice_days > tolerance.notice_period_tolerance * 2:
            adjusted_level = self._upgrade_risk_level(base_level)
            if adjusted_level != base_level:
                return (
                    adjusted_level,
                    f"提前通知期 {notice_days} 天，明显超出您的容忍范围（>{tolerance.notice_period_tolerance}天）",
                )

        return base_level, ""

    def _upgrade_risk_level(self, current_level: str) -> str:
        """升级风险等级"""
        if current_level == "low":
            return "medium"
        elif current_level == "medium":
            return "high"
        return current_level

    def _downgrade_risk_level(self, current_level: str) -> str:
        """降级风险等级"""
        if current_level == "high":
            return "medium"
        elif current_level == "medium":
            return "low"
        return current_level

    def customize_suggestion(
        self, risk_type: str, base_suggestion: str, risk_data: Dict
    ) -> str:
        """
        定制化建议（基于用户偏好）

        Args:
            risk_type: 风险类型
            base_suggestion: 基础建议
            risk_data: 风险相关数据

        Returns:
            定制化后的建议
        """
        if not self.preferences:
            return base_suggestion

        # 根据用户经验等级调整建议详细程度
        if self.preferences.experience_level == "beginner":
            # 新手：提供更详细的建议
            return self._add_detailed_guidance(base_suggestion, risk_type)
        elif self.preferences.experience_level == "expert":
            # 专家：提供简洁的建议
            return self._simplify_suggestion(base_suggestion)

        return base_suggestion

    def _add_detailed_guidance(self, suggestion: str, risk_type: str) -> str:
        """为新手添加详细指导"""
        guidance_map = {
            "deposit_limit": "\n[TIP] 新手提示：押金过高可能导致资金压力，建议与房东协商降低押金或分期支付。",
            "penalty_excessive": "\n[TIP] 新手提示：违约金过高可能导致提前退租时损失惨重，建议要求修改为合理范围。",
            "utility_markup": "\n[TIP] 新手提示：水电费加价是常见的隐性收费，建议要求房东提供缴费凭证。",
        }

        guidance = guidance_map.get(risk_type, "")
        return suggestion + guidance

    def _simplify_suggestion(self, suggestion: str) -> str:
        """为专家简化建议"""
        # 移除详细的法律条文引用，只保留核心建议
        lines = suggestion.split("\n")
        if len(lines) > 1:
            return lines[0]  # 只保留第一行
        return suggestion

    def get_personalized_summary(self, risk_items: List[Dict]) -> str:
        """
        生成个性化风险摘要

        Args:
            risk_items: 风险项列表

        Returns:
            个性化摘要文本
        """
        if not self.preferences:
            return ""

        # 统计用户关注的风险
        focused_risks = [
            item for item in risk_items if item.get("risk_type") in self.preferences.focused_risks
        ]

        if not focused_risks:
            return "[OK] 根据您的偏好，合同中没有您特别关注的风险项。"

        summary = f"[WARN] 发现 {len(focused_risks)} 项您特别关注的风险：\n"
        for item in focused_risks[:3]:  # 只显示前3项
            summary += f"- {item.get('issue', '未知风险')}\n"

        if len(focused_risks) > 3:
            summary += f"- 还有 {len(focused_risks) - 3} 项风险，请查看详细报告\n"

        return summary
