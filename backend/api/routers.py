from fastapi.routing import APIRouter
from starlette.responses import StreamingResponse

from schemas.request import ChatMessageRequest, UserSessionsRequest
from services.agent_service import MultiAgentService
from infrastructure.logging.logger import logger

# 1. 定义请求路由器
router = APIRouter()


# 2. 定义对话请求
@router.post("/api/query", summary="智能体对话接口")
async def query(request_context: ChatMessageRequest) -> StreamingResponse:
    """
    SSE返回数据（流式响应）
    响应头中：text/event-stream
    Args:
        request_context: 请求上下文

    Returns:
        StreamingResponse

    """

    # 1. 获取请求上下文的属性
    user_id = request_context.context.user_id
    user_query = request_context.query
    print(request_context.flag)
    logger.info(f"用户 {user_id} 发送的待处理任务 {user_query}")

    # 2. 调用AgentService（智能体的业务服务类）
    async_generator_result = MultiAgentService.process_task(request_context, flag=True)

    # 3. 封装结果到StreamingResponse中
    return StreamingResponse(
        content=async_generator_result,
        status_code=200,
        media_type="text/event-stream"
    )


# Deprecated: This endpoint is replaced by /session/sessions with proper authentication
# Keeping for backward compatibility only
# @router.post("/api/user_sessions")
# def get_user_sessions(request: UserSessionsRequest):
#     """
#     DEPRECATED: Use /session/sessions instead
#     获取用户的所有会话记忆数据。
#     """
#     logger.warning("Deprecated endpoint /api/user_sessions called")
#     return {
#         "success": False,
#         "error": "This endpoint is deprecated. Please use /session/sessions with authentication."
#     }
