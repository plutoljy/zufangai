"""
聊天消息模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class ChatMessage(BaseModel):
    """聊天消息模型"""
    message_id: UUID
    conversation_id: UUID
    sender_id: str
    sender_type: str = Field(..., pattern="^(pet|user|system)$")
    content: str
    content_type: str = Field(..., pattern="^(text|question|answer|user_interrupt)$")
    reply_to_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="sent", pattern="^(sending|sent|delivered|read|failed)$")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str
    content_type: str = Field(default="text", pattern="^(text|question|answer|user_interrupt)$")
    reply_to_id: Optional[UUID] = None


class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: list[ChatMessage]
    has_more: bool
    before_message_id: Optional[UUID] = None
