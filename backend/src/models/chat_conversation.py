"""
聊天会话模型
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class ChatConversation(BaseModel):
    """聊天会话模型"""
    conversation_id: UUID
    interview_id: Optional[UUID] = None
    participant_ids: List[str] = Field(default_factory=list)
    conversation_type: str = Field(..., pattern="^(pet_interview|user_direct|mixed)$")
    last_message_id: Optional[UUID] = None
    last_message_at: datetime = Field(default_factory=datetime.now)
    unread_count: Dict[str, int] = Field(default_factory=dict)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class CreateConversationRequest(BaseModel):
    """创建会话请求"""
    participant_ids: List[str]
    conversation_type: str = Field(..., pattern="^(pet_interview|user_direct|mixed)$")
    interview_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    conversations: List[ChatConversation]
    total: int
    page: int
    limit: int
