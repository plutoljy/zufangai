"""
宠物面试模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class PetInterview(BaseModel):
    """宠物面试模型"""
    interview_id: UUID
    request_id: UUID
    applicant_id: UUID
    dialogue: List[Dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.7
    max_questions: int = 10
    status: str = Field(default="pending", pattern="^(pending|in_progress|completed|abandoned)$")
    detected_issues: List[str] = Field(default_factory=list)
    consistency_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StartInterviewRequest(BaseModel):
    """开始面试请求"""
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_questions: int = Field(default=10, ge=1, le=50)


class InterviewStatusResponse(BaseModel):
    """面试状态响应"""
    interview_id: UUID
    status: str
    current_turn: int
    max_questions: int
    detected_issues: List[str]
    consistency_score: float
