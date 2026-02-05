# HashInsight Miner Diagnosis & Playbook Flow (v0.2)

> 目标：你的 App 能做到  
> **“哪台机器有问题 → 报什么错 → 怎样修 → 怎样避免 → 怎样调 setup”**

```mermaid
flowchart TD
  A[Telemetry Ingest<br/>CGMiner/HTTP/Web UI/Logs] --> B[Normalize & Enrich<br/>model_id, firmware, site, pool]
  B --> C[Signal Extraction<br/>keywords/regex/metrics/codes]
  C --> D[Signature Match Engine<br/>score + priority]
  D -->|Top 1-3| E[Diagnosis Output<br/>fault_category + confidence]
  E --> F[Playbook<br/>Step-by-step SOP]
  F --> G[Verification<br/>hashrate/temps/reject/uptime]
  G -->|Pass| H[Close Incident<br/>attach artifacts]
  G -->|Fail| I[Escalate<br/>board-level repair / RMA]
  E --> J[Prevention Checklist<br/>巡检/环境/变更管理]
  E --> K[Tuning Actions<br/>降频/限功率/风扇策略/Failover]
  H --> L[Learn & Update KB<br/>new signature / mapping]
  I --> L
```

## 输出给运维人员（建议 UI 结构）
- **Summary**：Machine / Severity / Category / Confidence
- **What happened**：匹配到的日志片段、指标异常（温度、掉链、拒绝率、重启次数…）
- **How to fix (Playbook)**：按步骤展开（带安全提示）
- **How to prevent**：巡检与环境、变更管理建议
- **How to tune setup**：降频/限功率/Failover/NTP-DNS 基线
- **Evidence pack**：截图/日志/测点记录（用于 RCA + 维修交接）
