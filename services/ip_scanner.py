"""
HashInsight Enterprise - IP Scanner Service
IP扫描自动发现矿机服务

Features:
- IP range parsing (start-end or CIDR format)
- Concurrent scanning with thread pool
- Miner type identification (Antminer, Whatsminer, BraiinsOS, etc.)
- Progress tracking for async operations
- Batch registration support

Usage:
    from services.ip_scanner import IPScanner
    
    scanner = IPScanner()
    results = scanner.scan_range("192.168.1.1", "192.168.1.254")
"""

import socket
import logging
import ipaddress
import requests
import json
import time
import hashlib
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from enum import Enum

from services.cgminer_client import CGMinerClient, quick_probe, CGMinerError

logger = logging.getLogger('IPScanner')


class MinerType(Enum):
    ANTMINER = "antminer"
    WHATSMINER = "whatsminer"
    AVALON = "avalon"
    BRAIINS = "braiins"
    VNISH = "vnish"
    LUXOS = "luxos"
    UNKNOWN = "unknown"


@dataclass
class DiscoveredMiner:
    """Discovered miner data structure"""
    ip_address: str
    port: int
    miner_type: str
    model: str
    firmware: str
    hashrate_ths: float
    temperature: float
    online: bool
    mac_address: str
    worker: str
    pool_url: str
    uptime_hours: float
    latency_ms: float
    scan_time: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScanProgress:
    """Scan progress tracking"""
    scan_id: str
    site_id: int
    total_ips: int
    scanned_ips: int
    discovered_miners: int
    status: str  # pending, scanning, completed, failed
    start_time: str
    end_time: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_ips == 0:
            return 0
        return round(self.scanned_ips / self.total_ips * 100, 1)


class IPScanner:
    """
    IP Scanner for discovering miners in a network range
    """
    
    CGMINER_PORT = 4028
    HTTP_PORTS = [80, 443, 8080]
    DEFAULT_TIMEOUT = 3.0
    MAX_WORKERS = 50
    
    # Known miner signatures for identification
    MINER_SIGNATURES = {
        MinerType.ANTMINER: {
            'cgminer_type': ['Antminer', 'bmminer'],
            'http_path': '/cgi-bin/get_system_info.cgi',
            'http_contains': ['Antminer', 'ANTMINER']
        },
        MinerType.WHATSMINER: {
            'cgminer_type': ['btminer', 'Whatsminer'],
            'http_path': '/api/v1/status',
            'http_contains': ['Whatsminer', 'MicroBT']
        },
        MinerType.BRAIINS: {
            'cgminer_type': ['BOSminer', 'braiins'],
            'http_path': '/cgi-bin/luci',
            'http_contains': ['Braiins', 'BOSminer']
        },
        MinerType.VNISH: {
            'cgminer_type': ['vnish'],
            'http_path': '/api/info',
            'http_contains': ['vnish', 'Vnish']
        },
        MinerType.LUXOS: {
            'cgminer_type': ['LuxOS', 'luxminer'],
            'http_path': '/api/status',
            'http_contains': ['LuxOS', 'Luxor']
        }
    }
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT, max_workers: int = MAX_WORKERS):
        self.timeout = timeout
        self.max_workers = max_workers
        self._scan_sessions: Dict[str, ScanProgress] = {}
        self._scan_results: Dict[str, List[DiscoveredMiner]] = {}
        self._lock = threading.Lock()
    
    @staticmethod
    def parse_ip_range(start_ip: str, end_ip: str) -> List[str]:
        """
        Parse IP range and return list of IP addresses
        
        Args:
            start_ip: Starting IP address (e.g., "192.168.1.1")
            end_ip: Ending IP address (e.g., "192.168.1.254")
            
        Returns:
            List of IP addresses in the range
        """
        try:
            start = ipaddress.IPv4Address(start_ip.strip())
            end = ipaddress.IPv4Address(end_ip.strip())
            
            if start > end:
                start, end = end, start
            
            ip_list = []
            current = int(start)
            end_int = int(end)
            
            max_ips = 10000
            if end_int - current > max_ips:
                raise ValueError(f"IP range too large. Maximum {max_ips} IPs allowed.")
            
            while current <= end_int:
                ip_list.append(str(ipaddress.IPv4Address(current)))
                current += 1
            
            return ip_list
            
        except ipaddress.AddressValueError as e:
            raise ValueError(f"Invalid IP address: {e}")
    
    @staticmethod
    def parse_cidr(cidr: str) -> List[str]:
        """
        Parse CIDR notation and return list of IP addresses
        
        Args:
            cidr: CIDR notation (e.g., "192.168.1.0/24")
            
        Returns:
            List of IP addresses in the network
        """
        try:
            network = ipaddress.IPv4Network(cidr.strip(), strict=False)
            
            max_ips = 10000
            if network.num_addresses > max_ips:
                raise ValueError(f"Network too large. Maximum {max_ips} IPs allowed.")
            
            return [str(ip) for ip in network.hosts()]
            
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation: {e}")
    
    def generate_scan_id(self, site_id: int) -> str:
        """Generate unique scan ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = hashlib.md5(f"{site_id}{timestamp}{time.time()}".encode()).hexdigest()[:8]
        return f"scan_{site_id}_{timestamp}_{random_part}"
    
    def _probe_single_ip(self, ip: str, username: str = "root", password: str = "root") -> Optional[DiscoveredMiner]:
        """
        Probe a single IP for miner
        
        Args:
            ip: IP address to probe
            username: Auth username for HTTP API
            password: Auth password for HTTP API
            
        Returns:
            DiscoveredMiner if found, None otherwise
        """
        miner_info = {
            'ip_address': ip,
            'port': self.CGMINER_PORT,
            'miner_type': MinerType.UNKNOWN.value,
            'model': 'Unknown',
            'firmware': 'Unknown',
            'hashrate_ths': 0.0,
            'temperature': 0.0,
            'online': False,
            'mac_address': '',
            'worker': '',
            'pool_url': '',
            'uptime_hours': 0.0,
            'latency_ms': 0.0,
            'scan_time': datetime.utcnow().isoformat() + 'Z',
            'error': None
        }
        
        try:
            probe_result = quick_probe(ip, self.CGMINER_PORT, self.timeout)
            
            if probe_result['result'] == 'OK':
                miner_info['online'] = True
                miner_info['hashrate_ths'] = probe_result.get('hashrate_ghs', 0) / 1000
                miner_info['temperature'] = probe_result.get('temp_max', 0)
                miner_info['latency_ms'] = probe_result.get('latency_ms', 0)
                
                try:
                    client = CGMinerClient(ip, self.CGMINER_PORT, self.timeout, max_retries=1)
                    
                    version_info = client.get_version()
                    if 'VERSION' in version_info and version_info['VERSION']:
                        v = version_info['VERSION'][0]
                        miner_type = v.get('Type', v.get('Miner', ''))
                        miner_info['miner_type'] = self._identify_type_from_string(miner_type)
                        miner_info['model'] = miner_type
                        miner_info['firmware'] = v.get('CGMiner', v.get('API', 'Unknown'))
                    
                    stats = client.get_stats()
                    if 'STATS' in stats and stats['STATS']:
                        for stat in stats['STATS']:
                            if 'miner_id' in stat:
                                miner_info['mac_address'] = stat.get('miner_id', '')
                            if not miner_info['model'] or miner_info['model'] == 'Unknown':
                                type_str = stat.get('Type', stat.get('ID', ''))
                                if type_str:
                                    miner_info['model'] = type_str
                                    miner_info['miner_type'] = self._identify_type_from_string(type_str)
                    
                    pools = client.get_pools()
                    if 'POOLS' in pools and pools['POOLS']:
                        for pool in pools['POOLS']:
                            if pool.get('Status') == 'Alive' or pool.get('Stratum Active'):
                                miner_info['pool_url'] = pool.get('URL', '')
                                miner_info['worker'] = pool.get('User', '')
                                break
                    
                    summary = client.get_summary()
                    if 'SUMMARY' in summary and summary['SUMMARY']:
                        s = summary['SUMMARY'][0]
                        elapsed = s.get('Elapsed', 0)
                        miner_info['uptime_hours'] = elapsed / 3600 if elapsed else 0
                        
                except CGMinerError as e:
                    logger.debug(f"CGMiner details fetch failed for {ip}: {e}")
                
                if miner_info['miner_type'] == MinerType.UNKNOWN.value:
                    http_result = self._probe_http_api(ip, username, password)
                    if http_result:
                        miner_info.update(http_result)
                
                return DiscoveredMiner(**miner_info)
            
            else:
                http_result = self._probe_http_api(ip, username, password)
                if http_result and http_result.get('online'):
                    miner_info.update(http_result)
                    return DiscoveredMiner(**miner_info)
                
        except Exception as e:
            logger.debug(f"Probe failed for {ip}: {e}")
            miner_info['error'] = str(e)
        
        return None
    
    def _probe_http_api(self, ip: str, username: str = "root", password: str = "root") -> Optional[Dict]:
        """Try HTTP API endpoints to identify miner"""
        result = None
        
        for port in self.HTTP_PORTS:
            for miner_type, signatures in self.MINER_SIGNATURES.items():
                http_path = signatures.get('http_path', '')
                if not http_path:
                    continue
                
                url = f"http://{ip}:{port}{http_path}"
                
                try:
                    response = requests.get(
                        url,
                        auth=(username, password),
                        timeout=self.timeout,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        content = response.text
                        http_contains = signatures.get('http_contains', [])
                        
                        for keyword in http_contains:
                            if keyword.lower() in content.lower():
                                result = {
                                    'online': True,
                                    'miner_type': miner_type.value,
                                    'port': port
                                }
                                
                                try:
                                    data = response.json()
                                    if 'model' in data:
                                        result['model'] = data['model']
                                    if 'hashrate' in data:
                                        result['hashrate_ths'] = float(data['hashrate']) / 1000
                                except:
                                    pass
                                
                                return result
                                
                except requests.exceptions.RequestException:
                    continue
        
        return result
    
    def _identify_type_from_string(self, type_string: str) -> str:
        """Identify miner type from a type string"""
        if not type_string:
            return MinerType.UNKNOWN.value
        
        type_lower = type_string.lower()
        
        if any(x in type_lower for x in ['antminer', 'bmminer', 's19', 's21', 't19', 't21']):
            return MinerType.ANTMINER.value
        elif any(x in type_lower for x in ['whatsminer', 'btminer', 'm30', 'm50', 'm60']):
            return MinerType.WHATSMINER.value
        elif any(x in type_lower for x in ['avalon', 'canaan']):
            return MinerType.AVALON.value
        elif any(x in type_lower for x in ['braiins', 'bosminer', 'bos']):
            return MinerType.BRAIINS.value
        elif 'vnish' in type_lower:
            return MinerType.VNISH.value
        elif any(x in type_lower for x in ['luxos', 'luxor']):
            return MinerType.LUXOS.value
        
        return MinerType.UNKNOWN.value
    
    def scan_range(
        self,
        start_ip: str,
        end_ip: str,
        site_id: int,
        username: str = "root",
        password: str = "root",
        callback: Optional[Callable] = None
    ) -> Tuple[str, List[DiscoveredMiner]]:
        """
        Scan an IP range for miners (synchronous)
        
        Args:
            start_ip: Starting IP address
            end_ip: Ending IP address
            site_id: Site ID for registration
            username: Auth username
            password: Auth password
            callback: Optional progress callback function(scanned, total, discovered)
            
        Returns:
            Tuple of (scan_id, list of discovered miners)
        """
        ip_list = self.parse_ip_range(start_ip, end_ip)
        scan_id = self.generate_scan_id(site_id)
        
        progress = ScanProgress(
            scan_id=scan_id,
            site_id=site_id,
            total_ips=len(ip_list),
            scanned_ips=0,
            discovered_miners=0,
            status='scanning',
            start_time=datetime.utcnow().isoformat() + 'Z'
        )
        
        with self._lock:
            self._scan_sessions[scan_id] = progress
            self._scan_results[scan_id] = []
        
        discovered = []
        scanned = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ip = {
                executor.submit(self._probe_single_ip, ip, username, password): ip
                for ip in ip_list
            }
            
            for future in as_completed(future_to_ip):
                scanned += 1
                ip = future_to_ip[future]
                
                try:
                    result = future.result()
                    if result:
                        discovered.append(result)
                        logger.info(f"Discovered miner at {ip}: {result.model}")
                except Exception as e:
                    logger.debug(f"Scan failed for {ip}: {e}")
                
                with self._lock:
                    progress.scanned_ips = scanned
                    progress.discovered_miners = len(discovered)
                
                if callback:
                    try:
                        callback(scanned, len(ip_list), len(discovered))
                    except:
                        pass
        
        with self._lock:
            progress.status = 'completed'
            progress.end_time = datetime.utcnow().isoformat() + 'Z'
            self._scan_results[scan_id] = discovered
        
        return scan_id, discovered
    
    def scan_range_async(
        self,
        start_ip: str,
        end_ip: str,
        site_id: int,
        username: str = "root",
        password: str = "root"
    ) -> str:
        """
        Start async scan and return scan_id immediately
        
        Args:
            start_ip: Starting IP address
            end_ip: Ending IP address
            site_id: Site ID
            username: Auth username
            password: Auth password
            
        Returns:
            scan_id for tracking progress
        """
        ip_list = self.parse_ip_range(start_ip, end_ip)
        scan_id = self.generate_scan_id(site_id)
        
        progress = ScanProgress(
            scan_id=scan_id,
            site_id=site_id,
            total_ips=len(ip_list),
            scanned_ips=0,
            discovered_miners=0,
            status='pending',
            start_time=datetime.utcnow().isoformat() + 'Z'
        )
        
        with self._lock:
            self._scan_sessions[scan_id] = progress
            self._scan_results[scan_id] = []
        
        def run_scan():
            with self._lock:
                self._scan_sessions[scan_id].status = 'scanning'
            
            discovered = []
            scanned = 0
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_ip = {
                    executor.submit(self._probe_single_ip, ip, username, password): ip
                    for ip in ip_list
                }
                
                for future in as_completed(future_to_ip):
                    scanned += 1
                    
                    try:
                        result = future.result()
                        if result:
                            discovered.append(result)
                    except:
                        pass
                    
                    with self._lock:
                        self._scan_sessions[scan_id].scanned_ips = scanned
                        self._scan_sessions[scan_id].discovered_miners = len(discovered)
            
            with self._lock:
                self._scan_sessions[scan_id].status = 'completed'
                self._scan_sessions[scan_id].end_time = datetime.utcnow().isoformat() + 'Z'
                self._scan_results[scan_id] = discovered
        
        thread = threading.Thread(target=run_scan, daemon=True)
        thread.start()
        
        return scan_id
    
    def get_scan_progress(self, scan_id: str) -> Optional[Dict]:
        """Get scan progress"""
        with self._lock:
            progress = self._scan_sessions.get(scan_id)
            if progress:
                return {
                    'scan_id': progress.scan_id,
                    'site_id': progress.site_id,
                    'total_ips': progress.total_ips,
                    'scanned_ips': progress.scanned_ips,
                    'discovered_miners': progress.discovered_miners,
                    'progress_percent': progress.progress_percent,
                    'status': progress.status,
                    'start_time': progress.start_time,
                    'end_time': progress.end_time,
                    'error': progress.error
                }
        return None
    
    def get_scan_results(self, scan_id: str) -> Optional[List[Dict]]:
        """Get scan results"""
        with self._lock:
            results = self._scan_results.get(scan_id)
            if results:
                return [m.to_dict() for m in results]
        return None
    
    def cleanup_scan(self, scan_id: str):
        """Remove scan session from memory (any status)"""
        with self._lock:
            progress = self._scan_sessions.get(scan_id)
            if progress:
                self._scan_sessions.pop(scan_id, None)
                self._scan_results.pop(scan_id, None)
                return True
            return False


_scanner_instance: Optional[IPScanner] = None


def get_scanner() -> IPScanner:
    """Get singleton scanner instance"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = IPScanner()
    return _scanner_instance
