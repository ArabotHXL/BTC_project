import os
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)

from app import app
from db import init_db

# 配置应用密钥
app.secret_key = os.environ.get("SESSION_SECRET", "bitcoin_mining_calculator_secret")

# 初始化数据库
init_db(app)

# 导入电力管理系统API和路由
logging.info("正在加载电力管理系统模块...")
import db_power_management_app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)