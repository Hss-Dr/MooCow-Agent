from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class DocumentUploadResponse(BaseModel):
    """文档上传记录响应模型"""
    id: int
    session_id: str
    document_name: str
    document_type: str
    file_size: Optional[int]
    upload_time: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SessionDocumentsResponse(BaseModel):
    """会话文档信息响应模型"""
    session_id: str
    has_documents: bool
    documents: List[DocumentUploadResponse]
    total_count: int
    
    class Config:
        from_attributes = True


class SessionDocumentSummary(BaseModel):
    """会话文档摘要响应模型"""
    session_id: str
    has_documents: bool
    latest_document_name: Optional[str] = None
    latest_document_type: Optional[str] = None
    latest_upload_time: Optional[datetime] = None
    total_documents: int = 0
    
    class Config:
        from_attributes = True 