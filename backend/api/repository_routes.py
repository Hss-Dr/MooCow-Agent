"""
文件管理路由

提供文件上传、列表、删除功能，并与RAG服务集成
"""
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Form, Security
from typing import List, Optional
import os
from pathlib import Path
from infrastructure.logging.logger import logger
from infrastructure.clients.rag_client import rag_client
from services.auth_service import access_security
from fastapi_jwt import JwtAuthorizationCredentials
from datetime import datetime


router = APIRouter()

# 文件存储路径
UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload_files/")
async def upload_files(
    files: UploadFile = File(...),
    session_id: Optional[str] = Query(default="default"),
    user_id: Optional[str] = Query(default="default_user"),
    scope: Optional[str] = Query(default="personal", description="personal=个人私有库(默认); shared=公共共享库(仅管理员)"),
    credentials: Optional[JwtAuthorizationCredentials] = Security(access_security)
):
    """
    上传文件到知识库

    Args:
        files: 上传的文件
        session_id: 会话ID
        user_id: 用户ID
        scope: personal=个人私有库(默认); shared=公共共享库(仅管理员)

    Returns:
        上传结果
    """
    try:
        # 以已验证的 JWT 身份为准，避免伪造 user_id 冒充他人/管理员
        if credentials and credentials.subject.get("user_id") is not None:
            user_id = str(credentials.subject.get("user_id"))

        # 未传 session_id 或为默认值时，用当前用户作为 RAG 存储目录名
        if not session_id or session_id == "default":
            session_id = user_id

        # 上传到公共库必须是已登录用户（管理员权限由 RAG 侧按 ADMIN_USER_IDS 白名单权威校验）
        if scope == "shared" and not (credentials and credentials.subject.get("user_id") is not None):
            raise HTTPException(status_code=401, detail="上传公共知识库需要登录")

        logger.info(f"用户 {user_id} 上传文件: {files.filename} (scope={scope})")

        # 创建用户专属目录
        user_dir = UPLOAD_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件到本地
        file_path = user_dir / files.filename
        content = await files.read()

        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"文件已保存到: {file_path}")

        # 调用RAG服务上传文件（入库到 ES）
        rag_result = await rag_client.upload_documents(
            files=[{
                "name": files.filename,
                "content": content
            }],
            user_id=user_id,
            session_id=session_id,
            scope=scope
        )
        logger.info(f"文件已上传到RAG服务: {rag_result}")

        # 不再吞掉 RAG 侧失败（权限不足/解析失败等）：避免“本地保存成功但知识库为空”的假成功
        if isinstance(rag_result, dict) and rag_result.get("status") == "error":
            err = rag_result.get("error", "上传到知识库失败")
            # 权限相关错误回传 403，其余回传 400
            status_code = 403 if ("管理员" in str(err) or "403" in str(err)) else 400
            raise HTTPException(status_code=status_code, detail=err)

        return {
            "status": "success",
            "file_id": str(hash(files.filename)),
            "url": str(file_path),
            "message": "文件上传成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_files/")
async def get_files(
    user_id: str = Query(default="default_user"),
    credentials: Optional[JwtAuthorizationCredentials] = Security(access_security)
):
    """
    获取用户的文件列表

    Args:
        user_id: 用户ID（以JWT身份为准）
        credentials: JWT凭证

    Returns:
        文件列表
    """
    try:
        # 以已验证的 JWT 身份为准（修复：登录用户看不到自己文件的问题）
        if credentials and credentials.subject.get("user_id") is not None:
            user_id = str(credentials.subject.get("user_id"))

        logger.info(f"获取用户 {user_id} 的文件列表")

        files = []
        user_dir = UPLOAD_DIR / user_id

        if user_dir.exists():
            for file_path in user_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()

                    # 简单的RAG状态推断（基于文件时间）
                    # TODO: 后续可以从Redis或数据库查询真实状态
                    import time
                    file_age = time.time() - stat.st_mtime

                    # 如果文件刚上传（<30秒），认为正在处理
                    if file_age < 30:
                        rag_status = "processing"
                    else:
                        # 否则认为已完成（简化逻辑）
                        rag_status = "success"

                    files.append({
                        "file_id": str(hash(file_path.name)),
                        "file_name": file_path.name,
                        "file_size": stat.st_size,
                        "create_time": int(stat.st_ctime),
                        "update_time": int(stat.st_mtime),
                        # 新增：RAG处理相关字段
                        "rag_status": rag_status,  # processing/success/failed
                        "chunk_method": "优化分块",
                        "chunk_count": 0,  # TODO: 从RAG服务查询
                    })

        logger.info(f"找到 {len(files)} 个文件")

        return files

    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete_file/")
async def delete_file(
    file_name: str = Query(...),
    user_id: str = Query(default="default_user"),
    credentials: Optional[JwtAuthorizationCredentials] = Security(access_security)
):
    """
    删除文件

    Args:
        file_name: 文件名
        user_id: 用户ID（以JWT身份为准）
        credentials: JWT凭证

    Returns:
        删除结果
    """
    try:
        # 以已验证的 JWT 身份为准
        if credentials and credentials.subject.get("user_id") is not None:
            user_id = str(credentials.subject.get("user_id"))

        logger.info(f"用户 {user_id} 删除文件: {file_name}")

        file_path = UPLOAD_DIR / user_id / file_name

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        # 删除本地文件
        file_path.unlink()

        logger.info(f"文件已删除: {file_path}")

        return {"message": "文件删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload_status/{file_name}")
async def get_upload_status(
    file_name: str,
    user_id: str = Query(default="default_user")
):
    """
    查询文件的RAG处理状态

    Args:
        file_name: 文件名
        user_id: 用户ID

    Returns:
        {
            "status": "processing" | "success" | "failed",
            "message": "处理描述",
            "progress": 进度百分比,
            "chunk_count": chunk数量
        }
    """
    try:
        logger.info(f"查询文件状态: {file_name}, user_id: {user_id}")

        file_path = UPLOAD_DIR / user_id / file_name

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        stat = file_path.stat()
        import time
        file_age = time.time() - stat.st_mtime

        # 简单的状态推断逻辑
        if file_age < 10:
            return {
                "status": "processing",
                "message": "正在上传文件...",
                "progress": 30,
                "chunk_count": 0
            }
        elif file_age < 30:
            return {
                "status": "processing",
                "message": "正在解析和切分文档...",
                "progress": 70,
                "chunk_count": 0
            }
        else:
            # TODO: 从RAG服务查询真实的chunk数量
            return {
                "status": "success",
                "message": "文档已入库完成，可以提问了",
                "progress": 100,
                "chunk_count": 0  # 实际应该查询RAG服务
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询上传状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

