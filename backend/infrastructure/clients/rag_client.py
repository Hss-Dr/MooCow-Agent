"""
RAG服务客户端

封装对 MooCow-Agent RAG服务的HTTP调用，提供：
1. 知识库检索
2. 流式对话
3. 文档上传
"""
import httpx
import json
import re
from typing import Dict, List, Optional, AsyncGenerator
from infrastructure.logging.logger import logger
from config.settings import settings
from services.auth_service import create_token


class RAGClient:
    """RAG服务客户端"""

    def __init__(self):
        self.base_url = settings.RAG_SERVICE_URL
        self.timeout = settings.RAG_SERVICE_TIMEOUT
        self.default_user_id = settings.RAG_DEFAULT_USER_ID

    async def retrieve_documents(
        self,
        question: str,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        从RAG服务检索文档（纯检索，不生成答案）

        Args:
            question: 用户问题
            user_id: 用户ID

        Returns:
            Dict: {
                "status": "success" | "no_documents" | "error",
                "documents": List[Dict],  # 检索到的文档片段
                "total": int
            }
        """
        if not user_id:
            user_id = self.default_user_id

        async with httpx.AsyncClient(trust_env=False) as client:
            try:
                logger.info(f"调用RAG检索: question={question}, user_id={user_id}")

                # 调用 RAG 的纯检索接口
                response = await client.post(
                    f"{self.base_url}/retrieve_documents",
                    params={"user_id": user_id},
                    json={"message": question},
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"RAG检索成功，返回{result.get('total', 0)}个文档")
                return result

            except httpx.HTTPError as e:
                logger.error(f"RAG服务HTTP错误: {str(e)}")
                return {
                    "status": "error",
                    "error": f"RAG服务请求失败: {str(e)}",
                    "documents": [],
                    "total": 0
                }
            except Exception as e:
                logger.error(f"RAG检索异常: {str(e)}")
                return {
                    "status": "error",
                    "error": f"RAG检索失败: {str(e)}",
                    "documents": [],
                    "total": 0
                }

    async def retrieve_from_rag(
        self,
        question: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        从RAG服务检索知识并获取回答

        Args:
            question: 用户问题
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Dict: 包含回答和文档引用的字典
                {
                    "answer": str,  # AI回答
                    "documents": List[Dict],  # 参考文档列表
                    "recommended_questions": List[str],  # 推荐问题
                    "status": str  # 状态: "success" 或 "error"
                }
        """
        if not user_id:
            user_id = self.default_user_id
        if not session_id:
            session_id = user_id

        async with httpx.AsyncClient(trust_env=False) as client:
            try:
                logger.info(f"调用RAG服务检索: question={question}, user_id={user_id}")

                # 调用 MooCow-Agent 的 chat_on_docs 接口
                response = await client.post(
                    f"{self.base_url}/chat_on_docs",
                    params={"session_id": session_id},
                    json={"message": question},
                    timeout=self.timeout,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream"
                    }
                )
                response.raise_for_status()

                # 解析流式响应（SSE格式）
                result = await self._parse_sse_response(response.text)
                logger.info(f"RAG检索成功，返回{len(result.get('documents', []))}个文档")

                return result

            except httpx.HTTPError as e:
                logger.error(f"RAG服务HTTP错误: {str(e)}")
                return {
                    "status": "error",
                    "error": f"RAG服务请求失败: {str(e)}",
                    "answer": "",
                    "documents": []
                }
            except Exception as e:
                logger.error(f"RAG检索异常: {str(e)}")
                return {
                    "status": "error",
                    "error": f"RAG检索失败: {str(e)}",
                    "answer": "",
                    "documents": []
                }

    async def _parse_sse_response(self, sse_text: str) -> Dict:
        """
        解析SSE格式的流式响应

        Args:
            sse_text: SSE格式的响应文本

        Returns:
            Dict: 解析后的结果
        """
        answer_parts = []
        documents = []
        recommended_questions = []
        thinking_parts = []

        lines = sse_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 解析 SSE 事件
            if line.startswith('event:'):
                event_type = line.split(':', 1)[1].strip()
                continue

            if line.startswith('data:'):
                data_str = line.split(':', 1)[1].strip()

                # 跳过 [DONE] 标记
                if data_str == '[DONE]':
                    continue

                try:
                    data = json.loads(data_str)

                    # 提取文档信息
                    if 'documents' in data:
                        documents = data['documents']

                    # 提取回答内容
                    if 'content' in data:
                        content = data.get('content', '')
                        is_thinking = data.get('thinking', False)

                        if is_thinking:
                            thinking_parts.append(content)
                        else:
                            answer_parts.append(content)

                    # 提取推荐问题
                    if 'recommended_questions' in data:
                        recommended_questions = data['recommended_questions']

                except json.JSONDecodeError:
                    logger.warning(f"无法解析SSE数据: {data_str}")
                    continue

        # 组合完整回答
        full_answer = ''.join(answer_parts)

        return {
            "status": "success",
            "answer": full_answer,
            "documents": documents,
            "recommended_questions": recommended_questions,
            "thinking": ''.join(thinking_parts) if thinking_parts else None
        }

    async def upload_documents(
        self,
        files: List[Dict],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        scope: str = "personal"
    ) -> Dict:
        """
        上传文档到RAG知识库

        Args:
            files: 文件列表，每个文件包含 name 和 content
            user_id: 用户ID
            session_id: 会话ID
            scope: personal=个人私有库(默认); shared=公共共享库(仅管理员)

        Returns:
            Dict: 上传结果
        """
        if not user_id:
            user_id = self.default_user_id
        if not session_id:
            session_id = user_id

        # RAG服务的 /upload_files 需要JWT认证；backend与RAG共享同一密钥，
        # 这里为服务间调用签发一个有效token，避免401。
        token = create_token(user_id, str(user_id))

        # 将 [{"name":..., "content":...}] 转换为 httpx 的 multipart 格式：
        # RAG服务端字段名是 "files"（List[UploadFile]），必须逐个以 (字段名, (文件名, 字节流)) 传入。
        multipart_files = [
            ("files", (f["name"], f["content"]))
            for f in files
        ]

        async with httpx.AsyncClient(trust_env=False) as client:
            try:
                # 调用 upload_files 接口
                response = await client.post(
                    f"{self.base_url}/upload_files",
                    params={"session_id": session_id, "scope": scope},
                    files=multipart_files,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"文档上传成功: {result}")
                return result

            except httpx.HTTPStatusError as e:
                # 提取 RAG 响应体里的 detail（如"文件已存在"），比裸的 Client error 更可读
                detail = ""
                try:
                    detail = e.response.json().get("detail", "")
                except Exception:
                    pass
                err_msg = detail or str(e)
                logger.error(f"文档上传失败: {err_msg}")
                return {
                    "status": "error",
                    "error": f"文档上传失败: {err_msg}"
                }
            except Exception as e:
                err_msg = str(e) or type(e).__name__
                logger.error(f"文档上传失败: {err_msg}")
                return {
                    "status": "error",
                    "error": f"文档上传失败: {err_msg}"
                }

    async def health_check(self) -> bool:
        """
        检查RAG服务健康状态

        Returns:
            bool: 服务是否正常
        """
        async with httpx.AsyncClient(trust_env=False) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/docs",
                    timeout=5
                )
                return response.status_code == 200
            except Exception as e:
                logger.error(f"RAG服务健康检查失败: {str(e)}")
                return False


# 创建全局客户端实例
rag_client = RAGClient()

