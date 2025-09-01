
#!/usr/bin/env python3
"""
应用拆分打包脚本
将Bitcoin Mining Calculator应用拆分为两个独立的包
"""

import os
import shutil
import tarfile
import json
from datetime import datetime

def create_package_1_core():
    """创建核心挖矿计算器包"""
    package_name = "btc_mining_calculator_core"
    
    # 创建临时目录
    if os.path.exists(package_name):
        shutil.rmtree(package_name)
    os.makedirs(package_name)
    
    # 核心文件列表
    core_files = [
        "main.py",
        "app.py", 
        "config.py",
        "models.py",
        "auth.py",
        "db.py",
        "mining_calculator.py",
        "decorators.py",
        "translations.py",
        "rate_limiting.py",
        "database_health.py",
        "startup_optimizer.py",
        "cache_manager.py",
        "language_engine.py",
        "user_portfolio_management.py",
        "models_subscription.py",
        "gmail_oauth_service.py",
        "gunicorn.conf.py",
        "startup.sh"
    ]
    
    # 复制核心文件
    for file in core_files:
        if os.path.exists(file):
            shutil.copy2(file, package_name)
    
    # 复制核心模板
    core_templates = [
        "templates/base.html",
        "templates/index.html", 
        "templates/login.html",
        "templates/register.html",
        "templates/dashboard_home.html",
        "templates/landing.html",
        "templates/homepage.html",
        "templates/unauthorized.html",
        "templates/legal.html",
        "templates/error.html",
        "templates/pricing.html",
        "templates/subscription.html",
        "templates/rate_limit_exceeded.html",
        "templates/upgrade_required.html"
    ]
    
    os.makedirs(f"{package_name}/templates", exist_ok=True)
    for template in core_templates:
        if os.path.exists(template):
            shutil.copy2(template, f"{package_name}/templates/")
    
    # 复制核心静态文件
    core_static = [
        "static/js/calculator_clean.js",
        "static/js/main.js",
        "static/js/simple-chart.js",
        "static/css/styles.css",
        "static/css/responsive.css"
    ]
    
    os.makedirs(f"{package_name}/static/js", exist_ok=True)
    os.makedirs(f"{package_name}/static/css", exist_ok=True)
    
    for static_file in core_static:
        if os.path.exists(static_file):
            dest_dir = f"{package_name}/static/{'js' if static_file.endswith('.js') else 'css'}"
            shutil.copy2(static_file, dest_dir)
    
    # 创建简化的requirements.txt
    core_requirements = """Flask==2.3.3
SQLAlchemy==2.0.21
psycopg2-binary==2.9.7
requests==2.31.0
numpy==1.24.3
python-dotenv==1.0.0
gunicorn==21.2.0
Werkzeug==2.3.7
pytz==2023.3
"""
    
    with open(f"{package_name}/requirements.txt", "w") as f:
        f.write(core_requirements)
    
    # 创建简化的README
    readme_content = """# Bitcoin Mining Calculator - Core Package

## 核心挖矿计算器功能

这是Bitcoin Mining Calculator的核心包，包含以下功能：
- 挖矿收益计算器
- 用户认证系统  
- 基础数据管理
- 多语言支持
- 订阅管理

## 安装和运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置环境变量：
```bash
export DATABASE_URL="your_database_url"
export SESSION_SECRET="your_secret_key"
```

3. 运行应用：
```bash
python main.py
```

或使用Gunicorn：
```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## 功能特点

- ⛏️ 挖矿收益计算器
- 👥 用户认证和管理
- 💰 订阅计划管理
- 🌐 中英文双语支持
- 📊 基础数据分析
"""
    
    with open(f"{package_name}/README.md", "w", encoding='utf-8') as f:
        f.write(readme_content)
    
    # 创建包信息文件
    package_info = {
        "name": "Bitcoin Mining Calculator Core",
        "version": "1.0.0",
        "description": "Core mining calculator functionality",
        "created": datetime.now().isoformat(),
        "files_count": len(os.listdir(package_name)),
        "features": [
            "Mining Profitability Calculator",
            "User Authentication",
            "Subscription Management", 
            "Multi-language Support",
            "Basic Analytics"
        ]
    }
    
    with open(f"{package_name}/package_info.json", "w") as f:
        json.dump(package_info, f, indent=2)
    
    return package_name

def create_package_2_advanced():
    """创建高级分析平台包"""
    package_name = "btc_mining_analytics_advanced"
    
    # 创建临时目录
    if os.path.exists(package_name):
        shutil.rmtree(package_name)
    os.makedirs(package_name)
    
    # 高级功能文件
    advanced_files = [
        "analytics_engine.py",
        "advanced_algorithm_engine.py", 
        "crm_routes.py",
        "mining_broker_routes.py",
        "batch_calculator_routes.py",
        "billing_routes.py",
        "miner_management_routes.py",
        "deribit_web_routes.py",
        "hosting_analytics.py",
        "models_hosting.py",
        "bitcoin_rpc_client.py",
        "coinwarz_api.py",
        "historical_data_engine.py",
        "next_sell_indicator.py",
        "performance_monitor.py",
        "professional_report_generator.py",
        "multi_exchange_collector.py",
        "deribit_options_poc.py"
    ]
    
    # 复制高级功能文件
    for file in advanced_files:
        if os.path.exists(file):
            shutil.copy2(file, package_name)
    
    # 复制高级模板
    advanced_templates = [
        "templates/analytics_dashboard.html",
        "templates/analytics_dashboard_new.html", 
        "templates/analytics_main.html",
        "templates/crm/",
        "templates/broker/",
        "templates/hosting/",
        "templates/batch_calculator.html",
        "templates/curtailment_calculator.html",
        "templates/network_history.html",
        "templates/algorithm_test.html",
        "templates/performance_monitor.html",
        "templates/deribit_analysis.html",
        "templates/portfolio_settings.html",
        "templates/user_access.html",
        "templates/login_dashboard.html",
        "templates/modules_dashboard.html",
        "templates/system_relationship_diagram.html"
    ]
    
    os.makedirs(f"{package_name}/templates", exist_ok=True)
    for template in advanced_templates:
        if os.path.exists(template):
            if os.path.isdir(template):
                shutil.copytree(template, f"{package_name}/{template}")
            else:
                shutil.copy2(template, f"{package_name}/templates/")
    
    # 复制高级静态文件
    advanced_static = [
        "static/js/enhanced_heatmap.js",
        "static/js/chart.js",
        "static/js/cache-optimization.js",
        "static/css/animations.css",
        "static/css/mining-calculator-enhanced.css",
        "static/css/performance.css"
    ]
    
    os.makedirs(f"{package_name}/static/js", exist_ok=True)
    os.makedirs(f"{package_name}/static/css", exist_ok=True)
    
    for static_file in advanced_static:
        if os.path.exists(static_file):
            dest_dir = f"{package_name}/static/{'js' if static_file.endswith('.js') else 'css'}"
            shutil.copy2(static_file, dest_dir)
    
    # 复制完整的模块目录
    if os.path.exists("modules"):
        shutil.copytree("modules", f"{package_name}/modules")
    
    # 复制analytics_dashboard_files
    if os.path.exists("analytics_dashboard_files"):
        shutil.copytree("analytics_dashboard_files", f"{package_name}/analytics_dashboard_files")
    
    # 复制deribit_analysis_package
    if os.path.exists("deribit_analysis_package"):
        shutil.copytree("deribit_analysis_package", f"{package_name}/deribit_analysis_package")
    
    # 创建高级功能requirements.txt
    advanced_requirements = """Flask==2.3.3
SQLAlchemy==2.0.21
psycopg2-binary==2.9.7
requests==2.31.0
numpy==1.24.3
pandas==1.5.3
matplotlib==3.7.2
plotly==5.15.0
python-dotenv==1.0.0
gunicorn==21.2.0
Werkzeug==2.3.7
pytz==2023.3
websocket-client==1.6.1
stripe==6.7.0
openpyxl==3.1.2
reportlab==4.0.4
celery==5.3.1
redis==4.6.0
beautifulsoup4==4.12.2
lxml==4.9.3
"""
    
    with open(f"{package_name}/requirements.txt", "w") as f:
        f.write(advanced_requirements)
    
    # 创建高级功能README
    readme_content = """# Bitcoin Mining Calculator - Advanced Analytics Platform

## 高级分析平台功能

这是Bitcoin Mining Calculator的高级分析包，包含以下功能：
- HashInsight Treasury Management Platform
- CRM客户关系管理系统
- 高级算法交易信号
- Deribit期权分析
- 托管业务管理
- 专业报告生成

## 安装和运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置环境变量：
```bash
export DATABASE_URL="your_database_url"
export SESSION_SECRET="your_secret_key"
export DERIBIT_API_KEY="your_deribit_key"
export STRIPE_SECRET_KEY="your_stripe_key"
```

3. 运行应用：
```bash
python main.py
```

## 功能特点

- 📊 HashInsight Treasury Management
- 🏢 CRM客户关系管理
- 🤖 高级算法交易信号
- 💼 期权交易分析
- 🏭 托管业务管理
- 📈 专业报告生成
- 🔄 多交易所数据集成
- 💰 佣金管理系统

## 依赖核心包

此高级包需要与核心包配合使用。请确保已安装核心包的所有依赖。
"""
    
    with open(f"{package_name}/README.md", "w", encoding='utf-8') as f:
        f.write(readme_content)
    
    # 创建包信息文件
    package_info = {
        "name": "Bitcoin Mining Calculator Advanced Analytics",
        "version": "1.0.0", 
        "description": "Advanced analytics and trading platform",
        "created": datetime.now().isoformat(),
        "files_count": len(os.listdir(package_name)),
        "features": [
            "Treasury Management Platform",
            "CRM System",
            "Advanced Trading Algorithms", 
            "Deribit Options Analysis",
            "Hosting Business Management",
            "Professional Report Generation",
            "Multi-Exchange Integration",
            "Commission Management"
        ]
    }
    
    with open(f"{package_name}/package_info.json", "w") as f:
        json.dump(package_info, f, indent=2)
    
    return package_name

def create_tar_packages():
    """创建tar.gz压缩包"""
    print("🔄 开始创建应用包...")
    
    # 创建核心包
    print("📦 创建核心挖矿计算器包...")
    core_package = create_package_1_core()
    
    # 创建高级包
    print("📊 创建高级分析平台包...")
    advanced_package = create_package_2_advanced()
    
    # 压缩核心包
    core_tar_name = f"{core_package}.tar.gz"
    with tarfile.open(core_tar_name, "w:gz") as tar:
        tar.add(core_package, arcname=core_package)
    
    # 压缩高级包
    advanced_tar_name = f"{advanced_package}.tar.gz" 
    with tarfile.open(advanced_tar_name, "w:gz") as tar:
        tar.add(advanced_package, arcname=advanced_package)
    
    # 检查文件大小
    core_size = os.path.getsize(core_tar_name) / (1024 * 1024)  # MB
    advanced_size = os.path.getsize(advanced_tar_name) / (1024 * 1024)  # MB
    
    print(f"\n✅ 包创建完成！")
    print(f"📦 核心包: {core_tar_name} ({core_size:.1f} MB)")
    print(f"📊 高级包: {advanced_tar_name} ({advanced_size:.1f} MB)")
    
    # 清理临时目录
    shutil.rmtree(core_package)
    shutil.rmtree(advanced_package)
    
    # 创建下载说明
    download_info = f"""# Bitcoin Mining Calculator - 分离包下载

## 包信息

1. **核心挖矿计算器** - `{core_tar_name}` ({core_size:.1f} MB)
   - 基础挖矿收益计算功能
   - 用户认证系统
   - 订阅管理
   - 多语言支持

2. **高级分析平台** - `{advanced_tar_name}` ({advanced_size:.1f} MB) 
   - HashInsight Treasury Management
   - CRM系统
   - 高级算法引擎
   - Deribit期权分析
   - 托管业务管理

## 使用说明

### 方案1：独立部署核心包
```bash
tar -xzf {core_tar_name}
cd {core_package}
pip install -r requirements.txt
python main.py
```

### 方案2：完整功能部署
```bash
# 解压两个包到同一目录
tar -xzf {core_tar_name}
tar -xzf {advanced_tar_name}

# 合并功能（可选）
cp -r {advanced_package}/* {core_package}/
cd {core_package}
pip install -r requirements.txt
python main.py
```

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open("PACKAGE_DOWNLOAD_INFO.md", "w", encoding='utf-8') as f:
        f.write(download_info)
    
    return core_tar_name, advanced_tar_name, core_size, advanced_size

if __name__ == "__main__":
    core_file, advanced_file, core_size, advanced_size = create_tar_packages()
    
    print(f"\n🎉 应用拆分完成！")
    print(f"📁 可下载文件：")
    print(f"   1. {core_file} ({core_size:.1f} MB)")
    print(f"   2. {advanced_file} ({advanced_size:.1f} MB)")
    print(f"📋 详细说明：PACKAGE_DOWNLOAD_INFO.md")
