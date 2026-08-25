from pydantic import Field
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class UserContext(BaseModel):
    """
    用户上下文信息，用于标识请求来源。
    """
    user_id: str                                                          # 当前用户的唯一标识
    session_id: Optional[str] = Field(description="会话ID", default=None)  # 可选的会话标识，用于多轮对话追踪
    attachments: Optional[List[Dict[str, Any]]] = Field(description="附件列表", default=None)  # 附件内容列表


class ChatMessageRequest(BaseModel):
    """
    用户发起聊天请求的入参结构。
    """
    query: str           # 用户输入的查询文本
    context: UserContext # 用户上下文信息
    flag: bool = True    # 预留标志位（当前默认为 True）
    deep_think: bool = True  # 深度思考开关：True 用推理模型（有思考过程），False 用快速模型


class UserSessionsRequest(BaseModel):
    """
    获取用户历史会话列表的请求体。
    """
    user_id: str = Field(description="用户唯一标识符")     # 用于查询该用户的所有会话记录

