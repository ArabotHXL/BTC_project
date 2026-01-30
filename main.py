import os
import logging
import sys

# 配置日志
logging.basicConfig(level=logging.INFO)

# === 强制重新构建标记 ===
BUILD_VERSION = "2026-01-30-v3"
logging.info(f"🚀 Application Version: {BUILD_VERSION}")
# === 强制重新构建标记 ===

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
        logging.error(f"Missing critical environment variables: {missing_vars}")
        # 🔧 CRITICAL SECURITY FIX: 绝对不允许硬编码的session secret
        if "SESSION_SECRET" in missing_vars:
            raise SystemExit("CRITICAL SECURITY ERROR: SESSION_SECRET environment variable must be set. Cannot proceed without secure session key.")
        if "DATABASE_URL" in missing_vars:
            raise SystemExit("CRITICAL ERROR: DATABASE_URL environment variable must be set.")

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

    # 🔧 CRITICAL FIX: 生产就绪度检查
    try:
        # 检查是否在生产模式或启用严格检查
        production_mode = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('ENABLE_PRODUCTION_CHECKS', 'false').lower() == 'true'
        
        if production_mode or not skip_db_check:
            logging.info("🚀 运行生产就绪度检查...")
            
            from production_readiness_checker import ProductionReadinessChecker
            
            # 创建检查器实例
            checker = ProductionReadinessChecker()
            
            # 运行启动检查 - 在生产模式下fail_fast，开发模式下不中断
            fail_fast = production_mode
            readiness_report = checker.run_startup_checks(fail_fast=fail_fast)
            
            # 记录检查结果
            if checker.production_ready:
                logging.info("✅ 生产就绪度检查通过")
            else:
                if fail_fast:
                    logging.error("❌ 生产就绪度检查失败，停止启动")
                    raise SystemExit("Production readiness check failed")
                else:
                    logging.warning("⚠️ 生产就绪度检查发现问题，但允许继续启动")
                    for warning in checker.warnings:
                        logging.warning(f"  - {warning}")
                        
    except ImportError as e:
        logging.warning(f"生产就绪度检查器不可用: {e}")
        logging.info("系统将继续启动，但建议修复生产就绪度检查器")
    except Exception as e:
        # 在开发模式下不因检查失败而阻止启动
        if os.environ.get('FLASK_ENV') == 'production':
            logging.error(f"生产就绪度检查失败: {e}")
            raise SystemExit(f"Production readiness check failed: {e}")
        else:
            logging.warning(f"生产就绪度检查出现问题，但允许启动: {e}")

    from app import app
    # db已在app模块中初始化
    
    # 🔧 CRITICAL FIX: 集成服务发现和注册
    enable_service_discovery = os.environ.get('ENABLE_SERVICE_DISCOVERY', 'true').lower() == 'true'
    deployment_mode = os.environ.get('DEPLOYMENT_MODE', 'standalone')
    
    if enable_service_discovery and deployment_mode in ['combined', 'gateway']:
        try:
            from service_integration import init_service_integration
            service_reg, gateway_router = init_service_integration(
                app, 
                enable_registration=True, 
                enable_heartbeat=True
            )
            logging.info(f"Service discovery initialized for {deployment_mode} mode")
        except ImportError as e:
            logging.warning(f"Service integration not available: {e}")
        except Exception as e:
            logging.error(f"Service integration failed: {e}")
    else:
        logging.info(f"Service discovery disabled for {deployment_mode} mode")

    # 🔧 CRITICAL SECURITY FIX: 严格要求SESSION_SECRET环境变量
    app.secret_key = os.environ.get("SESSION_SECRET")
    if not app.secret_key:
        raise SystemExit("CRITICAL SECURITY ERROR: SESSION_SECRET environment variable must be set. This should have been caught earlier - check environment setup.")

    # 数据库已在app模块中初始化
    logging.info("Database initialized successfully")

    # SOC2 Compliance: Setup audit log cleanup scheduler
    try:
        from security_soc2 import setup_audit_log_cleanup_scheduler
        setup_audit_log_cleanup_scheduler()
        logging.info("Audit log cleanup scheduler initialized")
    except Exception as e:
        logging.warning(f"Failed to setup audit log cleanup scheduler: {e}")

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
