from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from config.settings import settings

# 硅基流动配置(主模型)
SF_API_KEY = settings.SF_API_KEY
SF_BASE_URL = settings.SF_BASE_URL
MAIN_MODEL_NAME = settings.MAIN_MODEL_NAME
FAST_MODEL_NAME = settings.FAST_MODEL_NAME

# 阿里百炼配置(子模型)
AL_BAILIAN_API_KEY = settings.AL_BAILIAN_API_KEY
AL_BAILIAN_BASE_URL = settings.AL_BAILIAN_BASE_URL
SUB_MODEL_NAME = settings.SUB_MODEL_NAME

# 创建模型客户端
# 主模型客户端(协调Agent使用)
main_model_client = AsyncOpenAI(
    base_url=SF_BASE_URL, # 硅基流动base url
    api_key=SF_API_KEY  # 硅基流动api key
)
# 子模型客户端(干活的子Agent使用)
sub_model_client = AsyncOpenAI(
    base_url=AL_BAILIAN_BASE_URL, # 阿里百炼base url
    api_key=AL_BAILIAN_API_KEY # 阿里百炼api key
)




# 创建主调度模型（深度思考：推理模型，产生 THINKING 流）
main_model = OpenAIChatCompletionsModel(
    model=MAIN_MODEL_NAME,
    openai_client=main_model_client)

# 创建快速模式模型（关闭深度思考时使用：无推理过程，直接作答）
main_fast_model = OpenAIChatCompletionsModel(
    model=FAST_MODEL_NAME,
    openai_client=main_model_client)

# 创建子调度模型
sub_model = OpenAIChatCompletionsModel(
    model=SUB_MODEL_NAME,
    openai_client=sub_model_client)
