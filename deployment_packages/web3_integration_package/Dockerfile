# Web3 Integration Module Docker Configuration
# Web3集成模块Docker配置

FROM node:18-alpine AS contracts-builder

# 安装智能合约编译环境
WORKDIR /contracts
RUN npm install -g @nomiclabs/hardhat-waffle hardhat @openzeppelin/contracts

# 复制合约文件并编译 (如果存在)
COPY web3_integration_module/contracts* ./
RUN if [ -f package.json ]; then npm install && npm run compile; fi

# Python应用构建阶段
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV WEB3_PROVIDER_URI=https://mainnet.infura.io/v3/

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY web3_integration_module/ /app/web3_integration_module/
COPY blockchain_config.env.template /app/
COPY start_web3_module.sh /app/

# 从contracts-builder阶段复制编译后的合约 (如果存在)
COPY --from=contracts-builder /contracts/artifacts /app/web3_integration_module/contracts/artifacts/

# 设置执行权限
RUN chmod +x /app/start_web3_module.sh

# 创建必要的目录
RUN mkdir -p /app/logs /app/uploads /app/contracts/artifacts

# 创建非root用户
RUN groupadd -r web3user && useradd -r -g web3user web3user
RUN chown -R web3user:web3user /app
USER web3user

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# 暴露端口
EXPOSE 5002

# 默认命令
CMD ["python", "web3_integration_module/main.py"]