# Miner Knowledge Base (KB) Integration Documentation

## Overview

The Miner Knowledge Base (KB) v0.3.2 is an intelligent fault diagnosis and repair guidance system integrated into HashInsight Enterprise. It provides automated diagnosis of miner issues, structured repair playbooks, and preventive maintenance recommendations.

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **Fault Diagnosis** | 38 fault signatures covering power, thermal, hashrate, and network issues |
| **Repair Playbooks** | 9 structured SOPs with safety warnings and verification steps |
| **Error Code Explanation** | Dictionary support for Bitmain, WhatsMiner, and Avalon error codes |
| **Prevention Tips** | Proactive maintenance recommendations |
| **Multi-language** | Chinese and English support |

### Supported Brands

- **Bitmain** (Antminer series) - Full error code dictionary
- **WhatsMiner** (MicroBT) - Error code support
- **Avalon** (Canaan) - Error code support

## API Endpoints

### 1. Get KB Version

```
GET /api/kb/version
```

**Response:**
```json
{
  "success": true,
  "kb_version": "0.3.2",
  "signatures": 38,
  "playbooks": 9,
  "preventions": 3,
  "brands_with_error_dict": ["microbt", "canaan", "bitmain"]
}
```

### 2. Diagnose Miner Issues

```
POST /api/kb/diagnose
Content-Type: application/json
```

**Request Body:**
```json
{
  "miner_id": "M001",
  "model_id": "antminer_s19",
  "brand": "Bitmain",
  "timestamp": "2026-02-05T10:00:00Z",
  "logs": ["Power supply failure detected", "ERROR_POWER_LOST"],
  "metrics": {
    "uptime_sec": 100,
    "temperature_avg": 85,
    "hashrate_current": 5,
    "fan_avg": 4500
  }
}
```

**Response:**
```json
{
  "success": true,
  "miner_id": "M001",
  "confidence": 0.902,
  "selected": {
    "fault_id": "power_psu_failure",
    "title": "PSU Failure",
    "severity": "critical",
    "category": "power",
    "reasons": ["Log match: ERROR_POWER_LOST", "Low uptime detected"]
  },
  "playbook": {
    "playbook_id": "pb_power_psu_no_output_or_protect",
    "title": "供电/PSU：无输出、保护模式、掉电重启",
    "goal": "快速区分外部供电/线缆/PSU 与矿机内部短路或过载",
    "safety": ["高压危险：任何拆PSU/测量前必须断电并等待放电"],
    "steps": ["记录PSU指示灯/风扇状态", "检查铜排螺丝", "..."],
    "verification": ["稳定运行 30-60 分钟无掉电"]
  },
  "prevention": {
    "checks": ["维修台与腕带接地", "拆机前断电等待放电"]
  },
  "error_code_explanations": [
    {
      "code": "ERROR_POWER_LOST",
      "title": "Power status/voltage read failed",
      "meaning": "电源状态/电压读取异常",
      "quick_fix": "检查电源线、稳压线",
      "severity": "critical",
      "category": "power"
    }
  ]
}
```

### 3. Explain Error Codes

**GET (Single Code):**
```
GET /api/kb/error-explain?brand=Bitmain&code=ERROR_POWER_LOST
```

**POST (Multiple Codes):**
```
POST /api/kb/error-explain
Content-Type: application/json

{
  "brand": "Bitmain",
  "codes": ["ERROR_POWER_LOST", "ERROR_TEMP_TOO_HIGH"]
}
```

**Response:**
```json
{
  "success": true,
  "brand": "Bitmain",
  "explanations": [
    {
      "code": "ERROR_POWER_LOST",
      "title": "Power status/voltage read failed",
      "meaning": "电源状态/电压读取异常，可能是供电链路或PSU问题",
      "quick_fix": "检查电源线、稳压线、铜排/螺丝是否松动；确认市电电压稳定",
      "severity": "critical",
      "category": "power"
    }
  ]
}
```

### 4. Generate Ticket Draft

```
POST /api/kb/ticket-draft
Content-Type: application/json
```

**Request Body:** Same as `/api/kb/diagnose`

**Response:**
```json
{
  "success": true,
  "ticket": {
    "subject": "[CRITICAL] PSU Failure - M001",
    "description": "诊断结果：PSU故障\n置信度：90.2%\n...",
    "priority": "critical",
    "category": "power",
    "sop_steps": ["检查PSU指示灯", "更换电源线测试", "..."],
    "verification_points": ["稳定运行30分钟无掉电"]
  }
}
```

## UI Integration Points

### 1. Client Miners Page (`/hosting/client/miners`)

Each miner row displays a KB Diagnosis button (journal-medical icon). Clicking it:
1. Opens the KB Diagnosis modal
2. Uses cached miner data (no extra API call)
3. Calls `/api/kb/diagnose` with miner metrics
4. Displays structured diagnosis results

### 2. Event Monitoring Page (`/hosting/event-monitoring`)

Alert events include a "KB Diagnosis" button that:
1. Analyzes the alert context
2. Provides relevant repair playbook
3. Offers one-click ticket generation with SOP steps

## Diagnosis Flow

```
┌─────────────────┐
│  Miner Metrics  │ (temperature, hashrate, logs, error codes)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  KB Diagnosis   │ (38 fault signatures)
│    Engine       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Match Faults   │ → Confidence Score (0-100%)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Repair SOP     │ → Safety + Steps + Verification
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Prevention     │ → Maintenance Tips
└─────────────────┘
```

## Fault Categories

| Category | Description | Example Faults |
|----------|-------------|----------------|
| **power** | PSU, voltage, power supply issues | PSU failure, power lost |
| **thermal** | Temperature, cooling problems | Overheating, fan failure |
| **hashrate** | Mining performance issues | Low hashrate, chip errors |
| **network** | Connectivity problems | Network timeout, connection lost |
| **hardware** | Physical component failures | Board failure, sensor error |

## Confidence Scoring

The diagnosis confidence is calculated based on:
- **Log Matches**: Error patterns found in miner logs (40%)
- **Metric Rules**: Temperature, hashrate, uptime thresholds (35%)
- **Error Codes**: Known error code detection (25%)

Confidence levels:
- **≥80%**: High confidence - proceed with recommended SOP
- **50-79%**: Medium confidence - verify before proceeding
- **<50%**: Low confidence - gather more diagnostic data

## Safety Warnings

All repair playbooks include safety warnings when applicable:
- ⚠️ **High Voltage**: Disconnect power before PSU work
- ⚠️ **ESD Protection**: Use anti-static equipment
- ⚠️ **Hot Surfaces**: Wait for cooling before handling

## File Structure

```
kb/
├── miner_kb.zip              # Compressed KB data
│   ├── fault_signatures.json # 38 fault patterns
│   ├── playbooks.json        # 9 repair SOPs
│   ├── preventions.json      # Maintenance tips
│   └── error_dicts/          # Brand-specific error codes
│       ├── bitmain.json
│       ├── whatsminer.json
│       └── avalon.json

services/
└── miner_kb_service.py       # KB service implementation

routes/
└── kb_routes.py              # Flask API Blueprint
```

## Configuration

The KB service is registered in `app.py`:
```python
from routes.kb_routes import kb_bp
app.register_blueprint(kb_bp, url_prefix='/api/kb')
```

## Best Practices

1. **Regular KB Updates**: Update `miner_kb.zip` when new fault signatures are available
2. **Log Collection**: Ensure miner logs are captured for accurate diagnosis
3. **Metric Thresholds**: Adjust thresholds based on your specific environment
4. **Ticket Integration**: Use generated ticket drafts as starting points, not final submissions

## Troubleshooting

| Issue | Solution |
|-------|----------|
| KB not loading | Check `kb/miner_kb.zip` exists and is valid |
| No diagnosis results | Verify miner data includes logs and metrics |
| Error code not found | Brand might not be in supported list |
| Low confidence | Provide more diagnostic data (logs, metrics) |

## Version History

| Version | Changes |
|---------|---------|
| 0.3.2 | Added Bitmain log-code dictionary, expanded signatures |
| 0.3.1 | Added brand error-code dictionaries |
| 0.3.0 | Normalized playbook structure, prevention tips |
