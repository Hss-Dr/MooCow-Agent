import asyncio
from agents import (
    Agent,
    ModelSettings,
    Runner
)
from infrastructure.ai.openai_client import sub_model
from infrastructure.ai.openai_client import main_model, main_fast_model
from infrastructure.ai.prompt_loader import load_prompt
from multi_agent.agent_factory import AGENT_TOOLS
from infrastructure.tools.mcp.mcp_servers import search_mcp_client, baidu_mcp_client
from contextlib import AsyncExitStack

# 1. 创建主调度智能体（深度思考版：推理模型，产生 THINKING 流）
orchestrator_agent = Agent(
    name="新能源汽车主调度智能体",
    instructions=load_prompt("orchestrator_v1"),
    model=main_model,     # 推理模型（DeepSeek-R1）：主调度推理 + 思考流；已实测 R1 支持 function_call 工具路由
    # model=sub_model,    # 通用模型（DeepSeek-V3，干活为主）——子智能体仍使用
    model_settings=ModelSettings(
        temperature=0,
    ),
    # 直接使用Agent Tools
    tools=AGENT_TOOLS,
)

# 快速模式版（深度思考关闭时使用：无推理过程的快速模型）
orchestrator_agent_fast = Agent(
    name="新能源汽车主调度智能体",
    instructions=load_prompt("orchestrator_v1"),
    model=main_fast_model,
    model_settings=ModelSettings(
        temperature=0,
    ),
    tools=AGENT_TOOLS,
)


# 3. 测试方法
async def run_single_test(case_name: str, input_text: str):
    print(f"\n{'=' * 80}")
    print(f"测试用例: {case_name}")
    print(f"输入: \"{input_text}\"")
    print("-" * 80)

    # 使用 AsyncExitStack 同时管理多个连接
    async with AsyncExitStack() as stack:
        try:
            print("连接 MCP 服务中...")
            # 1. 进入上下文
            await stack.enter_async_context(search_mcp_client)
            await stack.enter_async_context(baidu_mcp_client)
            print("思考中...")

            # 2. 使用流式处理运行 Orchestrator Agent
            result = Runner.run_streamed(
                starting_agent=orchestrator_agent,
                input=input_text,
            )

            # 3. 遍历流式事件
            async for event in result.stream_events():

                # 3.1 run_item_stream_event级别的事假（Agent运行时产生的事假）
                if event.type == "run_item_stream_event":
                    # a. Agent运行时的工具调用事件
                    if hasattr(event, "name") and event.name == "tool_called":
                        from agents import ToolCallItem
                        if isinstance(event.item, ToolCallItem):
                            raw_item = event.item.raw_item
                            print(f"\n调用工具名:{raw_item.name}--->工具参数:{raw_item.arguments}")

                    # b. Agent运行时的工具执行完后事件
                    elif hasattr(event, 'name') and event.name == "tool_output":
                        from agents import ToolCallOutputItem
                        if isinstance(event.item, ToolCallOutputItem):
                            print(f"调用工具结果:{event.item.output}")

            # 4. 打印最终结果（最后协调Agent的输出）
            print(f"\n最终输出（来自 {result.last_agent.name}）:")
            print(f"{result.final_output}")

        except Exception as e:
            print(f"\n 异常原因 {e}\n")


async def main():
    print("\n" + "=" * 80)
    print("测试协调Agent (Orchestrator)")
    print("=" * 80)

    # 定义测试案例
    test_cases = [
        # A:咨询技术智能体
        #("单个任务（实时问题）", "今天新能源汽车圈发生了些什么事儿"),
        # ("单个任务（技术问题）", "为什么电动车冬天续航会明显缩水呢？"),
        # ("组合任务（1.技术问题 2.资讯）", "为什么电动车冬天续航会明显缩水呢？，顺便准备看一下今天天气怎么样"),
        # ("组合任务（1.资讯 2.技术问题 ）", "先准备看一下今天天气怎么样，顺便在问一下我最近车总是充不进电，怎么解决?")

        # 服务站与导航智能体
        # ("单个任务（服务站查询）", "帮我找个最近的充电站"),
        # ("单个任务（POI导航）", "天安门广场都有哪些商场"),
        # ("组合任务（1.服务站 2.POI）", "帮我导航到最近的比亚迪服务中心？，顺便准备看一下它附近都有哪些商场"),
        # ("组合任务（1.POI 2.服务站）", "昌平区温都水城有哪些健身房，然后再看一下附近有哪些服务站，我准备保养车")


        # ("多跳任务(先实时问题在服务站)","查一下今天北京的天气预报，如果没有下雨的话，就帮我找一家最近的服务站，我去保养车。"),
        # ("多跳任务(先技术问题在服务站)","我的蔚来汽车充电报错怎么解决？如果太复杂处理不了，就直接帮我导航去最近的蔚来官方服务中心。"),
        # ("混合需求(先实时问题在POI导航)", "帮我查一下今天故宫的门票售罄了吗？如果没有，请给导航去故宫博物院。"),
        # ("多跳任务(先技术问题在POI导航)", "车辆无法充电怎么办？问完这个，请帮我导航去清华大学，我想去拍夜景。"),
        # ("多跳任务（先服务站在实时问题）", "帮我找一家最近的小鹏汽车服务中心。另外，顺便查一下小鹏汽车现在的交付周期是多久？"),
        # ("多跳任务（先服务站在技术问题）","请给我导航去附近的特斯拉官方服务中心。在路上我想了解一下，动力电池健康度掉到 80% 以下必须更换吗？"),
        # ("多跳任务（先POI在实时问题）", "我想去欢乐谷玩，请生成导航链接。顺便查一下今天欢乐谷闭园时间是几点？"),
        # ("多跳任务（先POI在技术问题）", "导航去中关村。另外我想问问，家用充电桩安装大概需要多大功率的电源？")
    ]

    # 循环执行测试
    for name, inp in test_cases:
        await run_single_test(name, inp)

    print("\n所有测试完成！\n")



if __name__ == "__main__":
    asyncio.run(main())
