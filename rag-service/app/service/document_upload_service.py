from sqlalchemy.orm import Session
from models.document_upload import DocumentUpload
from typing import List, Optional
from datetime import datetime


class DocumentUploadService:
    """文档上传记录服务"""
    
    @staticmethod
    def create_upload_record(
        db: Session,
        session_id: str,
        document_name: str,
        document_type: str,
        file_size: Optional[int] = None
    ) -> DocumentUpload:
        """创建文档上传记录"""
        upload_record = DocumentUpload(
            session_id=session_id,
            document_name=document_name,
            document_type=document_type,
            file_size=file_size,
            upload_time=datetime.now()
        )
        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)
        return upload_record
    
    @staticmethod
    def get_session_documents(db: Session, session_id: str) -> List[DocumentUpload]:
        """获取指定会话的所有文档上传记录"""
        return db.query(DocumentUpload).filter(
            DocumentUpload.session_id == session_id
        ).order_by(DocumentUpload.upload_time.desc()).all()
    
    @staticmethod
    def has_uploaded_documents(db: Session, session_id: str) -> bool:
        """检查指定会话是否有上传的文档"""
        count = db.query(DocumentUpload).filter(
            DocumentUpload.session_id == session_id
        ).count()
        return count > 0
    
    @staticmethod
    def get_latest_document(db: Session, session_id: str) -> Optional[DocumentUpload]:
        """获取指定会话最新上传的文档"""
        return db.query(DocumentUpload).filter(
            DocumentUpload.session_id == session_id
        ).order_by(DocumentUpload.upload_time.desc()).first() 