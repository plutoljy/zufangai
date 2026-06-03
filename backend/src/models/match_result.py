"""
匹配结果模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class MatchResult(BaseModel):
    """匹配结果模型"""
    result_id: UUID
    interview_id: UUID
    overall_score: Optional[int] = Field(None, ge=0, le=100)
    deal_breaker_analysis: Dict[str, Any] = Field(default_factory=dict)
    common_grounds: List[Dict[str, Any]] = Field(default_factory=list)
    integrity_assessment: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class MatchResultResponse(BaseModel):
    """匹配结果响应"""
    result: MatchResult
    interview: Dict[str, Any]
    applicant_profile: Dict[str, Any]
