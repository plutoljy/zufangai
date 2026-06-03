"""
合租需求模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class RoommateRequest(BaseModel):
    """合租需求模型"""
    request_id: UUID
    user_id: UUID
    profile_id: UUID
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    rent_range: Optional[Dict[str, Any]] = None
    mode: str = Field(default="quick", pattern="^(quick|deep)$")
    interview_config: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="draft", pattern="^(draft|published|interviewing|completed|closed)$")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreateRequestRequest(BaseModel):
    """创建需求请求"""
    profile_id: UUID
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    rent_range: Optional[Dict[str, Any]] = None
    mode: str = Field(default="quick", pattern="^(quick|deep)$")
    interview_config: Dict[str, Any] = Field(default_factory=dict)


class UpdateRequestRequest(BaseModel):
    """更新需求请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    rent_range: Optional[Dict[str, Any]] = None
    mode: Optional[str] = Field(None, pattern="^(quick|deep)$")
    interview_config: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|interviewing|completed|closed)$")
