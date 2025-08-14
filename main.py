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

    # Database health check before app initialization
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        from database_health import db_health_manager
        
        logging.info("Performing database health check...")
        db_status = db_health_manager.check_database_connection(database_url)
        
        if not db_status['connected']:
            error_msg = db_status.get('error', 'Unknown database error')
            suggestion = db_status.get('suggestion', 'Check database configuration')
            
            logging.error(f"Database connection failed: {error_msg}")
            logging.error(f"Suggested fix: {suggestion}")
            
            # For Neon-specific errors, provide detailed guidance
            if db_status.get('neon_specific'):
                logging.error("NEON DATABASE ENDPOINT DISABLED:")
                logging.error("1. Go to your Neon console (https://console.neon.tech/)")
                logging.error("2. Select your project and database")
                logging.error("3. Enable the endpoint in the database settings")
                logging.error("4. Update your DATABASE_URL environment variable if needed")
                
            # Wait for database with timeout
            logging.info("Waiting for database to become available...")
            if not db_health_manager.wait_for_database(database_url, timeout=60):
                logging.error("Database unavailable after timeout. Starting with limited functionality.")
            else:
                logging.info("Database connection established successfully")
        else:
            logging.info(f"Database connection successful: {db_status.get('database_version', 'Unknown version')}")

    from app import app
    # db已在app模块中初始化

    # 配置应用密钥
    app.secret_key = os.environ.get("SESSION_SECRET",
                                    "bitcoin_mining_calculator_secret")

    # 数据库已在app模块中初始化
    logging.info("Database initialized successfully")

    # 启动统一数据管道 - 在后台线程中进行（本地开发默认禁用）
    # 默认启用后台服务，除非明确禁用
    enable_bg = os.environ.get("ENABLE_BACKGROUND_SERVICES",
                               "1").lower() in ("1", "true", "yes")
    if enable_bg:

        def start_background_services():
            try:
                from analytics_engine import AnalyticsEngine
                engine = AnalyticsEngine()
                engine.start_scheduler()
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
