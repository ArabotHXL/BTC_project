# 🎨 Miner Agent 管理界面设计

## 📋 文档信息

- **版本**: 1.0.0
- **日期**: 2025-10-13  
- **路由**: `/agent/` (管理员专用)
- **权限**: Owner, Admin 角色

---

## 🎯 设计目标

创建统一的 Agent 管理界面，提供：
- ✅ Agent 注册和配置
- ✅ 实时状态监控  
- ✅ 控制指令下发
- ✅ 事件告警查看
- ✅ 性能分析仪表盘

---

## 📱 页面结构

###  **1. Agent 列表页** (`/agent/`)

#### 布局设计

```
┌─────────────────────────────────────────────────────────────┐
│ HashInsight Enterprise - Agent Management                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [➕ Create Agent]  [🔄 Refresh]  [⚙️ Settings]             │
│                                                              │
│  📊 Overall Stats                                            │
│  ┌────────┬────────┬────────┬────────┐                     │
│  │ Total  │ Active │Offline │ Miners │                     │
│  │   10   │   8    │   2    │  485   │                     │
│  └────────┴────────┴────────┴────────┘                     │
│                                                              │
│  🔍 Search: [____________]  Filter: [All Sites ▼]          │
│                                                              │
│  Agent List                                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🟢 Site A Agent                                       │  │
│  │    ID: a1b2c3d4... | Site: Beijing DC                │  │
│  │    ⚡ 50 miners (48 online) | 📡 30s ago              │  │
│  │    [📊 View] [⚙️ Config] [📜 Logs]                    │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ 🟢 Site B Agent                                       │  │
│  │    ID: b2c3d4e5... | Site: Shenzhen DC               │  │
│  │    ⚡ 100 miners (98 online) | 📡 35s ago             │  │
│  │    [📊 View] [⚙️ Config] [📜 Logs]                    │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ 🔴 Site C Agent (Offline)                            │  │
│  │    ID: c3d4e5f6... | Site: Shanghai DC               │  │
│  │    ⚡ 75 miners | 📡 5 min ago                        │  │
│  │    [📊 View] [⚙️ Config] [🔄 Reconnect]              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Pagination: [◄] 1 2 3 ... 10 [►]                          │
└─────────────────────────────────────────────────────────────┘
```

#### 功能模块

**1. 统计卡片**
```html
<div class="stats-row">
  <div class="stat-card">
    <div class="stat-value countup">10</div>
    <div class="stat-label">Total Agents</div>
  </div>
  <div class="stat-card active">
    <div class="stat-value countup">8</div>
    <div class="stat-label">Active</div>
  </div>
  <div class="stat-card offline">
    <div class="stat-value countup">2</div>
    <div class="stat-label">Offline</div>
  </div>
  <div class="stat-card">
    <div class="stat-value countup">485</div>
    <div class="stat-label">Total Miners</div>
  </div>
</div>
```

**2. Agent 卡片**
```html
<div class="agent-card" data-status="active">
  <div class="agent-header">
    <span class="status-indicator online"></span>
    <h4>Site A Agent</h4>
    <span class="agent-badge">v1.0.0</span>
  </div>
  
  <div class="agent-info">
    <div class="info-item">
      <i class="bi bi-fingerprint"></i>
      <span>a1b2c3d4-e5f6-7890</span>
    </div>
    <div class="info-item">
      <i class="bi bi-building"></i>
      <span>Beijing Data Center</span>
    </div>
  </div>
  
  <div class="agent-stats">
    <div class="mini-stat">
      <i class="bi bi-cpu"></i>
      <span>50 miners</span>
    </div>
    <div class="mini-stat">
      <i class="bi bi-check-circle"></i>
      <span>48 online</span>
    </div>
    <div class="mini-stat">
      <i class="bi bi-clock"></i>
      <span>30s ago</span>
    </div>
  </div>
  
  <div class="agent-actions">
    <button class="btn-primary">📊 View Details</button>
    <button class="btn-secondary">⚙️ Configure</button>
    <button class="btn-secondary">📜 View Logs</button>
  </div>
</div>
```

---

### 📊 **2. Agent 详情页** (`/agent/{agent_id}`)

#### 布局设计

```
┌─────────────────────────────────────────────────────────────┐
│ ← Back to List | Site A Agent                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Agent Overview                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🟢 Online | Last seen: 25 seconds ago                 │  │
│  │ Version: 1.0.0 | Uptime: 10 days 5 hours              │  │
│  │ Site: Beijing Data Center                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Real-time Metrics                                           │
│  ┌─────────┬─────────┬─────────┬─────────┐                 │
│  │ CPU     │ Memory  │ Disk    │ Latency │                 │
│  │ 15.2%   │ 42.8%   │ 68.5%   │ 25ms    │                 │
│  └─────────┴─────────┴─────────┴─────────┘                 │
│                                                              │
│  Miners Status                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Total: 50 | Online: 48 | Offline: 2 | Error: 0       │  │
│  │                                                        │  │
│  │ [Chart: Miner Status Distribution]                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Recent Events                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🟡 [10:30] Miner 192.168.1.105 high temperature      │  │
│  │ 🔴 [10:25] Miner 192.168.1.100 offline               │  │
│  │ 🟢 [10:20] Data uploaded successfully (50 miners)    │  │
│  │ 🟢 [10:19] Heartbeat sent                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [🎮 Send Command] [⚙️ Edit Config] [🗑️ Delete Agent]       │
└─────────────────────────────────────────────────────────────┘
```

#### 标签页设计

```html
<ul class="nav nav-tabs">
  <li><a href="#overview" class="active">Overview</a></li>
  <li><a href="#miners">Miners (50)</a></li>
  <li><a href="#commands">Commands</a></li>
  <li><a href="#events">Events & Alerts</a></li>
  <li><a href="#logs">Logs</a></li>
  <li><a href="#settings">Settings</a></li>
</ul>

<div class="tab-content">
  <!-- Overview Tab -->
  <div id="overview" class="tab-pane active">
    <!-- 统计卡片、图表 -->
  </div>
  
  <!-- Miners Tab -->
  <div id="miners" class="tab-pane">
    <!-- 矿机列表、状态 -->
  </div>
  
  <!-- Commands Tab -->
  <div id="commands" class="tab-pane">
    <!-- 指令历史、发送新指令 -->
  </div>
  
  <!-- Events Tab -->
  <div id="events" class="tab-pane">
    <!-- 事件时间线 -->
  </div>
  
  <!-- Logs Tab -->
  <div id="logs" class="tab-pane">
    <!-- 实时日志查看器 -->
  </div>
  
  <!-- Settings Tab -->
  <div id="settings" class="tab-pane">
    <!-- Agent 配置编辑 -->
  </div>
</div>
```

---

### ➕ **3. 创建 Agent 页面** (`/agent/create`)

#### 表单设计

```
┌─────────────────────────────────────────────────────────────┐
│ Create New Agent                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Basic Information                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Agent Name *                                          │  │
│  │ [_____________________]                               │  │
│  │                                                        │  │
│  │ Site *                                                 │  │
│  │ [Select Site ▼]                                       │  │
│  │                                                        │  │
│  │ Description                                            │  │
│  │ [_____________________]                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Permissions                                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ☑ Read (View telemetry data)                         │  │
│  │ ☑ Control (Execute commands)                         │  │
│  │ ☐ Config (Modify agent settings)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Settings                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Collection Interval: [60] seconds                     │  │
│  │ Heartbeat Interval: [30] seconds                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [✓ Create Agent] [✗ Cancel]                                │
│                                                              │
│  ⚠️ After creation, you will receive:                       │
│  - Agent ID (UUID)                                           │
│  - Access Token (ONLY shown once - save it!)                │
└─────────────────────────────────────────────────────────────┘
```

#### 创建成功页面

```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Agent Created Successfully                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Agent Credentials                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ⚠️ IMPORTANT: Save these credentials now!             │  │
│  │    The token will NOT be shown again.                 │  │
│  │                                                        │  │
│  │ Agent ID:                                              │  │
│  │ a1b2c3d4-e5f6-7890-abcd-ef1234567890                  │  │
│  │ [📋 Copy]                                              │  │
│  │                                                        │  │
│  │ Access Token:                                          │  │
│  │ eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...              │  │
│  │ [📋 Copy]                                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Next Steps                                                  │
│  1. Download agent installation script                       │
│     [⬇️ Download install.sh]                                │
│                                                              │
│  2. Create agent_config.ini with above credentials           │
│     [⬇️ Download config template]                           │
│                                                              │
│  3. Follow deployment guide                                  │
│     [📖 View Deployment Guide]                              │
│                                                              │
│  [← Back to Agent List]                                      │
└─────────────────────────────────────────────────────────────┘
```

---

### 🎮 **4. 控制指令页面** (`/agent/{agent_id}/commands`)

#### 布局设计

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Commands - Site A Agent                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [➕ Send New Command]                                       │
│                                                              │
│  Pending Commands (3)                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ⏳ Reboot Miner - 192.168.1.100                       │  │
│  │    Created: 2 min ago | Priority: High                │  │
│  │    [View] [Cancel]                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Recent Commands                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ✅ Reboot Miner - 192.168.1.105                       │  │
│  │    Executed: 10 min ago | Duration: 45s               │  │
│  │    Result: Successfully rebooted                       │  │
│  │    [View Details]                                      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ ❌ Switch Pool - 192.168.1.102                        │  │
│  │    Failed: 15 min ago                                  │  │
│  │    Error: Connection timeout                           │  │
│  │    [View Details] [Retry]                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 发送指令对话框

```html
<div class="modal" id="sendCommandModal">
  <div class="modal-content">
    <h3>Send Command</h3>
    
    <label>Command Type *</label>
    <select id="commandType">
      <option value="reboot_miner">Reboot Miner</option>
      <option value="switch_pool">Switch Pool</option>
      <option value="adjust_frequency">Adjust Frequency</option>
      <option value="enable_low_power">Enable Low Power</option>
    </select>
    
    <label>Target Miner *</label>
    <select id="targetMiner">
      <option value="192.168.1.100">192.168.1.100 - Antminer S19 Pro</option>
      <option value="192.168.1.101">192.168.1.101 - Antminer S19 Pro</option>
      <!-- ... -->
    </select>
    
    <label>Priority</label>
    <select id="priority">
      <option value="0">Low</option>
      <option value="5" selected>Normal</option>
      <option value="9">High</option>
    </select>
    
    <!-- 动态参数区域 (根据 commandType 变化) -->
    <div id="commandParams">
      <!-- 例如：Reboot Miner -->
      <label>Delay (seconds)</label>
      <input type="number" value="30" />
      
      <label>Reason</label>
      <input type="text" placeholder="e.g., scheduled_maintenance" />
    </div>
    
    <div class="modal-actions">
      <button class="btn-primary">Send Command</button>
      <button class="btn-secondary">Cancel</button>
    </div>
  </div>
</div>
```

---

### 📊 **5. 监控仪表盘** (`/agent/dashboard`)

#### 布局设计

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Monitoring Dashboard                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  System Overview                                             │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ Agents   │ Miners   │ Hashrate │ Alerts   │             │
│  │ 8/10     │ 485/500  │ 52.5 PH │ 12 open  │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
│                                                              │
│  ┌──────────────────────┬──────────────────────┐           │
│  │ Agent Status Map     │ Miners Distribution  │           │
│  │ [Pie Chart]          │ [Bar Chart]          │           │
│  └──────────────────────┴──────────────────────┘           │
│                                                              │
│  ┌──────────────────────────────────────────────┐           │
│  │ Hashrate Trend (Last 24h)                    │           │
│  │ [Line Chart with multi-agent comparison]     │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
│  Active Alerts                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🔴 Site C Agent offline for 5 minutes                 │  │
│  │ 🟡 Site A: Miner 192.168.1.105 high temperature      │  │
│  │ 🟡 Site B: 2 miners offline                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 UI 组件设计

### 状态指示器

```css
.status-indicator {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

.status-indicator.online {
  background: #10b981; /* 绿色 */
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
  animation: pulse 2s infinite;
}

.status-indicator.offline {
  background: #ef4444; /* 红色 */
}

.status-indicator.degraded {
  background: #f59e0b; /* 橙色 */
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### 统计卡片

```html
<div class="metric-card">
  <div class="metric-icon">
    <i class="bi bi-cpu-fill"></i>
  </div>
  <div class="metric-content">
    <div class="metric-value countup" data-target="48">0</div>
    <div class="metric-label">Active Miners</div>
    <div class="metric-change positive">
      <i class="bi bi-arrow-up"></i> +2 from yesterday
    </div>
  </div>
</div>
```

### 实时日志查看器

```html
<div class="log-viewer">
  <div class="log-toolbar">
    <input type="text" placeholder="Search logs..." />
    <select>
      <option>All Levels</option>
      <option>ERROR</option>
      <option>WARNING</option>
      <option>INFO</option>
      <option>DEBUG</option>
    </select>
    <button>📥 Download</button>
    <button>⏸️ Pause</button>
  </div>
  
  <div class="log-content" id="logContent">
    <div class="log-line error">
      <span class="log-time">10:30:25</span>
      <span class="log-level">ERROR</span>
      <span class="log-message">Failed to connect to 192.168.1.100:4028</span>
    </div>
    <div class="log-line warning">
      <span class="log-time">10:30:20</span>
      <span class="log-level">WARNING</span>
      <span class="log-message">High temperature detected: 75.2°C</span>
    </div>
    <div class="log-line info">
      <span class="log-time">10:30:15</span>
      <span class="log-level">INFO</span>
      <span class="log-message">Telemetry data sent successfully</span>
    </div>
  </div>
</div>
```

---

## 📱 响应式设计

### 移动端适配

```css
/* 桌面 (>1024px) */
@media (min-width: 1024px) {
  .agent-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* 平板 (768px - 1024px) */
@media (min-width: 768px) and (max-width: 1024px) {
  .agent-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 手机 (<768px) */
@media (max-width: 768px) {
  .agent-grid {
    grid-template-columns: 1fr;
  }
  
  .metric-row {
    flex-direction: column;
  }
  
  .tab-content {
    padding: 15px;
  }
}
```

---

## 🌐 多语言支持

### 英文/中文切换

```javascript
const translations = {
  en: {
    agentList: "Agent List",
    createAgent: "Create Agent",
    online: "Online",
    offline: "Offline",
    totalMiners: "Total Miners",
    // ...
  },
  zh: {
    agentList: "代理列表",
    createAgent: "创建代理",
    online: "在线",
    offline: "离线",
    totalMiners: "矿机总数",
    // ...
  }
};

function translate(key) {
  const lang = localStorage.getItem('language') || 'zh';
  return translations[lang][key] || key;
}
```

---

## 🔄 实时更新

### WebSocket 集成（可选）

```javascript
// 建立 WebSocket 连接
const ws = new WebSocket('wss://hashinsight.replit.app/agent/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'heartbeat') {
    updateAgentStatus(data.agent_id, 'online', data.timestamp);
  }
  
  if (data.type === 'event') {
    addEventToTimeline(data.event);
  }
  
  if (data.type === 'command_result') {
    updateCommandStatus(data.command_id, data.status, data.result);
  }
};
```

### 定期轮询

```javascript
// 每 30 秒刷新一次 Agent 状态
setInterval(async function() {
  const response = await fetch('/agent/api/admin/agents?status=all');
  const data = await response.json();
  
  updateAgentList(data.agents);
}, 30000);
```

---

## 🎯 交互设计

### 用户操作流程

#### 创建 Agent
```
1. 点击 "Create Agent"
2. 填写表单（名称、站点、权限）
3. 点击 "Create"
4. 显示 Agent ID 和 Token（仅一次）
5. 用户复制凭证
6. 下载部署脚本和配置模板
7. 跳转到 Agent 列表
```

#### 发送控制指令
```
1. 进入 Agent 详情页
2. 点击 "Send Command"
3. 选择指令类型（重启/切池/调频）
4. 选择目标矿机
5. 填写参数（如延迟时间）
6. 确认发送
7. 显示"指令已下发"提示
8. 在指令列表中显示待执行状态
9. Agent 执行后更新状态（成功/失败）
```

#### 查看实时日志
```
1. 进入 Agent 详情页
2. 切换到 "Logs" 标签
3. 日志实时滚动显示（WebSocket或轮询）
4. 可以暂停、搜索、过滤、下载
```

---

## 📊 数据可视化

### Chart.js 集成

```javascript
// 矿机状态饼图
const minerStatusChart = new Chart(ctx, {
  type: 'doughnut',
  data: {
    labels: ['Online', 'Offline', 'Error'],
    datasets: [{
      data: [48, 2, 0],
      backgroundColor: ['#10b981', '#ef4444', '#f59e0b']
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { position: 'bottom' }
    }
  }
});

// 算力趋势折线图
const hashrateTrendChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
    datasets: [
      {
        label: 'Site A',
        data: [52.3, 52.5, 52.1, 51.8, 52.4, 52.6],
        borderColor: '#3b82f6',
        tension: 0.4
      },
      {
        label: 'Site B',
        data: [98.5, 98.2, 97.9, 98.1, 98.4, 98.3],
        borderColor: '#10b981',
        tension: 0.4
      }
    ]
  },
  options: {
    responsive: true,
    scales: {
      y: { beginAtZero: true, title: { display: true, text: 'Hashrate (TH/s)' } }
    }
  }
});
```

---

## 🔔 通知和告警

### 浏览器通知

```javascript
// 请求通知权限
if (Notification.permission === 'default') {
  Notification.requestPermission();
}

// 显示告警通知
function showAlert(title, message, severity) {
  if (Notification.permission === 'granted') {
    new Notification(title, {
      body: message,
      icon: '/static/images/logo.png',
      badge: '/static/images/badge.png',
      tag: 'agent-alert',
      requireInteraction: severity === 'critical'
    });
  }
}

// 示例
showAlert(
  'Agent Offline',
  'Site C Agent has been offline for 5 minutes',
  'error'
);
```

### 页面内提示

```javascript
// Toast 通知
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.classList.add('show');
  }, 100);
  
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
```

---

## 📝 实施路线图

### Phase 1: 基础页面 (1-2天)
- ✅ Agent 列表页
- ✅ Agent 创建页
- ✅ Agent 详情页（基础信息）

### Phase 2: 交互功能 (2-3天)
- ✅ 控制指令界面
- ✅ 实时状态更新
- ✅ 日志查看器

### Phase 3: 监控和可视化 (2-3天)
- ✅ 统一监控仪表盘
- ✅ 图表和数据可视化
- ✅ 告警和通知

### Phase 4: 优化和完善 (1-2天)
- ✅ 响应式设计
- ✅ 性能优化
- ✅ 用户体验改进

---

## 📚 相关文档

- [架构设计](./miner_agent_architecture.md)
- [API 接口](./miner_agent_api.md)
- [数据库设计](./miner_agent_database.md)
- [部署指南](./miner_agent_deployment.md)

---

**文档版本**: v1.0.0  
**最后更新**: 2025-10-13
