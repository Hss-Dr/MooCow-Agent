"""
聊天相关的Schema定义
"""
from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    web_search: Optional[bool] = False
    deep_research: Optional[bool] = False
    deep_think: Optional[bool] = True  # 深度思考开关（默认开）
    attachments: Optional[List[str]] = None
