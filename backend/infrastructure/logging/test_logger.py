from logger import logger

def some_function():
    # 1. 这种只会出现在 agent_debug.log (用于开发时看变量、Prompt)
    logger.debug("正在向硅基流动发送请求，Prompt长度: 500...")

    # 2. 这种会出现在 控制台 + app.log + agent_debug.log
    # logger.info("用户 [admin] 登录成功")

    # 3. 这种会出现在 所有地方 (且控制台是红色的)
    # try:
    #     1 / 0
    # except Exception as e:
    #     logger.error(f"计算发生未知错误: {e}")

if __name__ == '__main__':
    some_function()
