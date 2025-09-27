"""
Web3集成模块启动入口
Entry point for Web3 Integration Module
"""

import os
import sys
import logging
try:
    from .app import create_app, stop_background_services
except ImportError:
    from app import create_app, stop_background_services

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('web3_integration.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        # 获取环境配置
        env = os.environ.get('FLASK_ENV', 'development')
        port = int(os.environ.get('PORT', 5002))
        host = os.environ.get('HOST', '0.0.0.0')
        debug = env == 'development'
        
        logger.info(f"启动Web3集成模块 - 环境: {env}, 端口: {port}")
        
        # 创建应用
        app = create_app(env)
        
        # 启动应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False  # 避免重复启动后台服务
        )
        
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭服务...")
        stop_background_services()
        sys.exit(0)
    except Exception as e:
        logger.error(f"启动失败: {e}")
        stop_background_services()
        sys.exit(1)

if __name__ == '__main__':
    main()