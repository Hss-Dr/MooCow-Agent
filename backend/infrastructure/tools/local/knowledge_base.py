"""
RAG知识库工具

基于 MooCow-Agent RAG服务的知识库查询工具
支持文档检索和智能问答
"""
import asyncio
from typing import Dict, Optional
from agents import function_tool, RunContextWrapper
from infrastructure.logging.logger import logger
from infrastructure.clients.rag_client import rag_client


@function_tool
async def query_rag_knowledge(
    tool_context: RunContextWrapper,
    question: str,
) -> str:
    """
    从RAG知识库检索相关文档。

    适用场景：
    - 用户询问新能源汽车专业销售或售后问题（如"电池续航下降怎么办？"、"如何保养动力电池？"、"如何成为一名销售？"）
    - 需要查询文档中的具体信息

    本工具只返回检索到的文档片段，不生成答案。
    Agent 应基于返回的文档内容，用自己的推理能力生成准确答案。

    Args:
        question: 用户的具体问题
    """
    try:
        # 从请求上下文取真实用户ID（不暴露给LLM，避免模型乱填导致检索错库）
        user_id = None
        ctx = tool_context.context
        if isinstance(ctx, dict):
            user_id = ctx.get("user_id")

        logger.info(f"调用RAG知识库检索: {question}, user_id={user_id}")

        # 调用RAG客户端检索文档（纯检索，不生成答案）
        result = await rag_client.retrieve_documents(
            question=question,
            user_id=user_id
        )

        # 检查是否成功
        if result.get("status") == "error":
            error_msg = result.get("error", "未知错误")
            logger.error(f"RAG检索失败: {error_msg}")
            return f"❌ 知识库检索失败: {error_msg}\n\n建议：请确认RAG服务是否正常运行。"

        # 提取文档
        documents = result.get("documents", [])
        total = result.get("total", 0)

        # 如果没有检索到文档
        if total == 0 or not documents:
            return "📚 知识库中未找到相关文档。\n\n建议：\n1. 尝试换个方式提问\n2. 检查是否已上传相关文档到知识库\n3. 如果问题不需要文档支持，可以直接基于通用知识回答"

        # 把命中的文档写入运行上下文，供上层组装"参考来源"返回给前端
        # content 截断到 500 字，前端点击来源可展开查看片段
        if isinstance(ctx, dict):
            ctx["retrieved_docs"] = [
                {
                    "id": doc.get("document_id", ""),
                    "title": doc.get("document_name", "未知文档"),
                    "content": (doc.get("content_with_weight") or "")[:500],
                }
                for doc in documents
            ]

        # 格式化返回文档片段
        response = f"**📖 从知识库检索到 {total} 个相关文档片段**:\n\n"

        for i, doc in enumerate(documents, 1):
            doc_name = doc.get("document_name", "未知文档")
            content = doc.get("content_with_weight", "")
            doc_id = doc.get("document_id", "")

            response += f"**[文档 {i}] {doc_name}** (ID: {doc_id})\n"
            response += f"{content}\n\n"
            response += "---\n\n"

        response += "**💡 请基于上述文档内容，结合你的专业知识，为用户生成准确、详细的回答。**"

        return response

    except Exception as e:
        logger.error(f"RAG知识库检索异常: {str(e)}", exc_info=True)
        return f"❌ 检索知识库时发生错误: {str(e)}"


async def main():
    """测试函数"""
    result = await query_rag_knowledge(question="电池续航下降怎么解决?")
    print(result)


# 测试代码
if __name__ == "__main__":
    asyncio.run(main())


