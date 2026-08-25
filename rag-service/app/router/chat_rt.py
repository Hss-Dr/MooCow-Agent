from fastapi import APIRouter, Body, UploadFile, File, HTTPException, Query, Security, status, Depends
import uuid
from schemas.chat import SessionResponse, ChatRequest
from fastapi.responses import StreamingResponse
import os
from dotenv import load_dotenv
from typing import List, Optional
from service.core.file_parse import execute_insert_process
from service.core.api.utils.file_utils import get_project_base_directory
from fastapi_jwt import JwtAuthorizationCredentials
from service.core.retrieval import retrieve_content
from service.core.chat import get_chat_completion
from service.auth import access_security, access_security_optional
from utils import logger
from database.knowledgebase_operations import insert_knowledgebase, verify_user_knowledgebase
from sqlalchemy.orm import Session
from sqlalchemy import select
from models.message import KnowledgeBase
from utils.database import get_db
from service.quick_parse_service import quick_parse_service
from service.document_upload_service import DocumentUploadService
from schemas.document_upload import DocumentUploadResponse, SessionDocumentsResponse, SessionDocumentSummary
import os

# 加载 .env 文件
load_dotenv()

# 配置日志
logger.info(f"ES_HOST: {os.getenv('ES_HOST')}")
logger.info(f"ELASTICSEARCH_URL: {os.getenv('ELASTICSEARCH_URL')}")

# 混合库配置:公共共享库索引名 + 管理员白名单
SHARED_KB_INDEX = os.getenv("SHARED_KB_INDEX", "company_kb")
ADMIN_USER_IDS = {x.strip() for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()}

router = APIRouter()

##################################
# 创建一个新的对话 Session
##################################

@router.post("/create_session", response_model=SessionResponse)
async def create_session(
    credentials: JwtAuthorizationCredentials = Security(access_security),
):
    try:
        user_id = credentials.subject.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        session_id = str(uuid.uuid4()).replace("-", "")[:16]

        return {
            "session_id": session_id,
            "status": "success",
            "message": "Session created successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

##################################
# 快速文档解析接口
##################################

@router.post("/quick_parse")
async def quick_parse_document(
    session_id: str = Query(..., description="会话ID"),
    file: UploadFile = File(..., description="要解析的文档"),
    credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    """
    快速文档解析接口
    - 支持文档格式：docx, pdf, txt
    - 限制文档页数不超过4页
    - 每个session_id只能传递一个文档
    - 解析结果存储到Redis，保存时间为2小时
    """
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 读取文件内容
        file_content = await file.read()
        
        # 获取文件信息
        file_size = len(file_content)
        file_extension = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        document_type = file_extension.replace(".", "") if file_extension else "unknown"
        
        # 调用服务层处理业务逻辑
        result = quick_parse_service.quick_parse_document(
            session_id=session_id,
            filename=file.filename,
            file_content=file_content
        )
        
        # 记录文档上传信息到数据库
        try:
            DocumentUploadService.create_upload_record(
                db=db,
                session_id=session_id,
                document_name=file.filename,
                document_type=document_type,
                file_size=file_size
            )
            logger.info(f"文档上传记录已保存: session_id={session_id}, document_name={file.filename}")
        except Exception as db_error:
            logger.error(f"保存文档上传记录失败: {str(db_error)}")
            # 数据库记录失败不影响主要功能，继续返回解析结果
        
        logger.info(f"用户 {user_id} 的文档解析完成，session_id: {session_id}")
        return result

    except HTTPException as e:
        logger.error(f"快速解析错误: {str(e)}")
        raise e
    except Exception as e:
        logger.exception(f"快速解析发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"内部服务器错误: {str(e)}"
        )

##################################
# 获取解析内容接口
##################################

@router.get("/get_parsed_content")
async def get_parsed_content(
    session_id: str = Query(..., description="会话ID"),
    credentials: JwtAuthorizationCredentials = Security(access_security),
):
    """
    获取已解析的文档内容
    """
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 调用服务层获取内容
        result = quick_parse_service.get_parsed_content(session_id)
        
        logger.info(f"用户 {user_id} 获取解析内容，session_id: {session_id}")
        return result

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

##################################
# 基于ragflow知识库对话
##################################

@router.post("/retrieve_documents")
async def retrieve_documents(
    request: ChatRequest = Body(..., description="User question"),
    user_id: str = Query(..., description="User ID"),
    credentials: Optional[JwtAuthorizationCredentials] = Security(access_security_optional),
):
    """
    纯检索接口：从知识库检索相关文档，不生成答案。
    供 backend agent 调用，答案由 agent 自己生成。
    """
    try:
        logger.info(f"检索请求 - user_id: {user_id}, 问题: {request.message}")

        # 从知识库检索内容
        try:
            # 合并检索:公共共享库 + 本人个人库（逗号多索引，ES 侧合并排序）
            references = retrieve_content(f"{SHARED_KB_INDEX},{user_id}", request.message)
            logger.info(f"检索到 {len(references)} 条相关文档 (indices={SHARED_KB_INDEX},{user_id})")

            return {
                "status": "success",
                "documents": references,
                "total": len(references)
            }
        except Exception as e:
            logger.warning(f"检索失败: {str(e)}")
            return {
                "status": "no_documents",
                "documents": [],
                "total": 0,
                "message": f"未找到相关文档或检索失败: {str(e)}"
            }

    except Exception as e:
        logger.exception(f"检索服务异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/chat_on_docs")
async def chat_on_docs(
    session_id: str = Query(...),
    request: ChatRequest = Body(..., description="User message"),
    credentials: Optional[JwtAuthorizationCredentials] = Security(access_security_optional),
):
    """
    遗留接口（检索+生成）：为兼容保留，新调用方请使用 /retrieve_documents。
    """
    try:
        # 有token时使用token中的user_id；无token（内部服务调用）时用session_id作为user_id
        if credentials and credentials.subject.get("user_id"):
            user_id = str(credentials.subject.get("user_id"))
        else:
            user_id = session_id

        logger.info(f"开始处理用户 {user_id} 的请求")
        logger.info(f"问题内容: {request.message}")

        question = request.message

        # 尝试从知识库检索内容，如果没有知识库也不报错
        references = []
        try:
            logger.info("开始检索相关内容...")
            # 合并检索:公共共享库 + 本人个人库
            references = retrieve_content(f"{SHARED_KB_INDEX},{user_id}", question)
            logger.info(f"检索到 {len(references)} 条相关内容 (indices={SHARED_KB_INDEX},{user_id})")
        except Exception as e:
            logger.info(f"用户 {user_id} 没有知识库或检索失败: {str(e)}，将不使用知识库内容")
            references = []

        logger.info("开始生成回答...")
        # 返回流式响应
        return StreamingResponse(
            get_chat_completion(session_id, question, references, user_id),
            media_type="text/event-stream"
        )

    except HTTPException as e:
        logger.error(f"HTTP错误: {str(e)}")
        raise e
    except Exception as e:
        logger.exception(f"发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/upload_files")
async def upload_files(
    session_id: Optional[str] = Query(None),
    scope: str = Query("personal", description="personal=个人私有库(默认); shared=公共共享库(仅管理员)"),
    files: List[UploadFile] = File(...),
    credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db)
):
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 如果没有 session_id，使用 user_id 作为 session_id（仅用于磁盘目录组织，不再作为 ES 索引名）
        if session_id is None:
            session_id = user_id

        # 决定目标 ES 索引与 PG 归属：
        # - scope=shared: 写入公共共享库（仅管理员），归属记为公共库
        # - scope=personal(默认): 写入个人私有库（索引名=user_id），修复原“上传用session_id、检索用user_id”不一致
        if scope == "shared":
            if user_id not in ADMIN_USER_IDS:
                raise HTTPException(status_code=403, detail="只有管理员可以上传到公共知识库")
            index_target = SHARED_KB_INDEX
            owner_id = SHARED_KB_INDEX
        else:
            index_target = user_id
            owner_id = user_id

        # 确保 storage/file 文件夹存在
        storage_dir = os.path.join(get_project_base_directory(), "storage/file")
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        # 根据 session_id 创建子文件夹
        session_dir = os.path.join(storage_dir, session_id)
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
        
        # 检查文件名是否重复
        existing_files = []
        for file in files:
            file_name = file.filename
            # 查询数据库中是否已存在该文件名（按归属库判重：公共库全局判重，个人库按用户判重）
            stmt = select(KnowledgeBase).where(
                KnowledgeBase.user_id == owner_id,
                KnowledgeBase.file_name == file_name
            )
            existing_file = db.execute(stmt).scalar_one_or_none()
            if existing_file:
                existing_files.append(file_name)
        
        if existing_files:
            raise HTTPException(
                status_code=400,
                detail=f"以下文件已存在，请勿重复上传: {', '.join(existing_files)}"
            )

        # 处理文件上传
        successful_files = []
        failed_files = []
        
        for file in files:
            file_name = file.filename
            file_path = os.path.join(session_dir, file_name)
            
            try:
                # 读取文件内容
                file_content = await file.read()
                
                # 验证文件内容不为空
                if not file_content:
                    failed_files.append(f"{file_name}: 文件内容为空")
                    continue
                
                # 对于 Excel 文件，进行额外验证
                if file_name.lower().endswith(('.xlsx', '.xls')):
                    # 检查文件头，xlsx 文件应该是 ZIP 格式
                    if file_name.lower().endswith('.xlsx'):
                        # XLSX 文件应该以 PK 开头（ZIP 文件头）
                        if not file_content.startswith(b'PK'):
                            failed_files.append(f"{file_name}: 不是有效的 XLSX 文件格式，可能是 XLS 文件")
                            continue
                    elif file_name.lower().endswith('.xls'):
                        # XLS 文件有特定的文件头
                        if not (file_content.startswith(b'\xd0\xcf\x11\xe0') or 
                               file_content.startswith(b'\x09\x08')):
                            failed_files.append(f"{file_name}: 不是有效的 XLS 文件格式")
                            continue
                
                # 保存文件到本地
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
                
                # 验证文件大小
                if os.path.getsize(file_path) != len(file_content):
                    failed_files.append(f"{file_name}: 文件保存失败，大小不匹配")
                    continue
                
                # 保存文件 URL 和 Base64 编码的文件流
                file_url = f"{storage_dir}/{session_id}/{file_name}"
                logger.info(f"Processing file: {file_url}")

                # 尝试解析和插入文档
                try:
                    execute_insert_process(file_url, file_name, index_target)
                    logger.info(f"数据插入es成功: {file_name} -> index={index_target}")

                    insert_knowledgebase(owner_id, file_name)
                    logger.info(f"数据插入pg成功: {file_name} -> owner={owner_id}")
                    
                    successful_files.append(file_name)
                    
                except Exception as parse_error:
                    logger.error(f"文件解析失败 {file_name}: {str(parse_error)}")
                    failed_files.append(f"{file_name}: 文件解析失败 - {str(parse_error)}")
                    # 删除已保存的文件
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    continue
                        
            except Exception as e:
                logger.error(f"处理文件失败 {file_name}: {str(e)}")
                failed_files.append(f"{file_name}: 处理失败 - {str(e)}")
                continue

        # 构建返回结果
        if successful_files and not failed_files:
            return {
                "status": "success",
                "message": "所有文件解析成功",
                "successful_files": successful_files,
                "total_files": len(files)
            }
        elif successful_files and failed_files:
            return {
                "status": "partial_success",
                "message": f"部分文件解析成功，{len(successful_files)} 个成功，{len(failed_files)} 个失败",
                "successful_files": successful_files,
                "failed_files": failed_files,
                "total_files": len(files)
            }
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "failed",
                    "message": "所有文件解析失败",
                    "failed_files": failed_files,
                    "total_files": len(files)
                }
            )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

##################################
# 查询会话文档上传信息接口
##################################

@router.get("/sessions/{session_id}/documents", response_model=SessionDocumentsResponse)
async def get_session_documents(
    session_id: str,
    credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    """
    获取指定会话的所有文档上传记录
    """
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 获取会话的所有文档记录
        documents = DocumentUploadService.get_session_documents(db, session_id)
        has_documents = len(documents) > 0
        
        return SessionDocumentsResponse(
            session_id=session_id,
            has_documents=has_documents,
            documents=[DocumentUploadResponse.from_orm(doc) for doc in documents],
            total_count=len(documents)
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"获取会话文档信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}/documents/summary", response_model=SessionDocumentSummary)
async def get_session_document_summary(
    session_id: str,
    credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db),
):
    """
    获取指定会话的文档上传摘要信息
    """
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 检查是否有上传的文档
        has_documents = DocumentUploadService.has_uploaded_documents(db, session_id)
        
        # 获取最新的文档信息
        latest_document = DocumentUploadService.get_latest_document(db, session_id)
        
        # 获取总文档数量
        all_documents = DocumentUploadService.get_session_documents(db, session_id)
        total_documents = len(all_documents)
        
        return SessionDocumentSummary(
            session_id=session_id,
            has_documents=has_documents,
            latest_document_name=latest_document.document_name if latest_document else None,
            latest_document_type=latest_document.document_type if latest_document else None,
            latest_upload_time=latest_document.upload_time if latest_document else None,
            total_documents=total_documents
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"获取会话文档摘要失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )