# Mining Core Module Docker Configuration
# 挖矿核心模块Docker配置

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY mining_core_module/ /app/mining_core_module/
COPY config.env.template /app/
COPY start_mining_core.sh /app/

# 设置执行权限
RUN chmod +x /app/start_mining_core.sh

# 创建必要的目录
RUN mkdir -p /app/logs /app/uploads /app/reports

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# 暴露端口
EXPOSE 5001

# 默认命令
CMD ["python", "mining_core_module/main.py"]