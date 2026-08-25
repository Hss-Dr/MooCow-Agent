from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.sql import func
from models.base import Base

class Session(Base):
    __tablename__ = 'sessions'
    
    session_id = Column(String(16), primary_key=True)
    session_name = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now()) 