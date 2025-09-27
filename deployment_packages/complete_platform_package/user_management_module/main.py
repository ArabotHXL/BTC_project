"""
User Management Module - Main Entry Point
用户管理模块主入口点 - 启动脚本
"""

from app import app  # noqa: F401

if __name__ == '__main__':
    # 启动开发服务器
    # 根据任务要求：监听端口5003
    app.run(host='0.0.0.0', port=5003, debug=True)