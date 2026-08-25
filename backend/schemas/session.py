"""
会话相关的Schema定义
"""
from pydantic import BaseModel, RootModel
from typing import List, Optional


class SessionCreateResponse(BaseModel):
    """创建会话响应"""
    session_id: str
    session_name: Optional[str] = None
    status: str
    message: str


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    session_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    user_id: Optional[str] = None
    message_count: Optional[int] = 0
    last_message_at: Optional[str] = None


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionInfo]


class MessageItem(BaseModel):
    """消息项"""
    message_id: str
    session_id: str
    user_question: str
    model_answer: str
    think: Optional[str] = None
    process: Optional[str] = None
    documents: Optional[str] = None
    recommended_questions: Optional[List[str]] = None
    created_at: str


# Pydantic v2 使用 RootModel
class MessageHistoryResponse(RootModel[List[MessageItem]]):
    """消息历史响应"""
    pass
