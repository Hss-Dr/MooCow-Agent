import os
import sys
import logging
# 这是一个高级的文件处理器，它能根据时间（比如每天午夜）自动切割日志文件，防止一个文件无限变大
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# ================= 配置区域(日志存在哪”以及“日志长什么样) =================

# 1. 定义日志保存路径
# 使用 pathlib 获取项目根目录
# 结果路径: backend/app/logs
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"

# 确保目录存在
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 2. 定义日志格式
# 格式：[时间] [级别] [文件名:行号] - 消息
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
# %(asctime)s:   打印时间 (例如 2026-1-07 10:00:00)
# %(levelname)-8s: 打印日志级别 (INFO, ERROR等)。-8s 表示左对齐，占8个字符宽度，为了排版整齐。
# %(name)s:      logger的名字 (这里是 "ITS_App")
# %(lineno)d:    打印这行日志是在哪一行代码触发的 (非常便于找 Bug)
# %(message)s:   你具体打印的内容

# ================= 彩色日志格式器 (仅用于控制台) =================
class ColoredFormatter(logging.Formatter):
    """
    继承自 logging.Formatter，目的是重写 format 方法
    让控制台输出带有颜色，方便调试
    下面这些奇怪的字符串是 "ANSI 转义码"，终端看到这些代码就会变色
    """
    grey = "\x1b[38;20m"        # 灰色
    green = "\x1b[32;20m"       # 绿色
    yellow = "\x1b[33;20m"      # 黄色
    red = "\x1b[31;20m"         # 红色
    bold_red = "\x1b[31;1m"     # 加粗红色
    reset = "\x1b[0m"           # 重置颜色（否则后面所有字都会变色）
    format_str = CONSOLE_FORMAT # 引用上面定义的控制台格式

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,       # 调试用灰色
        logging.INFO: green + format_str + reset,       # 正常用绿色
        logging.WARNING: yellow + format_str + reset,   # 警告用黄色
        logging.ERROR: red + format_str + reset,        # 错误用红色
        logging.CRITICAL: bold_red + format_str + reset
    }
    # 重写 format 方法
    def format(self, record):
        # 1. 根据当前日志的级别 (record.levelno)，去字典里查对应的颜色格式
        log_fmt = self.FORMATS.get(record.levelno)
        # 2. 创建一个临时的标准 Formatter
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        # 3. 调用父类方法进行最终格式化
        return formatter.format(record)


# ================= 初始化 Logger =================

def get_logger(name="ITS_App"):
    """
    获取配置好的 Logger 实例
    """
    logger = logging.getLogger(name)

    # 如果已经有 handler 说明初始化过了，直接返回，防止重复打印
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # 总开关设为最低，由 handler 决定具体过滤

    # --- 1. 控制台 Handler (带颜色) ---
    console_handler = logging.StreamHandler(sys.stdout)         # 输出到标准输出(屏幕)
    console_handler.setLevel(logging.INFO)  # 控制台只看 INFO 以上 # 使用刚才定义的彩色格式
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # --- 2. 通用日志 (每天轮转, 保留30天) ---
    # 记录所有 INFO 及以上的信息
    app_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "app.log",
        when="midnight",  # 每天午夜切割
        interval=1,       # 间隔：1天切一次
        backupCount=30,   # 保留最近30个文件
        encoding="utf-8"  # 编码：防止中文乱码
    )
    app_handler.setLevel(logging.INFO)      # 门槛：INFO 及以上写入文件
    app_handler.setFormatter(logging.Formatter(FILE_FORMAT))  # 使用详细的文件格式
    logger.addHandler(app_handler)

    # --- 3. 错误日志 (每天轮转, 保留60天) ---
    # 只记录 ERROR 及以上
    error_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "error.log",
        when="midnight",
        interval=1,
        backupCount=60, # 错误日志更重要，保留 60 天
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)       # 只有 ERROR 及以上才写进来
    error_handler.setFormatter(logging.Formatter(FILE_FORMAT))
    logger.addHandler(error_handler)

    # --- 4. Agent/Debug 详细日志 (用于追踪 LLM 思考过程) ---
    # 记录 DEBUG 及以上 (最全的日志)
    agent_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "agent_debug.log",
        when="midnight",
        interval=1,
        backupCount=7,  # debug日志通常巨大，只保留 7 天节省磁盘
        encoding="utf-8"
    )
    agent_handler.setLevel(logging.DEBUG)
    agent_handler.setFormatter(logging.Formatter(FILE_FORMAT))
    logger.addHandler(agent_handler)

    return logger

# 日志大小级别：DEBUG(10)<INFO(20)<WARNING(30)<ERROR(40)<CRITICAL(50)
# 创建全局单例，方便其他文件直接 import logger
logger = get_logger()