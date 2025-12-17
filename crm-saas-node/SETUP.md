# CRM Platform - 安装和启动指南

## 🚀 快速开始

### 1. 安装依赖

在 `crm-saas-node` 目录下运行：

```bash
cd crm-saas-node
npm install
```

这将安装所有工作区（backend, frontend, shared）的依赖。

### 2. 验证安装

检查 TypeScript 配置：
```bash
npm run type-check
```

运行代码检查：
```bash
npm run lint
```

### 3. 启动开发服务器

**方式一：同时启动前后端**
```bash
npm run dev
```

**方式二：分别启动**

启动后端（端口 3000）：
```bash
npm run dev:backend
```

启动前端（端口 5173）：
```bash
npm run dev:frontend
```

### 4. 访问应用

- **前端应用**: http://localhost:5173
- **后端API**: http://localhost:3000/api
- **健康检查**: http://localhost:3000/api/health

## 📁 项目结构说明

```
crm-saas-node/
├── backend/              # 后端服务
│   ├── src/
│   │   ├── routes/      # API路由
│   │   ├── services/    # 业务逻辑层
│   │   ├── middleware/  # Express中间件
│   │   └── server.ts    # 服务器入口
│   ├── package.json     # 后端依赖
│   └── tsconfig.json    # 后端TS配置
│
├── frontend/             # 前端应用
│   ├── src/
│   │   ├── components/  # React组件
│   │   ├── pages/       # 页面组件
│   │   ├── App.tsx      # 根组件
│   │   └── main.tsx     # 应用入口
│   ├── package.json     # 前端依赖
│   └── tsconfig.json    # 前端TS配置
│
├── shared/               # 共享代码
│   ├── types/
│   │   └── index.ts     # 共享类型定义
│   └── package.json     # 共享模块配置
│
├── package.json          # 根配置（workspaces）
├── tsconfig.json         # 基础TS配置
├── .eslintrc.json        # ESLint配置
├── .prettierrc.json      # Prettier配置
└── .gitignore            # Git忽略文件
```

## 🔧 配置说明

### TypeScript 配置
- **严格模式**: 已启用
- **目标版本**: ES2022
- **模块系统**: CommonJS (backend), ESNext (frontend)

### 后端依赖
- ✅ Express 4.18+ (Web框架)
- ✅ Prisma 5.9+ (ORM)
- ✅ JWT (身份验证)
- ✅ CORS & Helmet (安全)
- ✅ Zod (数据验证)

### 前端依赖
- ✅ React 18 (UI框架)
- ✅ Vite 5 (构建工具)
- ✅ TailwindCSS 3 (样式)
- ✅ React Router 6 (路由)
- ✅ Axios (HTTP客户端)
- ✅ i18next (国际化)

## 📝 可用脚本

### 开发模式
- `npm run dev` - 同时启动前后端
- `npm run dev:backend` - 仅启动后端
- `npm run dev:frontend` - 仅启动前端

### 构建
- `npm run build` - 构建前后端
- `npm run build:backend` - 构建后端
- `npm run build:frontend` - 构建前端

### 代码质量
- `npm run lint` - ESLint检查
- `npm run format` - Prettier格式化
- `npm run type-check` - TypeScript类型检查

## 🔐 环境变量配置

创建 `.env` 文件：

```env
# 后端配置
PORT=3000
DATABASE_URL="postgresql://user:password@localhost:5432/crm"
JWT_SECRET="your-secret-key-here"
NODE_ENV=development

# 前端配置 (在 frontend/.env)
VITE_API_URL=http://localhost:3000/api
```

## 📚 下一步

1. ✅ 运行 `npm install` 安装依赖
2. ✅ 配置数据库连接（DATABASE_URL）
3. ✅ 运行 `npm run dev` 启动开发服务器
4. 开始开发你的CRM功能！

## 🐛 故障排除

### 依赖安装失败
```bash
# 清除缓存并重新安装
rm -rf node_modules package-lock.json
npm install
```

### TypeScript 错误
```bash
# 运行类型检查查看详细错误
npm run type-check
```

### 端口被占用
修改 `.env` 中的 PORT 或在启动命令中指定：
```bash
PORT=3001 npm run dev:backend
```
