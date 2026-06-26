# 多阶段构建：优化镜像大小和安全性
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 生产阶段
FROM python:3.11-slim AS production

WORKDIR /app

# 创建非 root 用户运行应用
RUN groupadd -r jarvis && useradd -r -g jarvis jarvis

# 只安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制 Python 依赖
COPY --from=builder /root/.local /home/jarvis/.local
ENV PATH=/home/jarvis/.local/bin:$PATH

# 复制应用代码
COPY --chown=jarvis:jarvis . .

# 创建上传目录
RUN mkdir -p /app/uploads && chown -R jarvis:jarvis /app/uploads

# 切换到非 root 用户
USER jarvis

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令（使用 gunicorn + uvicorn worker 支持生产并发）
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
