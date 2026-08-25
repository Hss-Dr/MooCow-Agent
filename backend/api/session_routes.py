"""
会话管理路由（混合存储版）

提供会话创建、列表、消息历史、删除等功能
"""
from fastapi import APIRouter, Query, HTTPException, Depends, status, Body
from sqlalchemy.orm import Session as DBSession
from schemas.session import (
    SessionCreateResponse,
    SessionListResponse,
    SessionInfo,
    MessageItem
)
from services.auth_service import get_current_user_id
from services.session_service import SessionService
from infrastructure.database.pg_database import get_db
from infrastructure.logging.logger import logger
from models.session import Session
import uuid
from datetime import datetime
from typing import List


router = APIRouter(prefix="/session")


@router.post("/create", response_model=SessionCreateResponse)
async def create_session(
    session_name: str = Query(default="新对话"),
    user_id: int = Depends(get_current_user_id),
    db: DBSession = Depends(get_db)
):
    """
    创建新会话（需认证或使用default_user）

    Args:
        session_name: 会话名称
        user_id: 用户ID（从JWT token自动获取）

    Returns:
        SessionCreateResponse: 包含新会话ID
    """
    try:
        # 生成16位会话ID
        session_id = str(uuid.uuid4()).replace("-", "")[:16]

        # 创建会话（包含数据库记录和JSONL文件）
        session = SessionService.create_session(
            user_id=user_id,
            session_id=session_id,
            session_name=session_name,
            db=db
        )

        logger.info(f"创建新会话成功: user_id={user_id}, session_id={session_id}")

        return SessionCreateResponse(
            session_id=session.session_id,
            session_name=session.session_name,
            status="success",
            message="Session created successfully"
        )
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    user_id: int = Depends(get_current_user_id),
    db: DBSession = Depends(get_db)
):
    """
    获取当前用户的所有会话列表

    用户只能查看自己的会话

    Returns:
        SessionListResponse: 会话列表（按最后消息时间倒序）
    """
    try:
        logger.info(f"获取用户 {user_id} 的会话列表")

        # 从数据库获取所有会话
        db_sessions = SessionService.get_user_sessions(user_id, db)

        # 转换为SessionInfo格式
        sessions: List[SessionInfo] = []
        for session in db_sessions:
            session_info = SessionInfo(
                session_id=session.session_id,
                session_name=session.session_name,
                created_at=session.created_at.isoformat() if session.created_at else None,
                updated_at=session.updated_at.isoformat() if session.updated_at else None,
                user_id=str(session.user_id),
                message_count=session.message_count,
                last_message_at=session.last_message_at.isoformat() if session.last_message_at else None
            )
            sessions.append(session_info)

        logger.info(f"找到 {len(sessions)} 个会话")

        return SessionListResponse(sessions=sessions)

    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/messages/{session_id}")
async def get_messages(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: DBSession = Depends(get_db)
):
    """
    获取会话的消息历史

    Args:
        session_id: 会话ID

    Returns:
        List[MessageItem]: 消息列表
    """
    try:
        logger.info(f"获取会话 {session_id} 的消息历史")

        # 验证会话归属
        session = db.query(Session).filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权限访问"
            )

        # 从JSONL文件加载历史（原始格式，含metadata）
        history = SessionService.load_history_raw(session_id, db, max_turn=50)

        # 转换为MessageItem格式
        messages: List[MessageItem] = []

        for i, msg in enumerate(history):
            # 跳过system消息
            if msg.get("role") == "system":
                continue

            if msg.get("role") == "user":
                user_question = msg.get("content", "")
                # 找到对应的assistant回答（含思考/处理过程/参考来源）
                model_answer = ""
                think = None
                process = None
                documents = None
                if i + 1 < len(history) and history[i + 1].get("role") == "assistant":
                    next_msg = history[i + 1]
                    model_answer = next_msg.get("content", "")
                    meta = next_msg.get("metadata") or {}
                    think = meta.get("thinking")
                    process = meta.get("process")
                    documents = meta.get("documents")

                message_item = MessageItem(
                    message_id=f"{session_id}_{i}",
                    session_id=session_id,
                    user_question=user_question,
                    model_answer=model_answer,
                    think=think,
                    process=process,
                    documents=documents,
                    created_at=datetime.now().isoformat()
                )
                messages.append(message_item)

        logger.info(f"找到 {len(messages)} 条消息")

        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息历史失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/delete/{session_id}")
async def delete_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: DBSession = Depends(get_db)
):
    """
    删除会话（包括数据库记录和JSONL文件）

    Args:
        session_id: 会话ID

    Returns:
        Dict: 删除结果
    """
    try:
        logger.info(f"删除会话: session_id={session_id}, user_id={user_id}")

        # 删除会话（验证归属）
        SessionService.delete_session(session_id, user_id, db)

        return {"message": "会话删除成功", "session_id": session_id}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/rename/{session_id}")
async def rename_session(
    session_id: str,
    request: dict = Body(...),
    user_id: int = Depends(get_current_user_id),
    db: DBSession = Depends(get_db)
):
    """
    重命名会话

    Args:
        session_id: 会话ID
        request: 请求体 {"session_name": "新名称"}
        user_id: 用户ID（从JWT token自动获取）

    Returns:
        Dict: 重命名结果
    """
    try:
        session_name = request.get("session_name")
        if not session_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少 session_name 参数"
            )

        logger.info(f"重命名会话: session_id={session_id}, new_name={session_name}, user_id={user_id}")

        # 验证会话归属
        session = db.query(Session).filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权限访问"
            )

        # 更新会话名称
        session.session_name = session_name
        session.updated_at = datetime.now()
        db.commit()

        logger.info(f"重命名会话成功: session_id={session_id}")

        return {
            "message": "会话重命名成功",
            "session_id": session_id,
            "session_name": session_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重命名会话失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
