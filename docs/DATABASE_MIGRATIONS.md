# 数据库迁移指南 (Database Migration Guide)

## 概述

HashInsight 使用 Alembic 进行数据库迁移管理。本指南介绍如何使用迁移系统。

## 快速开始

### 现有数据库

对于已有数据的数据库，执行以下命令标记为已迁移：

```bash
alembic stamp baseline_001
```

### 新数据库

对于全新的数据库：

```bash
# 1. 创建所有表
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 2. 标记为已迁移
alembic stamp baseline_001
```

## 常用命令

### 查看当前版本

```bash
alembic current
```

### 查看迁移历史

```bash
alembic history
```

### 创建新迁移

```bash
# 自动生成（推荐）
alembic revision --autogenerate -m "描述改动"

# 手动创建空迁移
alembic revision -m "描述改动"
```

### 执行迁移

```bash
# 升级到最新版本
alembic upgrade head

# 升级一个版本
alembic upgrade +1

# 降级一个版本
alembic downgrade -1
```

### 查看待执行的 SQL

```bash
alembic upgrade head --sql
```

## 迁移最佳实践

### 1. 始终在开发环境测试迁移

```bash
# 升级
alembic upgrade head

# 确认无误后回滚
alembic downgrade -1

# 再次升级确保可重复执行
alembic upgrade head
```

### 2. 避免破坏性操作

- 不要删除正在使用的列
- 添加新列时使用默认值或允许 NULL
- 重命名列时使用多步迁移

### 3. 大表迁移注意事项

对于大表（>100万行），考虑：
- 分批执行
- 在低峰期执行
- 添加索引前先创建列

## 文件结构

```
project/
├── alembic.ini          # Alembic 配置
├── alembic/
│   ├── env.py           # 环境配置
│   ├── script.py.mako   # 迁移模板
│   └── versions/        # 迁移脚本
│       └── baseline_001_*.py
```

## 故障排除

### 迁移冲突

如果遇到版本冲突：

```bash
# 查看分支
alembic branches

# 合并分支
alembic merge -m "merge heads" head1 head2
```

### 数据库状态不一致

```bash
# 强制标记当前版本
alembic stamp <revision>
```

## 生产环境注意事项

1. **备份数据库** - 迁移前始终备份
2. **测试迁移** - 在 staging 环境先测试
3. **监控执行时间** - 大表迁移可能需要较长时间
4. **准备回滚计划** - 确保可以快速回滚

## 环境变量

迁移依赖以下环境变量：

- `DATABASE_URL` - 数据库连接字符串（必需）

## 相关文档

- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
