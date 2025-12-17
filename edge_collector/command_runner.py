"""
Edge Command Runner
边缘命令执行器

Polls cloud API for queued commands and executes them on miners.
Supports both real CGMiner and simulated mode for testing.

Usage:
    python -m edge_collector.command_runner --mode simulated --site-id 1

Environment:
    EDGE_DEVICE_ID: Device ID for this edge collector
    EDGE_SITE_ID: Default site ID
    EDGE_API_BASE_URL: Cloud API base URL
    EDGE_AUTH_TOKEN: Device authentication token
    EDGE_MINER_MODE: simulated|cgminer (default: simulated)
    EDGE_EXECUTION_ENABLED: true|false (default: true)
    EDGE_POLL_INTERVAL: Polling interval in seconds (default: 5)
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EdgeCommandRunner')

EDGE_DEVICE_ID = os.environ.get('EDGE_DEVICE_ID', 'edge-001')
EDGE_SITE_ID = os.environ.get('EDGE_SITE_ID', '1')
EDGE_API_BASE_URL = os.environ.get('EDGE_API_BASE_URL', 'http://localhost:5000')
EDGE_AUTH_TOKEN = os.environ.get('EDGE_AUTH_TOKEN', '')
EDGE_MINER_MODE = os.environ.get('EDGE_MINER_MODE', 'simulated')
EDGE_EXECUTION_ENABLED = os.environ.get('EDGE_EXECUTION_ENABLED', 'true').lower() == 'true'
EDGE_POLL_INTERVAL = int(os.environ.get('EDGE_POLL_INTERVAL', '5'))

EXECUTED_COMMANDS_FILE = Path('.edge_executed_commands.json')


class CommandDeduplicator:
    """Tracks executed commands to prevent double execution"""
    
    def __init__(self, storage_file: Path = EXECUTED_COMMANDS_FILE, max_entries: int = 1000):
        self.storage_file = storage_file
        self.max_entries = max_entries
        self._executed: Dict[str, str] = {}
        self._load()
    
    def _load(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    self._executed = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load executed commands: {e}")
                self._executed = {}
    
    def _save(self):
        try:
            if len(self._executed) > self.max_entries:
                sorted_cmds = sorted(self._executed.items(), key=lambda x: x[1])
                self._executed = dict(sorted_cmds[-self.max_entries:])
            
            with open(self.storage_file, 'w') as f:
                json.dump(self._executed, f)
        except Exception as e:
            logger.warning(f"Failed to save executed commands: {e}")
    
    def is_executed(self, command_id: str) -> bool:
        return command_id in self._executed
    
    def mark_executed(self, command_id: str):
        self._executed[command_id] = datetime.utcnow().isoformat()
        self._save()


class EdgeCommandRunner:
    """Main command runner for Edge device"""
    
    def __init__(self, 
                 api_base_url: str = EDGE_API_BASE_URL,
                 auth_token: str = EDGE_AUTH_TOKEN,
                 site_id: str = EDGE_SITE_ID,
                 device_id: str = EDGE_DEVICE_ID,
                 miner_mode: str = EDGE_MINER_MODE):
        self.api_base_url = api_base_url.rstrip('/')
        self.auth_token = auth_token
        self.site_id = site_id
        self.device_id = device_id
        self.miner_mode = miner_mode
        self.deduplicator = CommandDeduplicator()
        
        self._miner_ips: Dict[str, str] = {}
    
    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json',
            'X-Edge-Device-ID': self.device_id
        }
    
    def poll_commands(self) -> List[Dict[str, Any]]:
        """Poll cloud API for queued commands"""
        try:
            url = f"{self.api_base_url}/api/edge/v1/commands/poll"
            params = {'site_id': self.site_id, 'limit': 10}
            
            response = requests.get(url, headers=self._headers(), params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('commands', [])
            elif response.status_code == 401:
                logger.error("Authentication failed - check EDGE_AUTH_TOKEN")
            else:
                logger.warning(f"Poll failed: {response.status_code} - {response.text[:200]}")
            
        except requests.RequestException as e:
            logger.error(f"Network error polling commands: {e}")
        
        return []
    
    def ack_command(self, command_id: str, results: List[Dict[str, Any]]) -> bool:
        """Send command execution results back to cloud"""
        try:
            url = f"{self.api_base_url}/api/edge/v1/commands/{command_id}/ack"
            payload = {'results': results}
            
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Acknowledged command {command_id[:8]}")
                return True
            else:
                logger.warning(f"Ack failed: {response.status_code} - {response.text[:200]}")
            
        except requests.RequestException as e:
            logger.error(f"Network error acknowledging command: {e}")
        
        return False
    
    def _get_adapter(self, ip_address: str, credentials: Optional[Dict] = None):
        """Get appropriate adapter based on mode"""
        if self.miner_mode == 'simulated':
            from edge_collector.adapters import SimulatedAdapter
            return SimulatedAdapter(ip_address, credentials=credentials)
        else:
            from edge_collector.adapters import CGMinerAdapter
            return CGMinerAdapter(ip_address, credentials=credentials)
    
    def _resolve_miner_ip(self, miner_id: str) -> Optional[str]:
        """Resolve miner ID to IP address"""
        if miner_id in self._miner_ips:
            return self._miner_ips[miner_id]
        
        if self.miner_mode == 'simulated':
            fake_ip = f"192.168.1.{hash(miner_id) % 250 + 1}"
            self._miner_ips[miner_id] = fake_ip
            return fake_ip
        
        return None
    
    def execute_command(self, command: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a single command on all target miners"""
        command_id = command.get('command_id')
        command_type = command.get('command_type')
        payload = command.get('payload', {})
        target_ids = command.get('target_ids', [])
        encrypted_credentials = command.get('encrypted_credentials', {})
        
        logger.info(f"Executing {command_type} on {len(target_ids)} miners")
        
        results = []
        for miner_id in target_ids:
            miner_id_str = str(miner_id)
            
            ip_address = self._resolve_miner_ip(miner_id_str)
            if not ip_address:
                results.append({
                    'miner_id': miner_id_str,
                    'status': 'FAILED',
                    'message': 'Could not resolve miner IP address'
                })
                continue
            
            credentials = None
            if miner_id_str in encrypted_credentials:
                credentials = self._decrypt_credentials(encrypted_credentials[miner_id_str])
            
            try:
                adapter = self._get_adapter(ip_address, credentials)
                result = adapter.execute(command_type, payload)
                
                results.append({
                    'miner_id': miner_id_str,
                    **result.to_dict()
                })
                
                logger.info(f"  {miner_id_str}: {'SUCCESS' if result.success else 'FAILED'} - {result.message}")
                
            except Exception as e:
                logger.error(f"  {miner_id_str}: ERROR - {e}")
                results.append({
                    'miner_id': miner_id_str,
                    'status': 'FAILED',
                    'message': str(e)
                })
        
        return results
    
    def _decrypt_credentials(self, encrypted_cred: Dict[str, Any]) -> Optional[Dict]:
        """Decrypt credentials using device private key"""
        try:
            from edge_collector.crypto_e2ee import decrypt_envelope
            
            decrypted = decrypt_envelope(
                encrypted_payload=encrypted_cred.get('encrypted_payload'),
                wrapped_dek=encrypted_cred.get('wrapped_dek'),
                nonce=encrypted_cred.get('nonce')
            )
            return decrypted
        except Exception as e:
            logger.warning(f"Failed to decrypt credentials: {e}")
            return None
    
    def run_once(self) -> int:
        """Poll and execute commands once, return number of commands processed"""
        if not EDGE_EXECUTION_ENABLED:
            logger.debug("Execution disabled, skipping poll")
            return 0
        
        commands = self.poll_commands()
        processed = 0
        
        for command in commands:
            command_id = command.get('command_id')
            
            if self.deduplicator.is_executed(command_id):
                logger.debug(f"Skipping already executed command {command_id[:8]}")
                continue
            
            results = self.execute_command(command)
            
            if self.ack_command(command_id, results):
                self.deduplicator.mark_executed(command_id)
                processed += 1
        
        return processed
    
    def run_forever(self, poll_interval: int = EDGE_POLL_INTERVAL):
        """Run continuous polling loop"""
        logger.info(f"Starting Edge Command Runner")
        logger.info(f"  Device ID: {self.device_id}")
        logger.info(f"  Site ID: {self.site_id}")
        logger.info(f"  API URL: {self.api_base_url}")
        logger.info(f"  Mode: {self.miner_mode}")
        logger.info(f"  Poll interval: {poll_interval}s")
        
        while True:
            try:
                processed = self.run_once()
                if processed > 0:
                    logger.info(f"Processed {processed} commands")
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            
            time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description='Edge Command Runner')
    parser.add_argument('--mode', choices=['simulated', 'cgminer'], default=EDGE_MINER_MODE,
                       help='Miner control mode')
    parser.add_argument('--site-id', default=EDGE_SITE_ID, help='Site ID')
    parser.add_argument('--api-url', default=EDGE_API_BASE_URL, help='Cloud API base URL')
    parser.add_argument('--token', default=EDGE_AUTH_TOKEN, help='Device auth token')
    parser.add_argument('--poll-interval', type=int, default=EDGE_POLL_INTERVAL,
                       help='Polling interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    runner = EdgeCommandRunner(
        api_base_url=args.api_url,
        auth_token=args.token,
        site_id=args.site_id,
        miner_mode=args.mode
    )
    
    if args.once:
        processed = runner.run_once()
        sys.exit(0 if processed >= 0 else 1)
    else:
        runner.run_forever(poll_interval=args.poll_interval)


if __name__ == '__main__':
    main()
