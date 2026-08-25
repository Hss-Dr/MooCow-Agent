FROM python:3.11.7-slim

# 方案1：使用更稳定的镜像源（清华大学镜像源）
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 或者使用官方源作为备用（如果镜像源有问题，请取消注释下面几行）
# RUN echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list && \
#     echo "deb http://security.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list && \
#     echo "deb http://deb.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list

# 安装必要的构建工具和依赖，增加错误处理
RUN apt-get update --fix-missing || apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
    build-essential \
    python3-dev \
    make \
    libgl1 \
    libgl1-mesa-glx \
    libglu1-mesa \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 更新 pip 并配置镜像源
RUN pip config set global.extra-index-url "https://mirrors.cernet.edu.cn/pypi/web/simple"
RUN pip install --upgrade pip setuptools wheel

# 设置工作目录
WORKDIR /app

# 拷贝全量锁定依赖并安装（134 包逐字锁定,含 numpy==1.26.4 / opencv-python==4.10.0.84 / xgboost==1.3.3）
COPY app/requirements.lock.txt /app/
RUN pip install --no-cache-dir -r requirements.lock.txt

# 下载 deepdoc 分词/词形还原所需的 NLTK 语料，否则解析文档时会因缺少
# wordnet 等资源抛 LookupError，导致上传的文档无法写入 ES。
# NLTK 3.10+ 需要 punkt_tab(不是旧版 punkt) 和 averaged_perceptron_tagger_eng(不是 averaged_perceptron_tagger)
ENV NLTK_DATA=/root/nltk_data
RUN python3 -m nltk.downloader -d /root/nltk_data \
    wordnet omw-1.4 punkt_tab stopwords averaged_perceptron_tagger_eng

# 拷贝代码（从 app/ 子目录）
COPY app/ /app/

# 修改文件权限
RUN chmod -R 755 /app
RUN chmod +x /app/start.sh

# 设置启动脚本为入口点
ENTRYPOINT ["/app/start.sh"]
