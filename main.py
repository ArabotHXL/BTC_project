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

# 启动后台数据收集调度器
try:
    from services.data_collection_scheduler import start_background_collection
    start_background_collection()
    logging.info("网络数据收集调度器已启动")
except Exception as e:
    logging.error(f"启动数据收集调度器失败: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)