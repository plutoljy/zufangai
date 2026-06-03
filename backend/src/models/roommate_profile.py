"""
宠物画像模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class RoommateProfile(BaseModel):
    """宠物画像模型"""
    profile_id: UUID
    user_id: UUID
    lifestyle_habits: Dict[str, Any] = Field(default_factory=dict)
    deal_breakers: Dict[str, Any] = Field(default_factory=dict)
    user_preferences_id: Optional[UUID] = None
    pet_personality: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class CreateProfileRequest(BaseModel):
    """创建画像请求"""
    lifestyle_habits: Dict[str, Any]
    deal_breakers: Dict[str, Any]
    user_preferences_id: Optional[UUID] = None


class UpdateProfileRequest(BaseModel):
    """更新画像请求"""
    lifestyle_habits: Optional[Dict[str, Any]] = None
    deal_breakers: Optional[Dict[str, Any]] = None
    user_preferences_id: Optional[UUID] = None
