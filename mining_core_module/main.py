"""
挖矿核心模块 - 启动入口
Mining Core Module - Entry Point

独立启动脚本，支持Gunicorn部署
"""
import os
import sys
import logging
from app import create_app

# 创建应用实例
app = create_app()

def run_development():
    """开发环境运行"""
    print("🚀 启动挖矿核心模块 (开发模式)")
    print(f"📍 服务地址: http://{app.config['HOST']}:{app.config['PORT']}")
    print("📊 功能模块:")
    print("   - 挖矿收益计算器")
    print("   - 批量计算处理")
    print("   - 技术指标分析")
    print("   - 历史数据管理")
    print("   - API数据集成")
    print("🔧 健康检查: /health")
    print("📚 API文档: /api/info")
    print("-" * 50)
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG'],
        threaded=True
    )

def run_production():
    """生产环境运行（通过Gunicorn）"""
    print("🏭 生产环境模式 - 请使用Gunicorn启动:")
    print(f"gunicorn --bind {app.config['HOST']}:{app.config['PORT']} --workers 4 main:app")
    return app

if __name__ == '__main__':
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'development':
        run_development()
    else:
        # 生产环境返回app实例供Gunicorn使用
        run_production()