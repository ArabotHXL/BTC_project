# CRM Platform - Enterprise SaaS Solution

## 项目简介

企业级CRM平台，采用现代化的技术栈构建，支持客户关系管理、销售跟踪、数据分析等核心功能。

## 技术栈

### 后端
- **Node.js + TypeScript** - 类型安全的JavaScript运行环境
- **Express** - 轻量级Web框架
- **Prisma** - 现代化的ORM工具
- **JWT** - 用户认证和授权
- **Zod** - 运行时数据验证

### 前端
- **React 18** - 用户界面库
- **TypeScript** - 类型安全
- **Vite** - 快速的构建工具
- **TailwindCSS** - 实用优先的CSS框架
- **React Router** - 客户端路由
- **Axios** - HTTP客户端
- **i18next** - 国际化支持

### 开发工具
- **ESLint** - 代码质量检查
- **Prettier** - 代码格式化
- **TypeScript** - 严格类型检查

## 项目结构

```
crm-saas-node/
├── backend/           # 后端API服务
│   ├── src/
│   │   ├── routes/    # 路由定义
│   │   ├── services/  # 业务逻辑
│   │   ├── middleware/# 中间件
│   │   └── server.ts  # 入口文件
│   ├── package.json
│   └── tsconfig.json
├── frontend/          # 前端应用
│   ├── src/
│   │   ├── components/# React组件
│   │   ├── pages/     # 页面组件
│   │   └── main.tsx   # 入口文件
│   ├── package.json
│   └── tsconfig.json
├── shared/            # 共享代码
│   ├── types/         # 共享类型定义
│   └── package.json
└── package.json       # 根配置（workspaces）
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

启动后端服务（端口3000）：
```bash
npm run dev:backend
```

启动前端应用（端口5173）：
```bash
npm run dev:frontend
```

同时启动前后端：
```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 代码检查和格式化

```bash
# ESLint检查
npm run lint

# Prettier格式化
npm run format

# TypeScript类型检查
npm run type-check
```

## 环境变量

在项目根目录创建 `.env` 文件：

```env
# 后端配置
PORT=3000
DATABASE_URL="postgresql://user:password@localhost:5432/crm"
JWT_SECRET="your-secret-key"

# 前端配置
VITE_API_URL=http://localhost:3000/api
```

## 开发规范

1. 使用TypeScript严格模式
2. 遵循ESLint规则
3. 使用Prettier统一代码风格
4. 提交前运行类型检查和代码检查
5. 使用语义化的Git提交信息

## API文档

后端API运行后，访问：
- Health Check: `http://localhost:3000/api/health`
- API Root: `http://localhost:3000/api`

## License

MIT
