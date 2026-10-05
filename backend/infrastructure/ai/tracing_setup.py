"""
Phoenix 追踪初始化（OpenTelemetry + OpenInference）

openai-agents SDK 提供 TracingProcessor 扩展点，OpenInference 官方实现了
OpenAIAgentsInstrumentor，把 Agent / LLM / Tool 三层 span 按 OTel 标准导出到
Phoenix（自托管，compose 中的 phoenix 服务）。

用法：应用启动时调用 setup_phoenix_tracing()，关闭时调用 shutdown_phoenix_tracing()。
"""
import os

from infrastructure.logging.logger import logger

_tracer_provider = None


def setup_phoenix_tracing():
    """注册 OpenInference 插桩，将 Agent trace 导出到 Phoenix。

    - 未配置 PHOENIX_OTLP_ENDPOINT 时跳过（本地裸跑后端时不追踪）
    - instrument() 默认独占式替换 SDK 自带 processor：SDK 默认 processor 会把
      trace 上传到 OpenAI 官方后台（本项目走 SiliconFlow 且网络不可达，无意义）
    - 初始化失败不阻断主流程，仅告警
    """
    global _tracer_provider

    endpoint = os.getenv("PHOENIX_OTLP_ENDPOINT", "")
    if not endpoint:
        logger.info("[Tracing] 未配置 PHOENIX_OTLP_ENDPOINT，跳过 Agent 追踪")
        return

    try:
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        project_name = os.getenv("PHOENIX_PROJECT_NAME", "moocow-agent")
        resource = Resource.create({
            "service.name": "moocow-backend",
            # Phoenix 按此属性把 trace 归入项目
            "openinference.project.name": project_name,
        })

        provider = trace_sdk.TracerProvider(resource=resource)
        # Batch 异步批量上报，避免每条 span 阻塞请求链路
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        OpenAIAgentsInstrumentor().instrument(tracer_provider=provider)

        _tracer_provider = provider
        logger.info(f"[Tracing] Phoenix 追踪已启用: {endpoint} (project={project_name})")
    except ImportError as e:
        logger.warning(f"[Tracing] 追踪依赖未安装，跳过 Agent 追踪: {e}")
    except Exception as e:
        logger.warning(f"[Tracing] Phoenix 追踪初始化失败（不影响主流程）: {e}")


def shutdown_phoenix_tracing():
    """应用关闭时冲刷未上报的 span。"""
    global _tracer_provider
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception:
            pass
        _tracer_provider = None
