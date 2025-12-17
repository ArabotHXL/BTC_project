#!/usr/bin/env python3
"""
HashInsight Enterprise - Secure Miner Agent
安全矿机数据采集代理

功能:
- E2E加密凭证解密 (PBKDF2-SHA256 + AES-GCM-256)
- CGMiner API 安全数据采集
- 实时遥测数据上报
- 明文数据即用即清

安全特性:
- 主密码本地输入，永不上传
- 凭证解密仅在本地进行
- 每次使用后清除明文数据
- 日志中不记录任何敏感信息

版本: 1.0.0
作者: HashInsight Team
"""

import json
import socket
import time
import logging
import requests
import sys
import os
import base64
import hashlib
import getpass
import gc
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("错误: 请安装 cryptography 库: pip install cryptography")
    sys.exit(1)

VERSION = "1.0.0"
CRYPTO_VERSION = 1
KDF_ALGORITHM = "PBKDF2-SHA256"
ENCRYPTION_ALGORITHM = "AES-GCM"
DEFAULT_ITERATIONS = 100000
KEY_LENGTH = 32

CGMINER_API_PORT = 4028
CGMINER_TIMEOUT = 5
COLLECTION_INTERVAL = 60
HEARTBEAT_INTERVAL = 30

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('secure_miner_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('SecureMinerAgent')


@dataclass
class DecryptedCredentials:
    ip: str = ""
    api_port: int = 4028
    ssh_port: int = 22
    ssh_user: str = ""
    ssh_password: str = ""
    api_key: str = ""
    pool_password: str = ""
    encrypted_at: str = ""
    
    def clear(self):
        self.ip = ""
        self.api_port = 4028
        self.ssh_port = 22
        self.ssh_user = ""
        self.ssh_password = ""
        self.api_key = ""
        self.pool_password = ""
        self.encrypted_at = ""
        gc.collect()


class SecureCredentialsDecryptor:
    
    def __init__(self, master_passphrase: str):
        if not master_passphrase or len(master_passphrase) < 8:
            raise ValueError("主密码必须至少8个字符")
        self._passphrase = master_passphrase
        logger.info("凭证解密器初始化完成")
    
    def _derive_key(self, salt: bytes, iterations: int) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        return kdf.derive(self._passphrase.encode('utf-8'))
    
    def decrypt(self, encrypted_json: str) -> DecryptedCredentials:
        try:
            encrypted_block = json.loads(encrypted_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的加密数据格式: {e}")
        
        if encrypted_block.get('v') != CRYPTO_VERSION:
            raise ValueError(f"不支持的加密版本: {encrypted_block.get('v')}")
        
        if encrypted_block.get('algo') != ENCRYPTION_ALGORITHM:
            raise ValueError(f"不支持的加密算法: {encrypted_block.get('algo')}")
        
        if encrypted_block.get('kdf') != KDF_ALGORITHM:
            raise ValueError(f"不支持的KDF算法: {encrypted_block.get('kdf')}")
        
        try:
            salt = base64.b64decode(encrypted_block['salt'])
            iv = base64.b64decode(encrypted_block['iv'])
            ciphertext = base64.b64decode(encrypted_block['ciphertext'])
            iterations = encrypted_block.get('iterations', DEFAULT_ITERATIONS)
        except (KeyError, Exception) as e:
            raise ValueError(f"加密数据结构不完整: {e}")
        
        key = self._derive_key(salt, iterations)
        
        try:
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, ciphertext, None)
            
            credentials_dict = json.loads(plaintext.decode('utf-8'))
            
            credentials = DecryptedCredentials(
                ip=credentials_dict.get('ip', ''),
                api_port=int(credentials_dict.get('api_port', 4028)),
                ssh_port=int(credentials_dict.get('ssh_port', 22)),
                ssh_user=credentials_dict.get('ssh_user', ''),
                ssh_password=credentials_dict.get('ssh_password', ''),
                api_key=credentials_dict.get('api_key', ''),
                pool_password=credentials_dict.get('pool_password', ''),
                encrypted_at=credentials_dict.get('encrypted_at', '')
            )
            
            del plaintext
            del credentials_dict
            gc.collect()
            
            logger.info("凭证解密成功")
            return credentials
            
        except Exception as e:
            raise ValueError(f"解密失败：密码错误或数据损坏 - {type(e).__name__}")
    
    def clear(self):
        self._passphrase = ""
        gc.collect()


class SecureCGMinerClient:
    
    def __init__(self, credentials: DecryptedCredentials):
        self._ip = credentials.ip
        self._port = credentials.api_port
        self._api_key = credentials.api_key
        self._timeout = CGMINER_TIMEOUT
        
        logger.info(f"CGMiner客户端初始化 (端口: {self._port})")
    
    def _send_command(self, command: str, params: Optional[Dict] = None) -> Optional[Dict]:
        try:
            request = {"command": command}
            if params:
                request.update(params)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((self._ip, self._port))
            
            sock.sendall(json.dumps(request).encode('utf-8'))
            
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            
            sock.close()
            
            if response:
                response_str = response.decode('utf-8').rstrip('\x00')
                return json.loads(response_str)
            
            return None
            
        except socket.timeout:
            logger.warning("连接超时")
            return None
        except socket.error as e:
            logger.warning(f"Socket错误: {type(e).__name__}")
            return None
        except json.JSONDecodeError:
            logger.error("JSON解析失败")
            return None
        except Exception as e:
            logger.error(f"查询错误: {type(e).__name__}")
            return None
    
    def get_summary(self) -> Optional[Dict]:
        return self._send_command('summary')
    
    def get_stats(self) -> Optional[Dict]:
        return self._send_command('stats')
    
    def get_pools(self) -> Optional[Dict]:
        return self._send_command('pools')
    
    def get_devs(self) -> Optional[Dict]:
        return self._send_command('devs')
    
    def get_config(self) -> Optional[Dict]:
        return self._send_command('config')
    
    def collect_metrics(self) -> Dict[str, Any]:
        metrics = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'online': False,
            'hashrate_5s': 0.0,
            'hashrate_1m': 0.0,
            'hashrate_5m': 0.0,
            'hashrate_15m': 0.0,
            'temperature_avg': 0.0,
            'temperature_max': 0.0,
            'temperatures': [],
            'fan_speeds': [],
            'fan_avg': 0,
            'power_w': 0,
            'accepted_shares': 0,
            'rejected_shares': 0,
            'hardware_errors': 0,
            'reject_rate': 0.0,
            'uptime_seconds': 0,
            'pool_url': '',
            'pool_worker': '',
            'error_flags': []
        }
        
        summary = self.get_summary()
        if summary and 'SUMMARY' in summary:
            s = summary['SUMMARY'][0] if summary['SUMMARY'] else {}
            metrics['online'] = True
            metrics['hashrate_5s'] = s.get('GHS 5s', 0) / 1000
            metrics['hashrate_1m'] = s.get('GHS av', 0) / 1000
            metrics['accepted_shares'] = s.get('Accepted', 0)
            metrics['rejected_shares'] = s.get('Rejected', 0)
            metrics['hardware_errors'] = s.get('Hardware Errors', 0)
            metrics['uptime_seconds'] = s.get('Elapsed', 0)
            
            total = metrics['accepted_shares'] + metrics['rejected_shares']
            if total > 0:
                metrics['reject_rate'] = (metrics['rejected_shares'] / total) * 100
        
        stats = self.get_stats()
        if stats and 'STATS' in stats:
            temps = []
            fans = []
            for stat in stats['STATS']:
                for key, value in stat.items():
                    if key.startswith('temp') and isinstance(value, (int, float)) and value > 0:
                        temps.append(value)
                    elif key.startswith('fan') and isinstance(value, (int, float)) and value > 0:
                        fans.append(int(value))
                
                if 'GHS 5m' in stat:
                    metrics['hashrate_5m'] = stat['GHS 5m'] / 1000
                if 'GHS 15m' in stat:
                    metrics['hashrate_15m'] = stat['GHS 15m'] / 1000
                if 'Power' in stat:
                    metrics['power_w'] = stat['Power']
            
            if temps:
                metrics['temperatures'] = temps
                metrics['temperature_avg'] = sum(temps) / len(temps)
                metrics['temperature_max'] = max(temps)
            
            if fans:
                metrics['fan_speeds'] = fans
                metrics['fan_avg'] = sum(fans) // len(fans)
        
        pools = self.get_pools()
        if pools and 'POOLS' in pools:
            for pool in pools['POOLS']:
                if pool.get('Status') == 'Alive':
                    metrics['pool_url'] = pool.get('URL', '')
                    metrics['pool_worker'] = pool.get('User', '')
                    break
        
        if metrics['temperature_max'] > 85:
            metrics['error_flags'].append('HIGH_TEMP')
        if metrics['fan_avg'] == 0 and metrics['online']:
            metrics['error_flags'].append('FAN_STOPPED')
        if metrics['reject_rate'] > 5:
            metrics['error_flags'].append('HIGH_REJECT_RATE')
        if metrics['hardware_errors'] > 100:
            metrics['error_flags'].append('HIGH_HW_ERRORS')
        
        return metrics
    
    def clear(self):
        self._ip = ""
        self._api_key = ""
        gc.collect()


class SecureMinerAgent:
    
    def __init__(self, api_base_url: str, agent_id: str, agent_token: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.agent_id = agent_id
        self.agent_token = agent_token
        self.decryptor: Optional[SecureCredentialsDecryptor] = None
        self.running = False
        
        logger.info(f"安全矿机代理初始化 - Agent ID: {agent_id}")
    
    def initialize_decryptor(self) -> bool:
        print("\n" + "="*60)
        print("HashInsight Enterprise - 安全矿机代理")
        print("="*60)
        print("\n请输入主密码来解密矿机凭证。")
        print("此密码仅在本地使用，不会上传到服务器。\n")
        
        try:
            passphrase = getpass.getpass("主密码 (Master Passphrase): ")
            
            if not passphrase or len(passphrase) < 8:
                print("错误: 主密码必须至少8个字符")
                return False
            
            self.decryptor = SecureCredentialsDecryptor(passphrase)
            
            del passphrase
            gc.collect()
            
            print("✓ 解密器初始化成功\n")
            return True
            
        except KeyboardInterrupt:
            print("\n操作已取消")
            return False
        except Exception as e:
            logger.error(f"初始化解密器失败: {type(e).__name__}")
            return False
    
    def fetch_encrypted_miners(self) -> List[Dict]:
        try:
            url = f"{self.api_base_url}/api/agents/{self.agent_id}/miners"
            headers = {
                'Authorization': f'Bearer {self.agent_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            miners = data.get('miners', [])
            
            logger.info(f"获取到 {len(miners)} 台矿机配置")
            return miners
            
        except requests.RequestException as e:
            logger.error(f"获取矿机列表失败: {type(e).__name__}")
            return []
    
    def upload_metrics(self, miner_id: int, metrics: Dict) -> bool:
        try:
            url = f"{self.api_base_url}/api/agents/{self.agent_id}/metrics"
            headers = {
                'Authorization': f'Bearer {self.agent_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'miner_id': miner_id,
                'metrics': metrics
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"矿机 {miner_id} 指标上报成功")
            return True
            
        except requests.RequestException as e:
            logger.error(f"上报指标失败: {type(e).__name__}")
            return False
    
    def collect_single_miner(self, miner_config: Dict) -> Optional[Dict]:
        miner_id = miner_config.get('id')
        encrypted_credentials = miner_config.get('encrypted_credentials')
        
        if not encrypted_credentials:
            logger.warning(f"矿机 {miner_id} 没有加密凭证")
            return None
        
        credentials = None
        client = None
        
        try:
            credentials = self.decryptor.decrypt(encrypted_credentials)
            
            client = SecureCGMinerClient(credentials)
            
            metrics = client.collect_metrics()
            
            logger.info(f"矿机 {miner_id} 数据采集完成 - 在线: {metrics['online']}")
            
            return metrics
            
        except ValueError as e:
            logger.error(f"矿机 {miner_id} 凭证解密失败")
            return None
        except Exception as e:
            logger.error(f"矿机 {miner_id} 采集失败: {type(e).__name__}")
            return None
        finally:
            if credentials:
                credentials.clear()
            if client:
                client.clear()
            gc.collect()
    
    def run_collection_cycle(self) -> Dict[str, Any]:
        results = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'total_miners': 0,
            'successful': 0,
            'failed': 0,
            'uploaded': 0
        }
        
        miners = self.fetch_encrypted_miners()
        results['total_miners'] = len(miners)
        
        for miner_config in miners:
            miner_id = miner_config.get('id')
            
            metrics = self.collect_single_miner(miner_config)
            
            if metrics:
                results['successful'] += 1
                
                if self.upload_metrics(miner_id, metrics):
                    results['uploaded'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"采集周期完成 - 成功: {results['successful']}/{results['total_miners']}, 上报: {results['uploaded']}")
        
        return results
    
    def start(self, interval: int = COLLECTION_INTERVAL):
        if not self.decryptor:
            if not self.initialize_decryptor():
                logger.error("无法启动代理: 解密器初始化失败")
                return
        
        self.running = True
        logger.info(f"代理启动 - 采集间隔: {interval}秒")
        
        try:
            while self.running:
                try:
                    self.run_collection_cycle()
                except Exception as e:
                    logger.error(f"采集周期异常: {type(e).__name__}")
                
                logger.info(f"等待 {interval} 秒后进行下一轮采集...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        
        if self.decryptor:
            self.decryptor.clear()
            self.decryptor = None
        
        gc.collect()
        logger.info("代理已停止，敏感数据已清除")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='HashInsight 安全矿机代理',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--api-url',
        default=os.environ.get('HASHINSIGHT_API_URL', 'http://localhost:5000'),
        help='HashInsight API 基础URL'
    )
    parser.add_argument(
        '--agent-id',
        default=os.environ.get('AGENT_ID'),
        help='代理ID'
    )
    parser.add_argument(
        '--agent-token',
        default=os.environ.get('AGENT_TOKEN'),
        help='代理认证令牌'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=int(os.environ.get('COLLECTION_INTERVAL', COLLECTION_INTERVAL)),
        help=f'采集间隔（秒），默认 {COLLECTION_INTERVAL}'
    )
    parser.add_argument(
        '--test-decrypt',
        metavar='JSON_FILE',
        help='测试解密加密凭证文件'
    )
    
    args = parser.parse_args()
    
    if args.test_decrypt:
        print("\n测试凭证解密...\n")
        try:
            with open(args.test_decrypt, 'r') as f:
                encrypted_json = f.read()
            
            passphrase = getpass.getpass("主密码: ")
            decryptor = SecureCredentialsDecryptor(passphrase)
            
            credentials = decryptor.decrypt(encrypted_json)
            
            print("\n✓ 解密成功!")
            print(f"  - IP: {credentials.ip}")
            print(f"  - API端口: {credentials.api_port}")
            print(f"  - SSH用户: {credentials.ssh_user or '(未设置)'}")
            print(f"  - 加密时间: {credentials.encrypted_at}")
            
            credentials.clear()
            decryptor.clear()
            del passphrase
            gc.collect()
            
            print("\n✓ 敏感数据已清除")
            
        except Exception as e:
            print(f"\n✗ 解密失败: {e}")
            sys.exit(1)
        
        return
    
    if not args.agent_id or not args.agent_token:
        parser.error("需要提供 --agent-id 和 --agent-token (或设置环境变量)")
    
    agent = SecureMinerAgent(
        api_base_url=args.api_url,
        agent_id=args.agent_id,
        agent_token=args.agent_token
    )
    
    agent.start(interval=args.interval)


if __name__ == '__main__':
    main()
