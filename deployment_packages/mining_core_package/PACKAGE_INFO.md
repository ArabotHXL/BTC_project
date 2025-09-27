# Mining Core Module Package Information
# 挖矿核心模块包信息

## 包详情 Package Details

- **包名称**: Mining Core Module 挖矿核心模块
- **版本**: v2.1.0
- **构建日期**: 2025-09-27
- **包类型**: 独立部署包
- **平台支持**: Linux, macOS, Windows
- **Python版本**: 3.8+

## 包内容 Package Contents

```
mining_core_package/
├── mining_core_module/          # 完整源代码
│   ├── api/                     # API客户端
│   ├── modules/                 # 核心模块
│   ├── routes/                  # 路由处理
│   ├── static/                  # 静态资源
│   ├── templates/               # 模板文件
│   ├── utils/                   # 工具函数
│   ├── app.py                   # Flask应用
│   ├── config.py                # 配置文件
│   ├── main.py                  # 主入口
│   └── models.py                # 数据模型
├── start_mining_core.sh         # Linux/macOS启动脚本
├── start_mining_core.bat        # Windows启动脚本
├── config.env.template          # 环境配置模板
├── requirements.txt             # Python依赖
├── Dockerfile                   # Docker配置
├── docker-compose.yml           # Docker Compose配置
├── database_init.sql            # 数据库初始化脚本
├── README.md                    # 详细说明文档
├── mining_api_docs.md           # API文档
├── LICENSE                      # 许可证
├── CHANGELOG.md                 # 更新日志
├── VERSION                      # 版本号
└── PACKAGE_INFO.md              # 包信息
```

## 快速开始 Quick Start

1. **解压包文件**
   ```bash
   unzip mining_core_package.zip
   cd mining_core_package
   ```

2. **配置环境**
   ```bash
   cp config.env.template .env
   # 编辑 .env 文件配置数据库和API密钥
   ```

3. **启动应用**
   ```bash
   # Linux/macOS
   ./start_mining_core.sh
   
   # Windows
   start_mining_core.bat
   ```

4. **验证安装**
   访问 http://localhost:5001 或 http://localhost:5001/health

## 系统要求 System Requirements

### 最低要求
- Python 3.8+
- 2GB RAM
- 5GB 磁盘空间
- 稳定网络连接

### 推荐配置
- Python 3.11+
- 4GB+ RAM
- 20GB+ SSD
- PostgreSQL 15+

## 主要功能 Key Features

- ✅ 实时挖矿收益计算
- ✅ 批量矿机数据处理
- ✅ 多种分析算法支持
- ✅ 专业报告生成
- ✅ RESTful API接口
- ✅ Docker容器化部署
- ✅ 自动化启动脚本
- ✅ 完整配置模板

## 技术栈 Technology Stack

- **后端框架**: Flask 2.3.3
- **数据库**: PostgreSQL 15+ / SQLite
- **缓存**: Redis 7+
- **Web服务器**: Gunicorn
- **容器化**: Docker & Docker Compose
- **API**: RESTful JSON API

## 安全特性 Security Features

- 环境变量配置管理
- API访问控制
- 数据验证和清洗
- SQL注入防护
- 安全的密码存储

## 支持和文档 Support & Documentation

- 📖 完整文档: README.md
- 🔧 API文档: mining_api_docs.md
- 📝 更新日志: CHANGELOG.md
- 🏠 官方网站: https://hashinsight.net
- 📧 技术支持: support@hashinsight.net

## 许可证 License

MIT License - 详见 LICENSE 文件

## 校验和 Checksums

生成时间: 2025-09-27T12:00:00Z
包大小: ~50MB (压缩后)

---

**HashInsight Mining Intelligence Platform**  
Mining Core Module v2.1.0  
© 2025 HashInsight Technologies