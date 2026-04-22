"""
用户偏好数据模型
用于存储用户的风险偏好和个性化设置
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RiskTolerance(BaseModel):
    """风险容忍度配置"""

    # 押金容忍度 (倍数，例如 1.0 表示接受 1 个月租金的押金)
    deposit_tolerance: float = Field(default=1.0, ge=0.5, le=3.0)

    # 违约金容忍度 (倍数，例如 0.3 表示接受 30% 的违约金)
    penalty_tolerance: float = Field(default=0.3, ge=0.1, le=1.0)

    # 水电费加价容忍度 (百分比，例如 0.2 表示接受 20% 的加价)
    utility_markup_tolerance: float = Field(default=0.2, ge=0.0, le=1.0)

    # 提前退租通知期容忍度 (天数)
    notice_period_tolerance: int = Field(default=30, ge=7, le=90)


class UserPreferences(BaseModel):
    """用户偏好完整模型"""

    user_id: str

    # 风险容忍度
    risk_tolerance: RiskTolerance = Field(default_factory=RiskTolerance)

    # 关注的风险类型 (用户特别关注的风险维度)
    focused_risks: List[str] = Field(
        default_factory=lambda: [
            "deposit_limit",  # 押金超限
            "penalty_excessive",  # 违约金过高
            "utility_markup",  # 水电费加价
        ]
    )

    # 用户角色 (影响风险判断的严格程度)
    user_role: str = Field(default="tenant")  # tenant(租客) / landlord(房东) / agent(中介)

    # 租房经验 (影响风险提示的详细程度)
    experience_level: str = Field(default="beginner")  # beginner / intermediate / expert

    # 地区偏好 (不同地区的法规可能不同)
    region: Optional[str] = None  # 例如: "上海", "北京", "深圳"

    # 自定义风险阈值
    custom_thresholds: Dict[str, float] = Field(default_factory=dict)

    # 创建和更新时间
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PreferenceUpdate(BaseModel):
    """用户偏好更新请求"""

    risk_tolerance: Optional[RiskTolerance] = None
    focused_risks: Optional[List[str]] = None
    user_role: Optional[str] = None
    experience_level: Optional[str] = None
    region: Optional[str] = None
    custom_thresholds: Optional[Dict[str, float]] = None
