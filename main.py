import os
import logging
import sys

# 配置日志
logging.basicConfig(level=logging.INFO)  # 降低日志级别提升启动速度


# 优化启动性能 - 延迟导入重型依赖
def create_app():
    """Factory function to create and configure the Flask app"""
    # 验证关键环境变量
    required_env_vars = ["DATABASE_URL", "SESSION_SECRET"]
    missing_vars = [
        var for var in required_env_vars if not os.environ.get(var)
    ]

    if missing_vars:
        logging.warning(f"Missing environment variables: {missing_vars}")
        # 设置默认值以避免应用崩溃
        if not os.environ.get("SESSION_SECRET"):
            os.environ["SESSION_SECRET"] = "bitcoin_mining_calculator_secret"

    from app import app
    from db import init_db

    # 配置应用密钥
    app.secret_key = os.environ.get("SESSION_SECRET",
                                    "bitcoin_mining_calculator_secret")

    # 初始化数据库
    try:
        init_db(app)
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        # 不要因为数据库问题让应用崩溃
        pass

    # 启动统一数据管道 - 在后台线程中进行（本地开发默认禁用）
    enable_bg = os.environ.get("ENABLE_BACKGROUND_SERVICES",
                               "0").lower() in ("1", "true", "yes")
    if enable_bg:

        def start_background_services():
            try:
                from unified_data_pipeline import start_unified_pipeline
                start_unified_pipeline()
                logging.info("Background services started successfully")
            except Exception as e:
                logging.error(f"Background services failed to start: {e}")

        # 在单独线程中启动后台服务，避免阻塞应用启动
        import threading
        background_thread = threading.Thread(target=start_background_services,
                                             daemon=True)
        background_thread.start()
    else:
        logging.info(
            "Background services are disabled. Set ENABLE_BACKGROUND_SERVICES=1 to enable."
        )

    return app


# 创建应用实例
app = create_app()

# 确保在直接运行时可以启动
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
