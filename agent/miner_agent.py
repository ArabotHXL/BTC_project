#!/usr/bin/env python3
"""
HashInsight Enterprise - Miner Agent
矿机数据采集和控制代理

功能:
- CGMiner API 数据采集
- 实时遥测数据上报
- 远程控制指令执行
- 心跳和健康检查
- 离线数据缓冲

版本: 1.0.0
作者: HashInsight Team
"""

import json
import socket
import time
import logging
import requests
import threading
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque
import configparser

# ==================== 配置和常量 ====================

VERSION = "1.0.0"
DEFAULT_COLLECTION_INTERVAL = 60  # 采集间隔（秒）
DEFAULT_HEARTBEAT_INTERVAL = 30   # 心跳间隔（秒）
CGMINER_API_PORT = 4028          # CGMiner API 端口
CGMINER_TIMEOUT = 5              # CGMiner 连接超时
MAX_BUFFER_SIZE = 10000          # 最大缓冲数据量
MAX_BUFFER_HOURS = 24            # 最大缓冲时长（小时）

# ==================== 日志配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('miner_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('MinerAgent')

# ==================== CGMiner API 客户端 ====================

class CGMinerClient:
    """CGMiner API 客户端，用于与矿机通信"""
    
    def __init__(self, ip_address: str, port: int = CGMINER_API_PORT, timeout: int = CGMINER_TIMEOUT):
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
    
    def _send_command(self, command: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        发送 CGMiner API 命令
        
        Args:
            command: 命令名称 (如 'summary', 'stats', 'pools')
            params: 命令参数
        
        Returns:
            API 响应的 JSON 数据，失败返回 None
        """
        try:
            # 构造 JSON-RPC 请求
            request = {"command": command}
            if params:
                request.update(params)
            
            # 连接到 CGMiner API
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.ip_address, self.port))
            
            # 发送命令
            sock.sendall(json.dumps(request).encode('utf-8'))
            
            # 接收响应
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            
            sock.close()
            
            # 解析 JSON 响应
            if response:
                # CGMiner 响应可能以 null 字符结尾
                response_str = response.decode('utf-8').rstrip('\x00')
                return json.loads(response_str)
            
            return None
            
        except socket.timeout:
            logger.warning(f"Timeout connecting to {self.ip_address}:{self.port}")
            return None
        except socket.error as e:
            logger.warning(f"Socket error connecting to {self.ip_address}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from {self.ip_address}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying {self.ip_address}: {e}")
            return None
    
    def get_summary(self) -> Optional[Dict]:
        """获取矿机摘要信息"""
        return self._send_command('summary')
    
    def get_stats(self) -> Optional[Dict]:
        """获取矿机详细统计"""
        return self._send_command('stats')
    
    def get_pools(self) -> Optional[Dict]:
        """获取矿池信息"""
        return self._send_command('pools')
    
    def get_devs(self) -> Optional[Dict]:
        """获取设备信息"""
        return self._send_command('devs')
    
    def reboot(self) -> bool:
        """重启矿机"""
        result = self._send_command('restart')
        return result is not None
    
    def switch_pool(self, pool_id: int) -> bool:
        """切换矿池"""
        result = self._send_command('switchpool', {'id': pool_id})
        return result is not None
    
    def get_full_telemetry(self) -> Optional[Dict]:
        """
        获取完整的遥测数据
        
        Returns:
            包含所有关键指标的字典
        """
        summary = self.get_summary()
        stats = self.get_stats()
        pools = self.get_pools()
        devs = self.get_devs()
        
        if not summary:
            return None
        
        # 解析数据
        try:
            summary_data = summary.get('SUMMARY', [{}])[0]
            stats_data = stats.get('STATS', [{}])[0] if stats else {}
            pool_data = pools.get('POOLS', [{}])[0] if pools else {}
            dev_data = devs.get('DEVS', []) if devs else []
            
            # 计算平均温度和风扇转速
            temperatures = []
            fan_speeds = []
            
            for dev in dev_data:
                if 'Temperature' in dev:
                    temperatures.append(float(dev['Temperature']))
                if 'Fan Speed' in dev:
                    fan_speeds.append(int(dev['Fan Speed']))
            
            avg_temp = sum(temperatures) / len(temperatures) if temperatures else 0
            max_temp = max(temperatures) if temperatures else 0
            min_temp = min(temperatures) if temperatures else 0
            avg_fan = sum(fan_speeds) / len(fan_speeds) if fan_speeds else 0
            max_fan = max(fan_speeds) if fan_speeds else 0
            
            # 构造标准化的遥测数据
            telemetry = {
                "ip_address": self.ip_address,
                "status": "running" if summary_data.get('Status') == 'S' else "stopped",
                "timestamp": int(time.time()),
                
                # 算力数据
                "hashrate": {
                    "realtime_th": round(summary_data.get('GHS 5s', 0) / 1000, 2),
                    "avg_5s": round(summary_data.get('GHS 5s', 0) / 1000, 2),
                    "avg_1m": round(summary_data.get('GHS av', 0) / 1000, 2),
                    "avg_5m": round(summary_data.get('GHS 5m', 0) / 1000, 2),
                    "avg_15m": round(summary_data.get('GHS 15m', 0) / 1000, 2),
                },
                
                # 温度数据
                "temperature": {
                    "avg": round(avg_temp, 2),
                    "max": round(max_temp, 2),
                    "min": round(min_temp, 2),
                },
                
                # 风扇数据
                "fan": {
                    "avg_speed": int(avg_fan),
                    "max_speed": int(max_fan),
                },
                
                # 份额数据
                "shares": {
                    "accepted": summary_data.get('Accepted', 0),
                    "rejected": summary_data.get('Rejected', 0),
                    "hardware_errors": summary_data.get('Hardware Errors', 0),
                    "reject_rate": round(
                        (summary_data.get('Rejected', 0) / max(summary_data.get('Accepted', 1), 1)) * 100, 
                        2
                    ),
                },
                
                # 矿池数据
                "pool": {
                    "url": pool_data.get('URL', ''),
                    "worker": pool_data.get('User', ''),
                    "status": pool_data.get('Status', 'Unknown'),
                },
                
                # 运行时间
                "uptime_seconds": summary_data.get('Elapsed', 0),
                
                # 原始数据（调试用）
                "raw_summary": summary_data,
            }
            
            return telemetry
            
        except Exception as e:
            logger.error(f"Error parsing telemetry data from {self.ip_address}: {e}")
            return None

# ==================== 云端 API 客户端 ====================

class CloudAPIClient:
    """云端 API 客户端，负责与 HashInsight 云端平台通信"""
    
    def __init__(self, base_url: str, agent_id: str, access_token: str):
        self.base_url = base_url.rstrip('/')
        self.agent_id = agent_id
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': f'MinerAgent/{VERSION}'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        发送 HTTP 请求到云端 API
        
        Args:
            method: HTTP 方法 (GET/POST/PUT)
            endpoint: API 端点 (如 '/heartbeat')
            data: 请求体数据
            params: URL 查询参数
        
        Returns:
            API 响应的 JSON 数据，失败返回 None
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=data, params=params, timeout=30)
            elif method == 'PUT':
                response = self.session.put(url, json=data, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # 检查响应状态
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("Authentication failed - invalid or expired token")
                return None
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded")
                return None
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {url}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            return None
    
    def send_heartbeat(self, stats: Dict) -> Optional[Dict]:
        """发送心跳"""
        payload = {
            "agent_id": self.agent_id,
            "timestamp": int(time.time()),
            "version": VERSION,
            "status": "online",
            "stats": stats
        }
        return self._make_request('POST', '/heartbeat', data=payload)
    
    def send_telemetry(self, miners_data: List[Dict]) -> Optional[Dict]:
        """上报遥测数据"""
        payload = {
            "agent_id": self.agent_id,
            "timestamp": int(time.time()),
            "batch_size": len(miners_data),
            "miners": miners_data
        }
        return self._make_request('POST', '/telemetry', data=payload)
    
    def send_telemetry_batch(self, batches: List[Dict]) -> Optional[Dict]:
        """批量上报缓冲的遥测数据"""
        payload = {
            "agent_id": self.agent_id,
            "offline_period": {
                "start": batches[0]['timestamp'] if batches else int(time.time()),
                "end": batches[-1]['timestamp'] if batches else int(time.time())
            },
            "batches": batches
        }
        return self._make_request('POST', '/telemetry/batch', data=payload)
    
    def get_pending_commands(self) -> List[Dict]:
        """获取待执行的控制指令"""
        params = {"agent_id": self.agent_id}
        response = self._make_request('GET', '/commands/pending', params=params)
        
        if response and response.get('status') == 'success':
            return response.get('data', {}).get('commands', [])
        return []
    
    def report_command_result(self, command_id: str, status: str, result: Optional[Dict] = None, error: Optional[Dict] = None) -> bool:
        """上报指令执行结果"""
        payload = {
            "agent_id": self.agent_id,
            "command_id": command_id,
            "status": status,
            "executed_at": int(time.time())
        }
        
        if result:
            payload["result"] = result
            payload["completed_at"] = int(time.time())
        
        if error:
            payload["error"] = error
        
        response = self._make_request('POST', f'/commands/{command_id}/result', data=payload)
        return response is not None
    
    def send_event(self, event_type: str, severity: str, title: str, message: str, details: Optional[Dict] = None) -> bool:
        """上报事件"""
        payload = {
            "agent_id": self.agent_id,
            "events": [{
                "event_type": event_type,
                "severity": severity,
                "title": title,
                "message": message,
                "timestamp": int(time.time()),
                "details": details or {}
            }]
        }
        response = self._make_request('POST', '/events', data=payload)
        return response is not None

# ==================== 数据缓冲管理器 ====================

class DataBuffer:
    """离线数据缓冲管理器"""
    
    def __init__(self, max_size: int = MAX_BUFFER_SIZE, max_hours: int = MAX_BUFFER_HOURS):
        self.buffer = deque(maxlen=max_size)
        self.max_hours = max_hours
        self.lock = threading.Lock()
    
    def add(self, data: Dict):
        """添加数据到缓冲区"""
        with self.lock:
            self.buffer.append(data)
            self._cleanup_old_data()
    
    def get_all(self) -> List[Dict]:
        """获取所有缓冲数据"""
        with self.lock:
            return list(self.buffer)
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer.clear()
    
    def size(self) -> int:
        """获取缓冲区大小"""
        with self.lock:
            return len(self.buffer)
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        if not self.buffer:
            return
        
        max_age = self.max_hours * 3600  # 转换为秒
        current_time = int(time.time())
        
        # 从左侧删除过期数据
        while self.buffer and (current_time - self.buffer[0].get('timestamp', current_time)) > max_age:
            self.buffer.popleft()

# ==================== 指令执行器 ====================

class CommandExecutor:
    """控制指令执行器"""
    
    def __init__(self, cloud_client: CloudAPIClient):
        self.cloud_client = cloud_client
    
    def execute_command(self, command: Dict) -> Dict:
        """
        执行控制指令
        
        Args:
            command: 指令字典，包含 command_type, target_ip, params
        
        Returns:
            执行结果字典
        """
        command_id = command.get('command_id')
        command_type = command.get('command_type')
        target_ip = command.get('target_ip')
        params = command.get('params', {})
        
        # 验证必需参数并上报错误
        if not command_id or not command_type or not target_ip:
            error_msg = "Missing required parameters: command_id, command_type, or target_ip"
            logger.error(error_msg)
            error = {"error_code": "INVALID_COMMAND", "message": error_msg}
            
            # 如果有command_id，上报失败结果到控制平面
            if command_id:
                self.cloud_client.report_command_result(command_id, 'failed', error=error)
            
            return {"status": "failed", "error": error}
        
        logger.info(f"Executing command {command_id}: {command_type} on {target_ip}")
        
        try:
            cgminer = CGMinerClient(target_ip)
            
            if command_type == 'reboot_miner':
                # 重启矿机
                delay = params.get('delay_seconds', 0)
                if delay > 0:
                    logger.info(f"Waiting {delay} seconds before reboot...")
                    time.sleep(delay)
                
                success = cgminer.reboot()
                
                if success:
                    result = {
                        "message": "Miner reboot command sent successfully",
                        "delay_seconds": delay
                    }
                    self.cloud_client.report_command_result(command_id, 'success', result=result)
                    return {"status": "success", "result": result}
                else:
                    error = {
                        "error_code": "REBOOT_FAILED",
                        "message": "Failed to send reboot command to miner"
                    }
                    self.cloud_client.report_command_result(command_id, 'failed', error=error)
                    return {"status": "failed", "error": error}
            
            elif command_type == 'switch_pool':
                # 切换矿池
                pool_id = params.get('pool_id', 0)
                success = cgminer.switch_pool(pool_id)
                
                if success:
                    result = {
                        "message": f"Switched to pool {pool_id}",
                        "pool_id": pool_id
                    }
                    self.cloud_client.report_command_result(command_id, 'success', result=result)
                    return {"status": "success", "result": result}
                else:
                    error = {
                        "error_code": "SWITCH_POOL_FAILED",
                        "message": "Failed to switch pool"
                    }
                    self.cloud_client.report_command_result(command_id, 'failed', error=error)
                    return {"status": "failed", "error": error}
            
            else:
                # 不支持的指令类型
                error = {
                    "error_code": "UNSUPPORTED_COMMAND",
                    "message": f"Command type {command_type} is not supported"
                }
                self.cloud_client.report_command_result(command_id, 'failed', error=error)
                return {"status": "failed", "error": error}
                
        except Exception as e:
            logger.error(f"Error executing command {command_id}: {e}")
            error = {
                "error_code": "EXECUTION_ERROR",
                "message": str(e)
            }
            self.cloud_client.report_command_result(command_id, 'failed', error=error)
            return {"status": "failed", "error": error}

# ==================== Miner Agent 主类 ====================

class MinerAgent:
    """矿机代理主类"""
    
    def __init__(self, config_file: str = 'agent_config.ini'):
        self.config_file = config_file
        self.config = self._load_config()
        
        # 初始化组件
        self.cloud_client = CloudAPIClient(
            base_url=self.config['api_base_url'],
            agent_id=self.config['agent_id'],
            access_token=self.config['access_token']
        )
        
        self.data_buffer = DataBuffer()
        self.command_executor = CommandExecutor(self.cloud_client)
        
        # 矿机列表（IP 地址）
        self.miner_ips = self.config.get('miner_ips', [])
        
        # 状态标志
        self.running = False
        self.online = False
        self.start_time = int(time.time())
        
        # 线程
        self.heartbeat_thread = None
        self.collection_thread = None
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        config = configparser.ConfigParser()
        
        if not os.path.exists(self.config_file):
            logger.error(f"Config file not found: {self.config_file}")
            sys.exit(1)
        
        config.read(self.config_file)
        
        return {
            'agent_id': config.get('agent', 'agent_id'),
            'access_token': config.get('agent', 'access_token'),
            'api_base_url': config.get('cloud', 'api_base_url'),
            'miner_ips': config.get('miners', 'ip_list', fallback='').split(','),
            'collection_interval': config.getint('settings', 'collection_interval', fallback=DEFAULT_COLLECTION_INTERVAL),
            'heartbeat_interval': config.getint('settings', 'heartbeat_interval', fallback=DEFAULT_HEARTBEAT_INTERVAL),
        }
    
    def start(self):
        """启动 Agent"""
        logger.info(f"Starting Miner Agent v{VERSION}")
        logger.info(f"Agent ID: {self.config['agent_id']}")
        logger.info(f"Monitoring {len(self.miner_ips)} miners")
        
        self.running = True
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        # 启动数据采集线程
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        
        # 主循环 - 处理控制指令
        try:
            self._command_loop()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
    
    def stop(self):
        """停止 Agent"""
        logger.info("Stopping Miner Agent...")
        self.running = False
        
        # 等待线程结束
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        
        logger.info("Miner Agent stopped")
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                # 收集系统状态
                stats = self._collect_system_stats()
                
                # 发送心跳
                response = self.cloud_client.send_heartbeat(stats)
                
                if response:
                    self.online = True
                    logger.debug("Heartbeat sent successfully")
                    
                    # 检查是否有待执行指令（心跳响应中携带）
                    commands = response.get('data', {}).get('commands', [])
                    for command in commands:
                        self._execute_command_async(command)
                else:
                    if self.online:
                        logger.warning("Heartbeat failed - entering offline mode")
                        self.online = False
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                self.online = False
            
            time.sleep(self.config['heartbeat_interval'])
    
    def _collection_loop(self):
        """数据采集循环"""
        while self.running:
            try:
                # 采集所有矿机数据
                miners_data = []
                
                for ip in self.miner_ips:
                    if not ip.strip():
                        continue
                    
                    cgminer = CGMinerClient(ip.strip())
                    telemetry = cgminer.get_full_telemetry()
                    
                    if telemetry:
                        miners_data.append(telemetry)
                
                logger.info(f"Collected data from {len(miners_data)}/{len(self.miner_ips)} miners")
                
                # 尝试上报数据
                if self.online:
                    response = self.cloud_client.send_telemetry(miners_data)
                    
                    if response:
                        logger.info("Telemetry data sent successfully")
                        
                        # 如果之前有缓冲数据，批量上报
                        if self.data_buffer.size() > 0:
                            self._flush_buffer()
                    else:
                        # 上报失败，缓冲数据
                        logger.warning("Telemetry upload failed - buffering data")
                        self.data_buffer.add({
                            'timestamp': int(time.time()),
                            'miners': miners_data
                        })
                else:
                    # 离线模式，缓冲数据
                    logger.info(f"Offline mode - buffering data (buffer size: {self.data_buffer.size()})")
                    self.data_buffer.add({
                        'timestamp': int(time.time()),
                        'miners': miners_data
                    })
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
            
            time.sleep(self.config['collection_interval'])
    
    def _command_loop(self):
        """控制指令处理循环（主线程）"""
        while self.running:
            try:
                if self.online:
                    # 获取待执行指令
                    commands = self.cloud_client.get_pending_commands()
                    
                    for command in commands:
                        self._execute_command_async(command)
                
            except Exception as e:
                logger.error(f"Error in command loop: {e}")
            
            time.sleep(10)  # 每10秒检查一次指令
    
    def _execute_command_async(self, command: Dict):
        """异步执行指令"""
        thread = threading.Thread(
            target=self.command_executor.execute_command,
            args=(command,),
            daemon=True
        )
        thread.start()
    
    def _collect_system_stats(self) -> Dict:
        """收集系统状态"""
        # 简化版本，实际可以使用 psutil 库获取更详细的信息
        return {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "uptime_seconds": int(time.time() - self.start_time),
            "miners": {
                "total": len(self.miner_ips),
                "online": 0,  # 需要实际检测
                "offline": 0,
            }
        }
    
    def _flush_buffer(self):
        """批量上报缓冲数据"""
        buffer_data = self.data_buffer.get_all()
        
        if not buffer_data:
            return
        
        logger.info(f"Flushing {len(buffer_data)} buffered data points...")
        
        # 批量上报
        response = self.cloud_client.send_telemetry_batch(buffer_data)
        
        if response:
            logger.info("Buffered data uploaded successfully")
            self.data_buffer.clear()
        else:
            logger.warning("Failed to upload buffered data")

# ==================== 主程序入口 ====================

def main():
    """主程序入口"""
    # 解析命令行参数
    import argparse
    
    parser = argparse.ArgumentParser(description='HashInsight Miner Agent')
    parser.add_argument('--config', default='agent_config.ini', help='Configuration file path')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    
    args = parser.parse_args()
    
    # 创建并启动 Agent
    agent = MinerAgent(config_file=args.config)
    agent.start()

if __name__ == '__main__':
    main()
