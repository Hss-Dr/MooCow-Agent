FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 配置APT镜像源（多源备份）
RUN cp /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list.d/debian.sources.bak 2>/dev/null || true && \
    # 尝试使用清华源
    (sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
     sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
     # 如果是旧格式sources.list
     (echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
      echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
      echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list)) && \
    echo "APT源配置完成"

# 安装系统依赖（带重试机制）
RUN apt-get update --fix-missing || apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    || (echo "清华源失败，尝试阿里云源..." && \
        sed -i 's|mirrors.tuna.tsinghua.edu.cn|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i 's|mirrors.tuna.tsinghua.edu.cn|mirrors.aliyun.com|g' /etc/apt/sources.list && \
        apt-get update && apt-get install -y --no-install-recommends gcc postgresql-client) && \
    rm -rf /var/lib/apt/lists/*

# 配置pip镜像源（多源）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.extra-index-url "https://mirrors.aliyun.com/pypi/simple/ https://pypi.douban.com/simple/" && \
    pip config set global.trusted-host "pypi.tuna.tsinghua.edu.cn mirrors.aliyun.com pypi.douban.com" && \
    echo "pip镜像源配置完成"

# 升级pip（使用国内源）
RUN pip install --upgrade pip setuptools wheel || \
    (echo "清华源失败，尝试阿里云源..." && \
     pip config set global.index-url https://mirrors.aliyun.com/pypi/simple && \
     pip install --upgrade pip setuptools wheel)

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（带超时和重试）
RUN pip install --no-cache-dir --timeout 100 -r requirements.txt || \
    (echo "安装失败，重试中..." && \
     pip install --no-cache-dir --timeout 100 -r requirements.txt) || \
    (echo "切换到豆瓣源..." && \
     pip config set global.index-url https://pypi.douban.com/simple && \
     pip install --no-cache-dir --timeout 100 -r requirements.txt)

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p logs storage/uploads user_memories scripts

# 复制并设置入口脚本权限
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 设置环境变量
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 使用入口脚本启动
CMD ["/app/entrypoint.sh"]
