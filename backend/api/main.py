import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routers import router
from api.session_routes import router as session_router
from api.repository_routes import router as repository_router
from api.chat_routes import router as chat_router
from api.auth_routes import router as auth_router
from infrastructure.logging.logger import logger
from infrastructure.tools.mcp.mcp_manager import mcp_connect, mcp_cleanup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理

    在应用启动时建立MCP连接，在应用关闭时清理连接。
    确保资源正确初始化和释放。
    """
    # 应用启动时执行
    logger.info("应用启动，建立MCP连接...")
    try:
        await mcp_connect()
        logger.info("MCP连接建立完成")
    except Exception as e:
        logger.error(f"MCP连接建立失败: {str(e)}")

    yield  # 应用运行期间（先别释放mcp链接 去处理请求...）

    # 应用关闭时执行
    logger.info("应用关闭，清理MCP连接...")
    try:
        await mcp_cleanup()
        logger.info("MCP连接清理完成")
    except Exception as e:
        logger.error(f"MCP连接清理失败: {str(e)}")


def create_fast_api() -> FastAPI:
    # 1. 创建FastApi实例,绑定了生命周期事件
    app = FastAPI(title="ITS API", lifespan=lifespan)

    # 2. 处理跨域
    app.add_middleware(
        CORSMiddleware,
        # CORSMiddleware 会自动拦截后端的响应 并贴上这些标签 Access-Control-Allow-Origin Access-Control-Allow-Methods Access-Control-Allow-Headers
        allow_origins=["*"],  # 生产环境应限制为特定域名
        allow_credentials=True,  # cookie(自定义的key value)(user_id)
        allow_methods=["*"],  # 任意的请求都可以（POST）
        allow_headers=["*"],  # 请求头中带上自己的信息（token）
    )

    # 3. 注册各种路由
    app.include_router(router=router, tags=["agent"])  # 原有Agent路由
    app.include_router(router=auth_router, tags=["auth"])  # 认证路由
    app.include_router(router=session_router, tags=["session"])  # 会话管理
    app.include_router(router=repository_router, tags=["repository"])  # 文件管理
    app.include_router(router=chat_router, tags=["chat"])  # 聊天功能

    # 4.返回创建的FastAPI
    return app


# 创建全局app实例供uvicorn使用
app = create_fast_api()


if __name__ == '__main__':
    print("1.准备启动Web服务器（端口8080）")
    try:
        # 修改为8080端口，避免与RAG服务(8001)冲突
        uvicorn.run(app=create_fast_api(), host="127.0.0.1", port=8080)

        logger.info("2.启动Web服务器成功...")

    except KeyboardInterrupt as e:
        logger.error(f"2.启动Web服务器失败: {str(e)}")
