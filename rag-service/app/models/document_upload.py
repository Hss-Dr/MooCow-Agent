from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from models.base import Base

class DocumentUpload(Base):
    __tablename__ = 'document_uploads'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(16), nullable=False)
    document_name = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)
    file_size = Column(Integer)
    upload_time = Column(TIMESTAMP, nullable=False, server_default=func.now())
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now()) 