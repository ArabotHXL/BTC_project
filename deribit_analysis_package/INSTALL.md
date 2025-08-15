# 安装和部署指南

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 集成到您的Flask应用

在您的主Flask应用文件中添加：

```python
from flask import Flask
from deribit_web_routes import deribit_bp

app = Flask(__name__)

# 注册Deribit分析蓝图
app.register_blueprint(deribit_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### 3. 模板文件放置
将 `deribit_analysis.html` 放置到您的 Flask 应用的 `templates/` 目录中。

### 4. 启动应用
```bash
python app.py
```

### 5. 访问分析页面
打开浏览器访问: `http://localhost:5000/deribit-analysis`

## 功能测试

### API端点测试
```bash
# 检查API状态
curl http://localhost:5000/api/deribit/status

# 获取分析数据
curl http://localhost:5000/api/deribit/analysis-data

# 手动触发分析
curl -X POST http://localhost:5000/api/deribit/manual-analysis \
  -H "Content-Type: application/json" \
  -d '{"instrument": "BTC-PERPETUAL"}'
```

### 预期结果
- ✅ 显示 BTC 价格在 $118,000+ 水平
- ✅ 交易方向分布图显示买入/卖出比例
- ✅ 价格区间分布图显示10个价格段
- ✅ API状态显示 Deribit/OKX/Binance 连接状态

## 文件结构说明

```
your_flask_app/
├── app.py                     # 您的主Flask应用
├── templates/
│   └── deribit_analysis.html  # 放置这里
├── deribit_web_routes.py      # 复制这个文件
├── deribit_options_poc.py     # 复制这个文件
├── multi_exchange_collector.py # 复制这个文件
├── deribit_trades.db          # 数据库文件(可选)
└── multi_exchange_trades.db   # 数据库文件(可选)
```

## 故障排除

### 常见问题

1. **导入错误**
   - 确保所有 `.py` 文件都在Python路径中
   - 检查依赖包是否正确安装

2. **数据库错误**
   - 数据库文件会自动创建
   - 确保应用有写入权限

3. **API连接问题**
   - 检查网络连接
   - 某些API可能有地区限制

### 调试模式
启用Flask调试模式查看详细错误信息：
```python
app.run(debug=True)
```