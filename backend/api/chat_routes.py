"""
聊天路由（混合存储版）

提供AI对话功能，集成认证和新会话服务
"""
from fastapi import APIRouter, Query, Body, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from schemas.chat import ChatRequest
from services.agent_service import MultiAgentService
from services.auth_service import get_current_user_id
from services.session_service import SessionService
from infrastructure.database.pg_database import get_db
from schemas.request import ChatMessageRequest, UserContext
from infrastructure.logging.logger import logger
from typing import AsyncGenerator
import re


router = APIRouter()


async def ai_search_with_session_save(
    session_id: str,
    user_id: int,
    user_query: str,
    db: DBSession,
    agent_stream: AsyncGenerator
):
    """
    包装Agent流，在最后保存会话历史

    Args:
        session_id: 会话ID
        user_id: 用户ID
        user_query: 用户问题
        db: 数据库会话
        agent_stream: Agent流式响应

    Yields:
        SSE数据块
    """
    full_response = ""
    full_thinking = ""
    full_process = ""
    full_documents = ""

    try:
        # 1. 先保存用户消息到JSONL
        SessionService.append_message(
            session_id=session_id,
            role="user",
            content=user_query,
            db=db
        )

        # 2. 流式转发Agent响应
        async for chunk in agent_stream:
            yield chunk

            # 收集完整回答/思考/处理过程/参考来源（从SSE数据中提取）
            if isinstance(chunk, str) and chunk.startswith("data: "):
                try:
                    import json
                    data_line = chunk[6:].strip()  # 去掉 "data: " 前缀
                    if data_line:
                        packet = json.loads(data_line)
                        content = packet.get("content", {})
                        kind = content.get("kind")
                        text = content.get("text", "")
                        if kind == "ANSWER":
                            full_response += text
                        elif kind == "THINKING":
                            full_thinking += text
                        elif kind == "PROCESS":
                            full_process += text
                        elif kind == "REFERENCE":
                            full_documents = text  # 单次事件，JSON 数组
                except:
                    pass

        # 3. 保存助手回答到JSONL（思考/过程/参考来源存 metadata，刷新后可恢复）
        if full_response:
            # 格式化输出（去掉多余换行）
            formatted_response = re.sub(r'\n+', '\n', full_response)

            metadata = {"model": "orchestrator"}
            if full_thinking:
                metadata["thinking"] = re.sub(r'\n+', '\n', full_thinking)
            if full_process:
                metadata["process"] = re.sub(r'\n+', '\n', full_process)
            if full_documents:
                metadata["documents"] = full_documents

            SessionService.append_message(
                session_id=session_id,
                role="assistant",
                content=formatted_response,
                db=db,
                metadata=metadata
            )

            logger.info(f"保存会话历史成功: session_id={session_id}, user_id={user_id}, "
                        f"回答{len(full_response)}字, 思考{len(full_thinking)}字, "
                        f"过程{len(full_process)}字, 参考{len(full_documents)}字")

    except Exception as e:
        logger.error(f"保存会话历史失败: {str(e)}")
        # 不中断流，只记录错误


@router.post("/ai_search/")
async def ai_search(
    session_id: str = Query(...),
    request: ChatRequest = Body(...),
    user_id: int = Depends(get_current_user_id),
    db: DBSession = Depends(get_db)
):
    """
    AI搜索对话（集成认证和会话保存）

    Args:
        session_id: 会话ID
        request: 聊天请求
        user_id: 用户ID（从JWT token自动获取）
        db: 数据库会话

    Returns:
        StreamingResponse: SSE流式响应
    """
    try:
        logger.info(f"AI搜索 - user_id: {user_id}, 会话: {session_id}, 问题: {request.message}")

        # 验证会话归属
        from models.session import Session
        session = db.query(Session).filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if not session:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或无权限访问"
            )

        # 处理附件：读取文件内容
        attachment_contents = []
        if request.attachments:
            from pathlib import Path
            logger.info(f"处理 {len(request.attachments)} 个附件")

            for file_url in request.attachments:
                try:
                    # 从 URL 提取文件路径 (storage/uploads/{user_id}/{filename})
                    file_path = Path(file_url)

                    if file_path.exists() and file_path.is_file():
                        # 读取文件内容（支持文本文件）
                        try:
                            content = file_path.read_text(encoding='utf-8')
                            attachment_contents.append({
                                "filename": file_path.name,
                                "content": content,
                                "size": file_path.stat().st_size
                            })
                            logger.info(f"成功读取附件: {file_path.name}, 大小: {len(content)} 字符")
                        except UnicodeDecodeError:
                            # 如果是二进制文件，记录但不处理
                            logger.warning(f"附件 {file_path.name} 不是文本文件，跳过")
                    else:
                        logger.warning(f"附件文件不存在: {file_url}")
                except Exception as e:
                    logger.error(f"读取附件失败 {file_url}: {str(e)}")

        # 转换为 its_multi_agent 的请求格式
        agent_request = ChatMessageRequest(
            query=request.message,
            context=UserContext(
                user_id=str(user_id),
                session_id=session_id,
                attachments=attachment_contents if attachment_contents else None
            ),
            flag=True,
            deep_think=request.deep_think if request.deep_think is not None else True
        )

        # 调用Agent服务（获取流）
        agent_stream = MultiAgentService.process_task(agent_request, flag=True)

        # 包装流，在最后保存会话历史
        wrapped_stream = ai_search_with_session_save(
            session_id=session_id,
            user_id=user_id,
            user_query=request.message,
            db=db,
            agent_stream=agent_stream
        )

        return StreamingResponse(
            content=wrapped_stream,
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"AI搜索失败: {str(e)}")
        raise
