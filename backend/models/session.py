"""
Session数据模型

会话元数据模型（对话历史存储在JSONL文件中）
"""
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from infrastructure.database.pg_database import Base


class Session(Base):
    """会话模型（混合存储架构）"""
    __tablename__ = 'sessions'

    session_id = Column(String(16), primary_key=True)
    session_name = Column(String(255), nullable=False)
    user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # 统计字段（缓存，避免扫描JSONL文件）
    message_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(TIMESTAMP, index=True)

    # 文件路径（相对路径，指向JSONL文件）
    file_path = Column(String(255), nullable=False)

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    # 关系
    user = relationship("User", backref="sessions")

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id={self.user_id})>"
