# 数据库连接修复指南

## ⚠️ 当前问题

你的应用无法连接到数据库，显示错误：
```
ERROR: The endpoint has been disabled. Enable it using Neon API and retry.
```

这是因为之前的Neon数据库endpoint已被禁用。

## 🔧 解决方案

### 方法1：在Replit中重新创建数据库（推荐）

1. **打开Database工具**
   - 在Replit workspace左侧工具栏，点击 **Database** 图标
   - 如果看到旧的数据库，点击"Delete"删除它

2. **创建新数据库**
   - 点击"Create database"按钮
   - 选择PostgreSQL
   - Replit会自动创建并配置新的PostgreSQL数据库

3. **等待几秒钟**
   - Replit会自动设置以下环境变量（作为Secrets）：
     - `DATABASE_URL`
     - `PGHOST`
     - `PGUSER`
     - `PGPASSWORD`
     - `PGDATABASE`
     - `PGPORT`

4. **重启应用**
   - 应用会自动重启并使用新的数据库连接

### 方法2：手动更新数据库凭据

如果你有外部PostgreSQL数据库，可以手动更新：

1. **打开Secrets标签**
   - 在Replit左侧工具栏，点击锁图标（Secrets）

2. **更新DATABASE_URL**
   - 找到 `DATABASE_URL` 密钥
   - 点击"Edit"
   - 输入你的新数据库连接字符串：
     ```
     postgresql://username:password@host:port/database
     ```
   - 点击"Save"

3. **重启应用**
   - 应用会自动检测到新的凭据

## ✅ 验证修复

修复后，你应该能够：

1. ✅ 访问 `/login` 页面（不再显示Internal Server Error）
2. ✅ 创建新用户账户
3. ✅ 登录系统
4. ✅ 使用CRM和其他数据库功能

## 🚀 临时解决方案（已实施）

在数据库修复之前，我已经添加了错误处理：

- `/login` 页面现在会显示友好的错误消息，而不是500错误
- 首页和计算器功能仍然可用（它们不依赖数据库）

## 📝 可用功能（无需数据库）

以下功能在数据库不可用时仍然工作：

- **首页**：`/` - 显示系统概览
- **挖矿计算器**：`/calculator` - 实时BTC挖矿盈利计算
- **TypeScript API服务**：端口3000（如果已启动）
  - DataHub: `http://localhost:3000/api/datahub/all`
  - 矿机监控: `http://localhost:3000/api/miners`

## 🔍 需要数据库的功能

以下功能需要数据库连接才能使用：

- ❌ 用户登录/注册
- ❌ CRM系统（客户/销售/资产管理）
- ❌ 托管服务管理
- ❌ 数据分析和报告
- ❌ Web3功能（区块链透明度）
- ❌ 财务管理

## 💡 常见问题

### Q: 我的数据会丢失吗？
A: 如果你删除旧数据库并创建新的，**是的，旧数据会丢失**。如果你有重要数据，请先导出备份。

### Q: 我可以使用外部数据库吗？
A: 可以！你可以使用任何PostgreSQL兼容的数据库（例如：Supabase、ElephantSQL、Amazon RDS等）。只需在Secrets中设置正确的`DATABASE_URL`即可。

### Q: 为什么Neon endpoint被禁用了？
A: Neon的免费计划可能会在一段时间不活跃后自动暂停endpoint。你可以在Neon控制台重新启用，或者在Replit中创建新的数据库。

## 📞 需要帮助？

如果以上步骤无法解决问题，请：

1. 检查Replit控制台日志（查看详细错误信息）
2. 确认Secrets中的`DATABASE_URL`格式正确
3. 尝试删除所有数据库相关的Secrets，让Replit重新创建

---

**最后更新**: 2025-11-01
