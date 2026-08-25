"""
会话业务管理服务类（混合存储版）

使用PostgreSQL存储会话元数据，JSONL文件存储对话历史
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from models.session import Session
from models.user import User
from utils.jsonl_helper import JSONLHelper
from infrastructure.logging.logger import logger


class SessionService:
    """会话服务（混合存储架构）"""

    @staticmethod
    def create_session(
        user_id: int,
        session_id: str,
        session_name: str,
        db: DBSession
    ) -> Session:
        """
        创建新会话

        Args:
            user_id: 用户ID
            session_id: 会话ID
            session_name: 会话名称
            db: 数据库会话

        Returns:
            Session: 创建的会话对象
        """
        # 获取用户名用于目录命名
        user = db.query(User).filter_by(id=user_id).first()
        username = user.username if user else f"user_{user_id}"

        # 构建文件路径（使用用户名而不是ID）
        file_path = f"user_memories/{username}/{session_id}.jsonl"

        # 创建数据库记录
        session = Session(
            session_id=session_id,
            user_id=user_id,
            session_name=session_name,
            file_path=file_path,
            message_count=0
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 创建system消息
        JSONLHelper.append_message(
            file_path,
            role="system",
            content=f"你是一个有记忆的智能体助手，请基于上下文历史会话用户问题 (会话ID {session_id})"
        )

        # 更新统计
        session.message_count = 1
        session.last_message_at = datetime.utcnow()
        db.commit()

        logger.info(f"创建会话成功: username={username}, user_id={user_id}, session_id={session_id}, file_path={file_path}")
        return session

    @staticmethod
    def append_message(
        session_id: str,
        role: str,
        content: str,
        db: DBSession,
        metadata: Optional[Dict] = None
    ):
        """
        追加消息到会话

        Args:
            session_id: 会话ID
            role: 消息角色（system/user/assistant）
            content: 消息内容
            db: 数据库会话
            metadata: 可选的元数据
        """
        # 查询会话
        session = db.query(Session).filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"会话不存在: {session_id}")

        # 追加到JSONL文件
        JSONLHelper.append_message(session.file_path, role, content, metadata)

        # 更新数据库统计
        session.message_count += 1
        session.last_message_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def load_history(
        session_id: str,
        db: DBSession,
        max_turn: int = 10
    ) -> List[Dict[str, str]]:
        """
        加载会话历史（OpenAI格式）

        Args:
            session_id: 会话ID
            db: 数据库会话
            max_turn: 最大轮数（每轮=1个user+1个assistant）

        Returns:
            List[Dict]: OpenAI格式的消息列表
        """
        # 查询会话
        session = db.query(Session).filter_by(session_id=session_id).first()
        if not session:
            logger.warning(f"会话不存在: {session_id}")
            return []

        try:
            # 从JSONL文件读取（限制条数）
            # max_turn轮对话 = system(1) + max_turn*2条消息
            max_messages = 1 + max_turn * 2
            jsonl_messages = JSONLHelper.read_messages(
                session.file_path,
                max_messages=max_messages
            )

            # 转换为OpenAI格式
            return JSONLHelper.convert_to_openai_format(jsonl_messages)

        except Exception as e:
            logger.error(f"加载会话历史失败: session_id={session_id}, error={e}")
            return []

    @staticmethod
    def load_history_raw(
        session_id: str,
        db: DBSession,
        max_turn: int = 10
    ) -> List[Dict]:
        """
        加载会话历史（原始JSONL格式，包含metadata）

        用于需要读取 thinking/process 等扩展字段的场景。
        """
        session = db.query(Session).filter_by(session_id=session_id).first()
        if not session:
            logger.warning(f"会话不存在: {session_id}")
            return []

        try:
            max_messages = 1 + max_turn * 2
            return JSONLHelper.read_messages(
                session.file_path,
                max_messages=max_messages
            )
        except Exception as e:
            logger.error(f"加载会话原始历史失败: session_id={session_id}, error={e}")
            return []

    @staticmethod
    def get_user_sessions(user_id: int, db: DBSession) -> List[Session]:
        """
        获取用户的所有会话

        Args:
            user_id: 用户ID
            db: 数据库会话

        Returns:
            List[Session]: 会话列表（按last_message_at倒序）
        """
        return db.query(Session).filter_by(user_id=user_id).order_by(
            Session.last_message_at.desc().nullslast()
        ).all()

    @staticmethod
    def delete_session(session_id: str, user_id: int, db: DBSession):
        """
        删除会话（包括数据库记录和JSONL文件）

        Args:
            session_id: 会话ID
            user_id: 用户ID（用于验证归属）
            db: 数据库会话
        """
        from pathlib import Path

        # 查询会话
        session = db.query(Session).filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if not session:
            raise ValueError(f"会话不存在或无权限: session_id={session_id}")

        # 删除JSONL文件
        file_path = Path(session.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"删除JSONL文件: {session.file_path}")

        # 删除数据库记录
        db.delete(session)
        db.commit()
        logger.info(f"删除会话成功: session_id={session_id}")

    @staticmethod
    def prepare_history(
        user_id: int,
        session_id: str,
        user_input: str,
        db: DBSession,
        max_turn: int = 10
    ) -> List[Dict[str, str]]:
        """
        准备历史会话（用于发送给LLM）

        加载历史 + 追加当前用户输入

        Args:
            user_id: 用户ID
            session_id: 会话ID
            user_input: 用户输入
            db: 数据库会话
            max_turn: 最大轮数

        Returns:
            List[Dict]: 包含用户输入的完整历史
        """
        # 加载历史
        chat_history = SessionService.load_history(session_id, db, max_turn)

        # 追加当前用户输入
        chat_history.append({"role": "user", "content": user_input})

        return chat_history


# 全局单例
session_service = SessionService()
