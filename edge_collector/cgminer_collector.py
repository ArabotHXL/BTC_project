#!/usr/bin/env python3
"""
HashInsight Edge Collector - 矿场边缘数据采集器
Mining Farm Edge Data Collector

功能:
- 通过CGMiner API (端口4028) 采集矿机实时数据
- 支持批量采集6000+矿机
- 数据压缩后上传到云端
- 断网时本地缓存，恢复后自动重传
- 支持Antminer S19/S21, Whatsminer M30/M50, Avalon等主流矿机

部署: 在矿场本地服务器运行此脚本
"""

import socket
import json
import gzip
import time
import logging
import threading
import queue
import os
import sqlite3
import hashlib
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EdgeCollector')


@dataclass
class MinerData:
    """矿机数据结构"""
    miner_id: str
    ip_address: str
    timestamp: str
    online: bool
    hashrate_ghs: float = 0.0
    hashrate_5s_ghs: float = 0.0
    temperature_avg: float = 0.0
    temperature_max: float = 0.0
    temperature_chips: List[float] = None
    fan_speeds: List[int] = None
    frequency_avg: float = 0.0
    accepted_shares: int = 0
    rejected_shares: int = 0
    hardware_errors: int = 0
    uptime_seconds: int = 0
    power_consumption: float = 0.0
    efficiency: float = 0.0
    pool_url: str = ""
    worker_name: str = ""
    firmware_version: str = ""
    error_message: str = ""
    
    def __post_init__(self):
        if self.temperature_chips is None:
            self.temperature_chips = []
        if self.fan_speeds is None:
            self.fan_speeds = []


class CGMinerAPI:
    """CGMiner API客户端"""
    
    def __init__(self, host: str, port: int = 4028, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
    
    def send_command(self, command: str, parameter: str = "") -> Optional[Dict]:
        """发送API命令并返回JSON响应"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            request = json.dumps({"command": command, "parameter": parameter})
            sock.sendall(request.encode('utf-8'))
            
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\x00' in chunk:
                    break
            
            sock.close()
            
            data = response.rstrip(b'\x00').decode('utf-8', errors='ignore')
            return json.loads(data) if data else None
            
        except socket.timeout:
            logger.debug(f"Timeout connecting to {self.host}:{self.port}")
            return None
        except ConnectionRefusedError:
            logger.debug(f"Connection refused: {self.host}:{self.port}")
            return None
        except Exception as e:
            logger.debug(f"Error querying {self.host}: {e}")
            return None
    
    def get_summary(self) -> Optional[Dict]:
        """获取矿机摘要信息"""
        return self.send_command("summary")
    
    def get_stats(self) -> Optional[Dict]:
        """获取详细统计信息(温度、频率等)"""
        return self.send_command("stats")
    
    def get_pools(self) -> Optional[Dict]:
        """获取矿池信息"""
        return self.send_command("pools")
    
    def get_devs(self) -> Optional[Dict]:
        """获取设备信息"""
        return self.send_command("devs")
    
    def get_version(self) -> Optional[Dict]:
        """获取版本信息"""
        return self.send_command("version")


class MinerDataParser:
    """矿机数据解析器 - 支持多种矿机固件"""
    
    @staticmethod
    def parse_antminer(summary: Dict, stats: Dict, pools: Dict, ip: str, miner_id: str) -> MinerData:
        """解析Antminer数据 (S19/S21/T19等)"""
        data = MinerData(
            miner_id=miner_id,
            ip_address=ip,
            timestamp=datetime.utcnow().isoformat(),
            online=True
        )
        
        try:
            if summary and 'SUMMARY' in summary and summary['SUMMARY']:
                s = summary['SUMMARY'][0]
                data.hashrate_ghs = s.get('GHS av', s.get('MHS av', 0) / 1000)
                data.hashrate_5s_ghs = s.get('GHS 5s', s.get('MHS 5s', 0) / 1000)
                data.accepted_shares = s.get('Accepted', 0)
                data.rejected_shares = s.get('Rejected', 0)
                data.hardware_errors = s.get('Hardware Errors', 0)
                data.uptime_seconds = s.get('Elapsed', 0)
            
            if stats and 'STATS' in stats:
                temps = []
                fans = []
                freqs = []
                
                for stat in stats['STATS']:
                    for key, value in stat.items():
                        if isinstance(value, (int, float)):
                            key_lower = key.lower()
                            if 'temp' in key_lower and value > 0 and value < 150:
                                temps.append(value)
                            elif 'fan' in key_lower and value > 0:
                                fans.append(int(value))
                            elif 'freq' in key_lower and value > 0:
                                freqs.append(value)
                
                if temps:
                    data.temperature_chips = temps
                    data.temperature_avg = sum(temps) / len(temps)
                    data.temperature_max = max(temps)
                if fans:
                    data.fan_speeds = fans
                if freqs:
                    data.frequency_avg = sum(freqs) / len(freqs)
            
            if pools and 'POOLS' in pools and pools['POOLS']:
                pool = pools['POOLS'][0]
                data.pool_url = pool.get('URL', '')
                data.worker_name = pool.get('User', '')
        
        except Exception as e:
            logger.error(f"Error parsing Antminer data for {ip}: {e}")
            data.error_message = str(e)
        
        return data
    
    @staticmethod
    def parse_whatsminer(summary: Dict, stats: Dict, pools: Dict, ip: str, miner_id: str) -> MinerData:
        """解析Whatsminer数据 (M30/M50等)"""
        return MinerDataParser.parse_antminer(summary, stats, pools, ip, miner_id)
    
    @staticmethod
    def parse_avalon(summary: Dict, stats: Dict, pools: Dict, ip: str, miner_id: str) -> MinerData:
        """解析Avalon数据"""
        return MinerDataParser.parse_antminer(summary, stats, pools, ip, miner_id)


class OfflineCache:
    """离线缓存管理器 - 使用SQLite存储"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "offline_cache.db"
        self._init_db()
    
    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE,
                data BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    
    def save_batch(self, batch_id: str, data: bytes):
        """保存待上传批次"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR REPLACE INTO pending_uploads (batch_id, data) VALUES (?, ?)',
                (batch_id, data)
            )
            conn.commit()
            logger.info(f"Cached batch {batch_id} for later upload")
        finally:
            conn.close()
    
    def get_pending_batches(self, max_retry: int = 5) -> List[Tuple[str, bytes]]:
        """获取待上传批次"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT batch_id, data FROM pending_uploads WHERE retry_count < ? ORDER BY created_at',
                (max_retry,)
            )
            return cursor.fetchall()
        finally:
            conn.close()
    
    def mark_uploaded(self, batch_id: str):
        """标记批次已上传"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM pending_uploads WHERE batch_id = ?', (batch_id,))
            conn.commit()
        finally:
            conn.close()
    
    def increment_retry(self, batch_id: str):
        """增加重试次数"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE pending_uploads SET retry_count = retry_count + 1 WHERE batch_id = ?',
                (batch_id,)
            )
            conn.commit()
        finally:
            conn.close()


class CloudUploader:
    """云端数据上传器"""
    
    def __init__(self, api_url: str, api_key: str, site_id: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.site_id = site_id
        self.session = requests.Session()
        self.session.headers.update({
            'X-Collector-Key': api_key,
            'X-Site-ID': site_id,
            'Content-Type': 'application/octet-stream',
            'Content-Encoding': 'gzip'
        })
    
    def upload(self, data: List[MinerData]) -> bool:
        """上传矿机数据到云端"""
        try:
            json_data = json.dumps([asdict(d) for d in data])
            compressed = gzip.compress(json_data.encode('utf-8'))
            
            response = self.session.post(
                f"{self.api_url}/api/collector/upload",
                data=compressed,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"Uploaded {len(data)} miner records successfully")
                    return True
                else:
                    logger.error(f"Upload failed: {result.get('error')}")
                    return False
            else:
                logger.error(f"Upload HTTP error: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.warning("Network unavailable, data will be cached")
            return False
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False


class EdgeCollector:
    """边缘采集器主类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.miners = config.get('miners', [])
        self.collection_interval = config.get('collection_interval', 30)
        self.max_workers = config.get('max_workers', 50)
        self.api_url = config.get('api_url', 'http://localhost:5000')
        self.api_key = config.get('api_key', '')
        self.site_id = config.get('site_id', 'default')
        
        self.cache = OfflineCache(config.get('cache_dir', './cache'))
        self.uploader = CloudUploader(self.api_url, self.api_key, self.site_id)
        
        self.running = False
        self.stats = {
            'total_collected': 0,
            'successful': 0,
            'failed': 0,
            'last_collection': None
        }
    
    def collect_single_miner(self, miner_config: Dict) -> Optional[MinerData]:
        """采集单个矿机数据"""
        ip = miner_config.get('ip')
        miner_id = miner_config.get('id', ip)
        miner_type = miner_config.get('type', 'antminer').lower()
        port = miner_config.get('port', 4028)
        
        api = CGMinerAPI(ip, port)
        
        summary = api.get_summary()
        if not summary:
            return MinerData(
                miner_id=miner_id,
                ip_address=ip,
                timestamp=datetime.utcnow().isoformat(),
                online=False,
                error_message="Connection failed"
            )
        
        stats = api.get_stats()
        pools = api.get_pools()
        
        if miner_type == 'whatsminer':
            return MinerDataParser.parse_whatsminer(summary, stats, pools, ip, miner_id)
        elif miner_type == 'avalon':
            return MinerDataParser.parse_avalon(summary, stats, pools, ip, miner_id)
        else:
            return MinerDataParser.parse_antminer(summary, stats, pools, ip, miner_id)
    
    def collect_all(self) -> List[MinerData]:
        """并行采集所有矿机数据"""
        results = []
        start_time = time.time()
        
        logger.info(f"Starting collection for {len(self.miners)} miners...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_miner = {
                executor.submit(self.collect_single_miner, m): m
                for m in self.miners
            }
            
            for future in as_completed(future_to_miner):
                miner = future_to_miner[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                        if data.online:
                            self.stats['successful'] += 1
                        else:
                            self.stats['failed'] += 1
                except Exception as e:
                    logger.error(f"Collection error for {miner.get('ip')}: {e}")
                    self.stats['failed'] += 1
        
        elapsed = time.time() - start_time
        self.stats['total_collected'] += len(results)
        self.stats['last_collection'] = datetime.utcnow().isoformat()
        
        online_count = sum(1 for r in results if r.online)
        logger.info(f"Collected {len(results)} miners ({online_count} online) in {elapsed:.2f}s")
        
        return results
    
    def upload_data(self, data: List[MinerData]) -> bool:
        """上传数据到云端，失败时缓存"""
        if not data:
            return True
        
        if self.uploader.upload(data):
            return True
        else:
            batch_id = f"{self.site_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            json_data = json.dumps([asdict(d) for d in data])
            compressed = gzip.compress(json_data.encode('utf-8'))
            self.cache.save_batch(batch_id, compressed)
            return False
    
    def retry_pending_uploads(self):
        """重试待上传的缓存数据"""
        pending = self.cache.get_pending_batches()
        if not pending:
            return
        
        logger.info(f"Retrying {len(pending)} cached batches...")
        
        for batch_id, compressed_data in pending:
            try:
                response = self.uploader.session.post(
                    f"{self.uploader.api_url}/api/collector/upload",
                    data=compressed_data,
                    timeout=30
                )
                
                if response.status_code == 200 and response.json().get('success'):
                    self.cache.mark_uploaded(batch_id)
                    logger.info(f"Cached batch {batch_id} uploaded successfully")
                else:
                    self.cache.increment_retry(batch_id)
            except Exception as e:
                logger.error(f"Retry upload error for {batch_id}: {e}")
                self.cache.increment_retry(batch_id)
    
    def run_once(self) -> Dict:
        """执行单次采集和上传"""
        data = self.collect_all()
        success = self.upload_data(data)
        self.retry_pending_uploads()
        
        return {
            'collected': len(data),
            'online': sum(1 for d in data if d.online),
            'offline': sum(1 for d in data if not d.online),
            'upload_success': success,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def run(self):
        """持续运行采集循环"""
        self.running = True
        logger.info(f"Edge Collector started. Site: {self.site_id}, Miners: {len(self.miners)}")
        logger.info(f"Collection interval: {self.collection_interval}s, Workers: {self.max_workers}")
        
        while self.running:
            try:
                result = self.run_once()
                logger.info(f"Collection cycle complete: {result}")
                
                time.sleep(self.collection_interval)
                
            except KeyboardInterrupt:
                logger.info("Collector stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"Collection cycle error: {e}")
                time.sleep(10)
    
    def stop(self):
        """停止采集器"""
        self.running = False


def generate_miner_list(ip_range: str, id_prefix: str = "miner") -> List[Dict]:
    """从IP范围生成矿机列表
    
    示例: generate_miner_list("192.168.1.100-192.168.1.200", "S19_")
    """
    miners = []
    
    parts = ip_range.split('-')
    if len(parts) != 2:
        return miners
    
    start_ip = parts[0].strip()
    end_ip = parts[1].strip()
    
    start_parts = list(map(int, start_ip.split('.')))
    end_parts = list(map(int, end_ip.split('.')))
    
    current = start_parts.copy()
    index = 1
    
    while current <= end_parts:
        ip = '.'.join(map(str, current))
        miners.append({
            'id': f"{id_prefix}{index:04d}",
            'ip': ip,
            'port': 4028,
            'type': 'antminer'
        })
        index += 1
        
        current[3] += 1
        for i in range(3, 0, -1):
            if current[i] > 255:
                current[i] = 0
                current[i-1] += 1
    
    return miners


def load_config(config_path: str) -> Dict:
    """加载配置文件"""
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def create_sample_config(output_path: str = "collector_config.json"):
    """创建示例配置文件"""
    config = {
        "api_url": "https://your-replit-app.replit.app",
        "api_key": "your-collector-api-key",
        "site_id": "site_001",
        "collection_interval": 30,
        "max_workers": 50,
        "cache_dir": "./cache",
        "miners": [
            {"id": "S19_0001", "ip": "192.168.1.100", "port": 4028, "type": "antminer"},
            {"id": "S19_0002", "ip": "192.168.1.101", "port": 4028, "type": "antminer"},
            {"id": "M30_0001", "ip": "192.168.2.100", "port": 4028, "type": "whatsminer"}
        ],
        "ip_ranges": [
            {"range": "192.168.1.100-192.168.1.199", "prefix": "S19_", "type": "antminer"},
            {"range": "192.168.2.100-192.168.2.199", "prefix": "M30_", "type": "whatsminer"}
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Sample config created: {output_path}")
    return config


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='HashInsight Edge Collector')
    parser.add_argument('-c', '--config', default='collector_config.json', help='Config file path')
    parser.add_argument('--init', action='store_true', help='Create sample config file')
    parser.add_argument('--test', help='Test connection to a single miner IP')
    parser.add_argument('--once', action='store_true', help='Run single collection cycle')
    
    args = parser.parse_args()
    
    if args.init:
        create_sample_config()
        exit(0)
    
    if args.test:
        print(f"Testing connection to {args.test}...")
        api = CGMinerAPI(args.test)
        summary = api.get_summary()
        if summary:
            print("Connection successful!")
            print(json.dumps(summary, indent=2))
        else:
            print("Connection failed!")
        exit(0)
    
    config = load_config(args.config)
    if not config:
        print(f"Config file not found: {args.config}")
        print("Run with --init to create a sample config")
        exit(1)
    
    if config.get('ip_ranges'):
        for ip_range in config['ip_ranges']:
            miners = generate_miner_list(
                ip_range['range'],
                ip_range.get('prefix', 'miner_')
            )
            for m in miners:
                m['type'] = ip_range.get('type', 'antminer')
            config.setdefault('miners', []).extend(miners)
    
    collector = EdgeCollector(config)
    
    if args.once:
        result = collector.run_once()
        print(json.dumps(result, indent=2))
    else:
        collector.run()
