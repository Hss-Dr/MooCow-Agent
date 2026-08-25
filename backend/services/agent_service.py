import re
import json
from collections.abc import AsyncGenerator
from agents.run import Runner, RunConfig
from multi_agent.orchestrator_agent import orchestrator_agent, orchestrator_agent_fast
from schemas.request import ChatMessageRequest
from services.stream_response_service import process_stream_response
from utils.response_util import ResponseFactory
from infrastructure.logging.logger import logger
from utils.jsonl_helper import JSONLHelper
import traceback
from schemas.response import ContentKind
from sqlalchemy.orm import Session as DBSession
from infrastructure.database.pg_database import get_db
from models.session import Session



class MultiAgentService:
    """
    多智能体业务服务类
    todo:
    process_task:方法前面加上async 以及返回值类型一定是AsyncGenerator
    """

    @classmethod
    async def process_task(cls, request: ChatMessageRequest, flag: bool) -> AsyncGenerator:
        """
        多智能体处理任务入口
        Args:
            request:  请求上下文

        Returns:
            AsyncGenerator：异步生成器对象（必须）
        """
        try:
            # 1. 获取请求上下文的信息
            user_id = request.context.user_id
            session_id = request.context.session_id
            user_query = request.query

            # 2. 准备历史对话 - 从JSONL读取
            db_gen = get_db()
            db: DBSession = next(db_gen)
            try:
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    raise ValueError(f"Session {session_id} not found")

                # 从JSONL读取历史消息
                jsonl_messages = JSONLHelper.read_messages(session.file_path, max_messages=50)
                chat_history = JSONLHelper.convert_to_openai_format(jsonl_messages)
                # 添加当前用户查询
                chat_history.append({"role": "user", "content": user_query})

                # 3. 运行Agent
                # 深度思考开关：开=推理模型（产生 THINKING 流），关=快速模型（直接作答）
                starting_agent = orchestrator_agent if request.deep_think else orchestrator_agent_fast
                logger.info(f"[Agent] 深度思考模式: {'开启' if request.deep_think else '关闭'}")

                # context 透传真实用户ID：RAG 工具需要用它对个人知识库检索/上传
                run_context = {"user_id": str(user_id), "query": user_query}

                streaming_result = Runner.run_streamed(
                    starting_agent=starting_agent,
                    input=chat_history,  # 列表
                    context=run_context,
                    max_turns=5,  # COT(思考 行动 观察)--->迭代多少次（不是异常重试）
                    run_config=RunConfig(tracing_disabled=True)
                )

                # 4. 处理Agent的事件流（事件流）
                async for chunk in process_stream_response(streaming_result):
                    yield chunk

                # 4.1 流结束后下发参考来源（RAG 检索命中的文档，供前端标记出处）
                retrieved_docs = run_context.get("retrieved_docs") or []
                if retrieved_docs:
                    yield "data: " + ResponseFactory.build_text(
                        json.dumps(retrieved_docs, ensure_ascii=False),
                        ContentKind.REFERENCE
                    ).model_dump_json() + "\n\n"
                    logger.info(f"[Reference] 下发 {len(retrieved_docs)} 个参考文档")

                # 5. 获取Agent的结果
                agent_result = streaming_result.final_output

                format_agent_result = re.sub(r'\n+', '\n', agent_result)
                # 6. 存储历史对话 - 这里不再手动保存，由chat_routes处理
                # chat_history.append({"role": "assistant", "content": format_agent_result})
                # Note: Message saving is handled by the chat_routes wrapper
            finally:
                db.close()
        except Exception as e:
            # 记录错误日志
            logger.error(f"AgentService.process_query执行出错: {str(e)}")
            logger.debug(f"异常详情: {traceback.format_exc()}")

            text = f"❌ 系统错误: {str(e)}"
            yield "data: " + ResponseFactory.build_text(
                text, ContentKind.PROCESS
            ).model_dump_json() + "\n\n"

            # 如果允许重试，则启动重试流程
            if flag:
                text = f"🔄 正在尝试自动重试..."
                yield "data: " + ResponseFactory.build_text(
                    text, ContentKind.PROCESS
                ).model_dump_json() + "\n\n"

                # 递归调用进行重试
                async for item in MultiAgentService.process_task(request,flag=False):
                    yield item
