# 快速启动Gunicorn配置
import os

# 基础设置
bind = "0.0.0.0:5000"
workers = 1  # 减少worker数量以加速启动
worker_class = "sync"
timeout = 30
keepalive = 5

# 性能优化
preload_app = True  # 预加载应用
worker_connections = 1000
max_requests = 0
max_requests_jitter = 0

# 快速启动优化
reload = False  # 禁用重载以提升启动速度
enable_stdio_inheritance = True

# 日志配置
loglevel = "info"
errorlog = "-"
accesslog = "-"

# 进程名称
proc_name = "mining_calculator_fast"

# 环境变量优化 - 激进优化模式
raw_env = [
    "FAST_STARTUP=1",
    "SKIP_DATABASE_HEALTH_CHECK=1", 
    "PYTHONOPTIMIZE=1",
    "ENABLE_BACKGROUND_SERVICES=0",
    "LOAD_CORE_MODULES=1",
    "LOAD_ADVANCED_MODULES=0",
    "PYTHONDONTWRITEBYTECODE=1",
    "FLASK_ENV=production"
]