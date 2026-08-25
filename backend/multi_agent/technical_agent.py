from infrastructure.ai.prompt_loader import load_prompt
from infrastructure.ai.openai_client import sub_model
from infrastructure.tools.local.knowledge_base import query_rag_knowledge
from infrastructure.tools.local.skill_tool import load_skill
from infrastructure.tools.mcp.mcp_servers import search_mcp_client
from agents import Agent, ModelSettings
from agents import Runner, RunConfig


# 1. 定义全链路智能体（销售售前 + 售后技术 + 实时资讯）
#    系统提示词只做场景判定；销售/售后具体玩法封装成 Skill，由 load_skill 按需加载注入对话
technical_agent = Agent(
    name="新能源汽车全链路智能体",
    instructions=load_prompt("technical_agent"),
    model=sub_model,
    model_settings=ModelSettings(temperature=0),  # 不要发挥内容(软件层面限制模型的发挥)
    tools=[
        query_rag_knowledge,  # RAG知识库检索（用户上下文注入真实 user_id）
        load_skill,           # 按需加载销售/售后技能（Skill 插件机制）
    ],
    mcp_servers=[search_mcp_client],
)


# 2. 测试全链路智能体
async def run_single_test(case_name: str, input_text: str):

    print(f"\n{'=' * 80}")
    print(f"测试用例: {case_name}")
    print(f"输入: \"{input_text}\"")
    print("-" * 80)
    try:
        await search_mcp_client.connect()
        print("思考中...")
        result = Runner.run_streamed(
            technical_agent,
            input=input_text,
            run_config=RunConfig(tracing_disabled=True),
        )

        async for event in result.stream_events():
            if event.type == "run_item_stream_event":
                if hasattr(event, "name") and event.name in ("tool_called", "tool_output"):
                    from agents import ToolCallItem, ToolCallOutputItem
                    if event.name == "tool_called" and isinstance(event.item, ToolCallItem):
                        raw = event.item.raw_item
                        print(f"\n调用工具: {raw.name} --> 参数: {raw.arguments}")
                    elif event.name == "tool_output" and isinstance(event.item, ToolCallOutputItem):
                        output = str(event.item.output)[:200]
                        print(f"工具输出(前200字): {output}")

        print(f"\n\nAgent的最终输出:\n{result.final_output}")
    except Exception as e:
        print(f"\n Error: {e}\n")
    finally:
        try:
            await search_mcp_client.cleanup()
        except:
            pass


async def main():
    test_cases = [
        # ("Case 1: 售后技术", "我的车电池充不进电了，怎么办？"),
        ("Case 2: 销售售前", "预算20万，想买一款适合家用的新能源SUV，推荐一下"),
        # ("Case 3: 实时资讯", "今天理想汽车股价多少？"),
        # ("Case 4: 闲聊拒绝", "给我讲个笑话"),
    ]

    for name, question in test_cases:
        await run_single_test(name, question)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
