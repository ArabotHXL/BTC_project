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

# 启动统一数据管道
try:
    from unified_data_pipeline import start_unified_pipeline
    start_unified_pipeline()
    logging.info("统一数据管道已启动")
except Exception as e:
    logging.error(f"启动统一数据管道失败: {e}")

# For gunicorn compatibility, the app is exposed as 'app'
# If running directly with python main.py, uncomment the lines below:
# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000, debug=True)