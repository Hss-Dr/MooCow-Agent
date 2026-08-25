"""
快速文档解析服务
处理文档解析和Redis存储相关的业务逻辑
"""

import os
import redis
from docx import Document
import pdfplumber
from io import BytesIO
from fastapi import HTTPException
from utils import logger
from typing import Tuple


class QuickParseService:
    """快速文档解析服务类
    
    支持的文件格式及限制:
    - PDF: 不超过4页
    - DOCX: 不超过4000字符
    - TXT: 不超过4000字符
    
    解析结果存储到Redis，默认保存2小时
    """
    
    def __init__(self):
        # Redis 连接配置
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_db = int(os.getenv('REDIS_DB', 0))
        
        # 创建 Redis 客户端
        self.redis_client = redis.Redis(
            host=self.redis_host, 
            port=self.redis_port, 
            db=self.redis_db, 
            decode_responses=True
        )
        
        # 支持的文件格式
        self.supported_formats = ['docx', 'pdf', 'txt']
        
        # 页数限制（仅用于PDF）
        self.max_pages = 4
        
        # 字符数限制（用于TXT和DOCX）
        self.max_characters = 4000
        
        # Redis 过期时间（2小时）
        self.redis_expire_seconds = 7200

    def validate_file_format(self, filename: str) -> str:
        """验证文件格式并返回扩展名"""
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_extension = filename.lower().split('.')[-1]
        if file_extension not in self.supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式，仅支持 {', '.join(self.supported_formats)}"
            )
        
        return file_extension

    def check_session_exists(self, session_id: str) -> bool:
        """检查会话是否已存在文档"""
        return self.redis_client.exists(session_id)

    def parse_docx(self, file_content: bytes) -> Tuple[str, int]:
        """解析 DOCX 文件，返回文本内容和字符数"""
        try:
            doc = Document(BytesIO(file_content))
            text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text.append(paragraph.text.strip())
            
            content = '\n'.join(text)
            char_count = len(content)
            
            # 检查字符数限制
            if char_count > self.max_characters:
                raise HTTPException(
                    status_code=400, 
                    detail=f"DOCX 文档字符数({char_count})超过限制({self.max_characters}字符)"
                )
            
            return content, char_count
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"DOCX 文件解析失败: {str(e)}")

    def parse_pdf(self, file_content: bytes) -> Tuple[str, int]:
        """解析 PDF 文件，返回文本内容和页数"""
        try:
            pdf_file = BytesIO(file_content)
            
            # 使用 pdfplumber 解析
            with pdfplumber.open(pdf_file) as pdf:
                pages = len(pdf.pages)
                if pages > self.max_pages:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"PDF 文档页数({pages})不能超过 {self.max_pages} 页"
                    )
                
                text = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
                
                return '\n'.join(text), pages
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF 文件解析失败: {str(e)}")

    def parse_txt(self, file_content: bytes) -> Tuple[str, int]:
        """解析 TXT 文件，返回文本内容和字符数"""
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'ascii']
            content = None
            
            for encoding in encodings:
                try:
                    content = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise HTTPException(status_code=400, detail="无法识别文本文件编码")
            
            char_count = len(content)
            
            # 检查字符数限制
            if char_count > self.max_characters:
                raise HTTPException(
                    status_code=400, 
                    detail=f"TXT 文档字符数({char_count})超过限制({self.max_characters}字符)"
                )
            
            return content, char_count
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"TXT 文件解析失败: {str(e)}")

    def parse_document(self, file_content: bytes, file_extension: str) -> Tuple[str, int]:
        """根据文件类型解析文档
        
        返回:
            tuple: (文档内容, 统计值)
            - PDF文件返回 (内容, 页数)
            - TXT/DOCX文件返回 (内容, 字符数)
        """
        if file_extension == 'docx':
            return self.parse_docx(file_content)
        elif file_extension == 'pdf':
            return self.parse_pdf(file_content)
        elif file_extension == 'txt':
            return self.parse_txt(file_content)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式")

    def store_to_redis(self, session_id: str, content: str) -> None:
        """将内容存储到Redis"""
        try:
            self.redis_client.setex(
                session_id, 
                self.redis_expire_seconds,
                content
            )
            logger.info(f"文档内容已存储到Redis，session_id: {session_id}")
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"存储到Redis失败: {str(e)}"
            )

    def get_from_redis(self, session_id: str) -> str:
        """从Redis获取内容"""
        content = self.redis_client.get(session_id)
        if not content:
            raise HTTPException(
                status_code=404, 
                detail="未找到该会话的文档内容，可能已过期或未上传"
            )
        return content

    def get_ttl(self, session_id: str) -> int:
        """获取Redis键的剩余过期时间"""
        return self.redis_client.ttl(session_id)

    def quick_parse_document(self, session_id: str, filename: str, file_content: bytes) -> dict:
        """快速解析文档的主要业务逻辑"""
        # 验证文件格式
        file_extension = self.validate_file_format(filename)
        
        # 检查会话是否已存在文档
        if self.check_session_exists(session_id):
            raise HTTPException(
                status_code=400, 
                detail="该会话已有文档，每个session_id只能上传一个文档"
            )
        
        # 验证文件内容
        if not file_content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 解析文档
        content, count_value = self.parse_document(file_content, file_extension)
        
        # 存储到Redis
        self.store_to_redis(session_id, content)
        
        # 根据文件类型返回不同的统计信息
        if file_extension == 'pdf':
            return {
                "status": "success",
                "message": "文档解析完成",
                "session_id": session_id,
                "filename": filename,
                "file_type": file_extension,
                "pages": count_value,
                "content_length": len(content),
                "limit_info": f"PDF页数限制: {self.max_pages}页",
                "expiry_hours": self.redis_expire_seconds // 3600
            }
        else:  # txt 或 docx
            return {
                "status": "success",
                "message": "文档解析完成",
                "session_id": session_id,
                "filename": filename,
                "file_type": file_extension,
                "character_count": count_value,
                "content_length": len(content),
                "limit_info": f"字符数限制: {self.max_characters}字符",
                "expiry_hours": self.redis_expire_seconds // 3600
            }

    def get_parsed_content(self, session_id: str) -> dict:
        """获取已解析的文档内容"""
        content = self.get_from_redis(session_id)
        ttl = self.get_ttl(session_id)
        
        return {
            "status": "success",
            "session_id": session_id,
            "content": content,
            "content_length": len(content),
            "remaining_seconds": ttl if ttl > 0 else 0
        }


# 创建全局服务实例
quick_parse_service = QuickParseService() 