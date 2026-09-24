from agents import function_tool, Runner, RunContextWrapper
from agents.run import RunConfig

from multi_agent.technical_agent import technical_agent
from multi_agent.service_agent import comprehensive_service_agent
from infrastructure.tools.mcp.mcp_servers import search_mcp_client, baidu_mcp_client
from infrastructure.clients.rag_client import rag_client

from infrastructure.logging.logger import logger


# 1. 定义技术专家智能体工具
@function_tool
async def consult_technical_expert(
        tool_context: RunContextWrapper,
        query: str,
) -> str:
    """
    【销售与售后专家】全链路智能体：处理新能源汽车销售售前、售后技术以及实时资讯。
    当用户询问：
    1. 销售售前："推荐一款车"、"XX万预算"、"车型对比"、"购车优惠"、"试驾"等购车咨询。
    2. 售后技术："怎么修"、"为什么会这样"、"如何操作"等故障/保养问题（电池、充电、续航、OTA等）。
    3. "今天股价"、"现在天气"等实时信息。
    请调用此工具。

    Args:
    query: 用户的原始问题或完整指令。
    """
    try:
        logger.info(f"[Route] 转交技术专家: {query[:30]}...")
        logger.info(f"[Route] 开始运行技术专家...")

        # ============================================================
        # 平台级强制预检索：产品/参数/售后类问题必须先查知识库。
        # 之前依赖模型自觉调用 query_rag_knowledge，模型经常跳过
        # 直接联网搜索，导致"已上传文档却检索不到"。这里在运行
        # Agent 前强制检索一次，有结果直接注入输入上下文。
        # ============================================================
        ctx = tool_context.context
        user_id = ctx.get("user_id") if isinstance(ctx, dict) else None
        agent_input = query

        try:
            kb_result = await rag_client.retrieve_documents(
                question=query,
                user_id=user_id
            )
            documents = kb_result.get("documents", []) or []
            total = kb_result.get("total", 0)

            if kb_result.get("status") == "success" and documents:
                # 写入运行上下文，供上层组装"参考来源"返回给前端
                if isinstance(ctx, dict):
                    ctx["retrieved_docs"] = [
                        {
                            "id": doc.get("document_id", ""),
                            "title": doc.get("document_name", "未知文档"),
                            "content": (doc.get("content_with_weight") or "")[:500],
                        }
                        for doc in documents
                    ]

                # 组装注入上下文（每篇截断 800 字，最多 5 篇，控制 prompt 体积）
                parts = []
                for i, doc in enumerate(documents[:5], 1):
                    name = doc.get("document_name", "未知文档")
                    content = (doc.get("content_with_weight") or "")[:800]
                    parts.append(f"[文档{i}] 《{name}》\n{content}")

                kb_block = "\n\n".join(parts)
                agent_input = (
                    f"用户问题：{query}\n\n"
                    f"以下是知识库中检索到的 {total} 个相关文档片段，"
                    f"【必须优先基于这些内容回答，严禁编造参数/价格】：\n\n{kb_block}\n\n"
                    f"若知识库内容不足以回答，再调用 bailian_web_search 联网搜索并注明来源。"
                )
                logger.info(f"[Route] 知识库预检索命中 {total} 个片段，已注入技术专家上下文")
            else:
                logger.info(f"[Route] 知识库预检索无结果（{total}），按正常流程处理")
        except Exception as e:
            # 预检索失败不阻断主流程，降级为原逻辑
            logger.warning(f"[Route] 知识库预检索失败（降级为原流程）: {e}")

        # context 透传（含 user_id 供 RAG 工具使用）
        result = await Runner.run(
            technical_agent,
            input=agent_input,
            context=tool_context.context,
            run_config=RunConfig(tracing_disabled=True)
        )

        logger.info(f"[Route] 技术专家执行完成，返回长度: {len(result.final_output) if result.final_output else 0}")
        return result.final_output
    except Exception as e:
        logger.error(f"[Route] 技术专家执行失败: {str(e)}")
        import traceback
        logger.error(f"[Route] 技术专家异常详情: {traceback.format_exc()}")
        return f"技术专家暂时无法回答: {str(e)}"


# 2. 定义全能业务智能体工具
@function_tool
async def query_service_station_and_navigate(
        query: str,
) -> str:
    """
        【服务站专家】处理线下新能源汽车服务站查询、充电站查询、位置查找和地图导航需求。
        当用户询问：
        1. "附近的维修点"、"找比亚迪服务中心"、"充电站在哪"（服务站查询）。
        2. "怎么去XX"、"导航到XX"（路径规划）。
        3. 任何涉及地理位置和线下服务站的请求。
        请调用此工具。
        Args:
            query: 用户的原始问题（包含隐含的位置信息）。
    """
    try:
        logger.info(f"[Route] 转交业务专家: {query[:30]}...")
        result = await Runner.run(
            comprehensive_service_agent,
            input=query,
            run_config=RunConfig(tracing_disabled=True)
        )
        return result.final_output
    except Exception as e:
        return f"业务专家暂时无法回答: {str(e)}"


# 3. 将工具暴露给主调度智能体
# 注意：query_rag_knowledge 只给技术专家用，主调度通过 consult_technical_expert 间接调用
AGENT_TOOLS = [
    consult_technical_expert,
    query_service_station_and_navigate,
]


async def run_technical_tool():
    """测试技术专家工具"""
    print("\n" + "=" * 80)
    print("测试技术专家Agent Tool")
    print("=" * 80)
    await search_mcp_client.connect()

    test_cases = ["今天理想汽车股价多少"]

    for query in test_cases:
        print(f"\n 查询: {query}")
        print("-" * 0)
        result = await consult_technical_expert(query=query)
        print(f"回答: {result}\n")

    await search_mcp_client.cleanup()


async def run_service_tool():
    """测试业务服务工具"""
    print("\n" + "=" * 80)
    print("测试业务服务Agent Tool")
    print("=" * 80)

    await baidu_mcp_client.connect()

    test_cases = [
        # "我想去比亚迪服务中心保养",
        "怎么去颐和园",
    ]

    for query in test_cases:
        print(f"\n查询: {query}")
        print("-" * 80)
        result = await query_service_station_and_navigate(query=query)
        print(f"回答: {result}\n")

    await baidu_mcp_client.cleanup()


async def main():
    # 1. 测试技术智能体工具
     await run_technical_tool()

    # 2. 测试全能业务智能体工具
    #await run_service_tool()
    # print("\n所有测试完成！\n")


# 以下是测试代码，可以独立运行测试每个Agent Tool
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
