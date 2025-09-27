# User Management Module Docker Configuration
# 用户管理模块Docker配置

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
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev \
    libjpeg-dev \
    libpng-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY user_management_module/ /app/user_management_module/
COPY database_config.env.template /app/
COPY start_user_management.sh /app/

# 设置执行权限
RUN chmod +x /app/start_user_management.sh

# 创建必要的目录
RUN mkdir -p /app/logs /app/uploads /app/exports /app/backups
RUN mkdir -p /app/user_management_module/static/uploads/avatars
RUN mkdir -p /app/user_management_module/static/uploads/documents

# 创建非root用户
RUN groupadd -r userapp && useradd -r -g userapp userapp
RUN chown -R userapp:userapp /app
USER userapp

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5003/health || exit 1

# 暴露端口
EXPOSE 5003

# 默认命令
CMD ["python", "user_management_module/main.py"]