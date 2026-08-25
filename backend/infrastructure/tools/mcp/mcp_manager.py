from infrastructure.logging.logger import logger
from infrastructure.tools.mcp.mcp_servers import (
    search_mcp_client,
    baidu_mcp_client,
)
"""
与MCP服务端建立连接和取消连接
"""
async def mcp_connect():
    # 建立MCP连接
    try:
        await baidu_mcp_client.connect()
    except Exception as e:
        logger.error(f"百度地图MCP连接失败: {str(e)}")
    try:
        await search_mcp_client.connect()
    except Exception as e:
        logger.error(f"搜索MCP连接失败: {str(e)}")


async def mcp_cleanup():
    # 清理MCP连接
    try:
        await baidu_mcp_client.cleanup()
    except Exception as e:
        logger.warning(f"百度地图MCP清理时出现非致命错误: {e}")
    try:
        await search_mcp_client.cleanup()
    except Exception as e:
        logger.warning(f"搜索MCP清理时出现非致命错误: {e}")