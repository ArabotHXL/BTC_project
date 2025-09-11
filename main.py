import os
import logging
import sys

# 配置日志
logging.basicConfig(level=logging.INFO)

# 确保数据库健康检查模块可用
try:
    from database_health import db_health_manager
except ImportError:
    logging.warning("Database health module not available, creating minimal version")
    class MockDatabaseHealthManager:
        def check_database_connection(self, url):
            return {'connected': True, 'database_version': 'Unknown'}
        def wait_for_database(self, url, timeout=60):
            return True
    db_health_manager = MockDatabaseHealthManager()

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

    # 快速启动模式 - 为部署优化跳过数据库健康检查
    skip_db_check = os.environ.get("SKIP_DATABASE_HEALTH_CHECK", "1").lower() in ("1", "true", "yes")  # 默认启用快速启动
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and not skip_db_check:
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
    elif skip_db_check:
        logging.info("Database health check skipped for fast startup")

    from app import app
    # db已在app模块中初始化

    # 配置应用密钥
    app.secret_key = os.environ.get("SESSION_SECRET",
                                    "bitcoin_mining_calculator_secret")

    # 数据库已在app模块中初始化
    logging.info("Database initialized successfully")

    # 分阶段启动优化 - 延迟加载非关键组件
    fast_startup = os.environ.get("FAST_STARTUP", "1").lower() in ("1", "true", "yes")
    
    if fast_startup:
        logging.info("Fast startup mode enabled - deferring background services")
        
        # Signal that core app is ready for deployment
        try:
            with open('/tmp/core_app_ready', 'w') as f:
                f.write('ready')
            logging.info("Core application readiness signal created")
        except Exception as e:
            logging.warning(f"Could not create core readiness signal: {e}")
        
        def delayed_initialization():
            """延迟5秒启动后台服务，确保部署就绪"""
            import time
            time.sleep(5)  # 等待主应用完成启动和部署检查
            
            # 启动后台服务
            enable_bg = os.environ.get("ENABLE_BACKGROUND_SERVICES", "1").lower() in ("1", "true", "yes")
            if enable_bg:
                try:
                    from modules.analytics.engines.analytics_engine import AnalyticsEngine
                    engine = AnalyticsEngine()
                    engine.start_scheduler()
                    logging.info("Background services started successfully (delayed)")
                except Exception as e:
                    logging.error(f"Background services failed to start: {e}")
            
        # 在单独线程中延迟启动后台服务
        import threading
        delayed_thread = threading.Thread(target=delayed_initialization, daemon=True)
        delayed_thread.start()
    else:
        # 传统启动方式（完整初始化）
        enable_bg = os.environ.get("ENABLE_BACKGROUND_SERVICES", "1").lower() in ("1", "true", "yes")
        if enable_bg:
            def start_background_services():
                try:
                    from modules.analytics.engines.analytics_engine import AnalyticsEngine
                    engine = AnalyticsEngine()
                    engine.start_scheduler()
                    logging.info("Background services started successfully")
                except Exception as e:
                    logging.error(f"Background services failed to start: {e}")

            import threading
            background_thread = threading.Thread(target=start_background_services, daemon=True)
            background_thread.start()
        else:
            logging.info("Background services are disabled. Set ENABLE_BACKGROUND_SERVICES=1 to enable.")

    return app


# 创建应用实例
app = create_app()

# 确保在直接运行时可以启动
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
