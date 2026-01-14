"""
HashInsight Enterprise - Hardened CGMiner TCP Client
安全加固的CGMiner TCP客户端

Features:
- Safe TCP connection with strict timeouts
- Automatic retry with exponential backoff
- Robust response parsing (handles CGMiner quirks)
- Normalized telemetry output
- Command whitelist for security
- Defensive error handling

Usage:
    from services.cgminer_client import CGMinerClient, get_normalized_telemetry
    
    client = CGMinerClient("192.168.1.100")
    telemetry = get_normalized_telemetry(client)
"""

import socket
import json
import time
import logging
import re
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger('CGMinerClient')

ALLOWED_COMMANDS = frozenset({
    'summary', 'stats', 'pools', 'devs', 'version', 'config',
    'coin', 'usbstats', 'lcd', 'check', 'asc', 'asccount'
})

CONTROL_COMMANDS = frozenset({
    'enable', 'disable', 'restart', 'addpool', 'removepool',
    'switchpool', 'setconfig', 'fanctrl', 'asclock', 'ascunlock'
})


class CGMinerError(Exception):
    """CGMiner communication error with structured details"""
    
    def __init__(self, message: str, host: str = "", port: int = 4028, 
                 error_type: str = "unknown", latency_ms: float = 0):
        self.message = message
        self.host = host
        self.port = port
        self.error_type = error_type
        self.latency_ms = latency_ms
        self.timestamp = datetime.utcnow()
        super().__init__(f"[{error_type}] {message} (host={host}:{port})")


class CGMinerClient:
    """
    Hardened CGMiner API TCP Client
    
    Security features:
    - Command whitelist validation
    - Strict connection timeouts
    - Automatic retry with backoff
    - Safe response parsing
    """
    
    DEFAULT_PORT = 4028
    DEFAULT_TIMEOUT = 5.0
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 0.5
    MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB limit
    
    def __init__(self, host: str, port: int = DEFAULT_PORT, 
                 timeout: float = DEFAULT_TIMEOUT,
                 max_retries: int = MAX_RETRIES,
                 allow_control: bool = False):
        """
        Initialize CGMiner client
        
        Args:
            host: Miner IP address (validated)
            port: CGMiner API port (default 4028)
            timeout: Connection timeout in seconds
            max_retries: Maximum retry attempts
            allow_control: Allow control commands (default False for safety)
        """
        self.host = self._validate_host(host)
        self.port = self._validate_port(port)
        self.timeout = min(timeout, 30.0)
        self.max_retries = min(max_retries, 5)
        self.allow_control = allow_control
        self._last_latency_ms: float = 0.0
        self._last_response_time: Optional[datetime] = None
    
    @staticmethod
    def _validate_host(host: str) -> str:
        """Validate and sanitize host input"""
        if not host or not isinstance(host, str):
            raise ValueError("Host must be a non-empty string")
        
        host = host.strip()
        
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        
        if re.match(ip_pattern, host):
            octets = host.split('.')
            if all(0 <= int(o) <= 255 for o in octets):
                return host
            raise ValueError(f"Invalid IP address: {host}")
        
        if re.match(hostname_pattern, host) and len(host) <= 253:
            return host
        
        raise ValueError(f"Invalid host format: {host}")
    
    @staticmethod
    def _validate_port(port: int) -> int:
        """Validate port number"""
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"Port must be between 1-65535, got: {port}")
        return port
    
    @property
    def last_latency_ms(self) -> float:
        """Last request latency in milliseconds"""
        return self._last_latency_ms
    
    @property
    def last_response_time(self) -> Optional[datetime]:
        """Timestamp of last successful response"""
        return self._last_response_time
    
    def send_command(self, command: str, parameter: str = "") -> Dict[str, Any]:
        """
        Send CGMiner command with retry
        
        Args:
            command: Command name (must be in whitelist)
            parameter: Optional command parameter
            
        Returns:
            Parsed JSON response
            
        Raises:
            CGMinerError: On communication failure
            ValueError: On invalid command
        """
        command = command.lower().strip()
        
        if command in CONTROL_COMMANDS:
            if not self.allow_control:
                raise ValueError(f"Control command '{command}' not allowed. Set allow_control=True")
        elif command not in ALLOWED_COMMANDS:
            raise ValueError(f"Unknown command '{command}'. Allowed: {ALLOWED_COMMANDS}")
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return self._send_once(command, parameter)
            except CGMinerError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.RETRY_BACKOFF_BASE * (2 ** attempt)
                    wait_time += wait_time * 0.1 * (hash(self.host) % 10) / 10
                    logger.debug(f"Retry {attempt + 1}/{self.max_retries} after {wait_time:.2f}s: {e.message}")
                    time.sleep(wait_time)
        
        raise last_error or CGMinerError("Unknown error", self.host, self.port, "unknown")
    
    def _send_once(self, command: str, parameter: str = "") -> Dict[str, Any]:
        """Single command send without retry"""
        sock = None
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            request = json.dumps({"command": command, "parameter": parameter})
            sock.sendall(request.encode('utf-8'))
            
            response = b''
            while len(response) < self.MAX_RESPONSE_SIZE:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b'\x00' in chunk:
                        break
                except socket.timeout:
                    if response:
                        break
                    raise
            
            self._last_latency_ms = (time.time() - start_time) * 1000
            self._last_response_time = datetime.utcnow()
            
            return self._parse_response(response)
                
        except socket.timeout:
            latency = (time.time() - start_time) * 1000
            raise CGMinerError(
                f"Connection timeout ({self.timeout}s)",
                self.host, self.port, "timeout", latency
            )
        except ConnectionRefusedError:
            raise CGMinerError(
                "Connection refused - miner may be offline or API disabled",
                self.host, self.port, "connection"
            )
        except socket.gaierror as e:
            raise CGMinerError(
                f"DNS resolution failed: {e}",
                self.host, self.port, "dns"
            )
        except OSError as e:
            raise CGMinerError(
                f"Network error: {str(e)}",
                self.host, self.port, "connection"
            )
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
    
    def _parse_response(self, raw: bytes) -> Dict[str, Any]:
        """
        Parse CGMiner response with quirk handling
        
        CGMiner quirks handled:
        - Trailing null bytes
        - Missing commas in some firmware
        - Nested JSON fragments
        """
        try:
            data = raw.rstrip(b'\x00').decode('utf-8', errors='replace')
            data = data.strip()
            
            if not data:
                raise CGMinerError("Empty response", self.host, self.port, "parse")
            
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                pass
            
            data = re.sub(r'}\s*{', '},{', data)
            data = re.sub(r']\s*\[', '],[', data)
            
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                pass
            
            if not data.startswith('{'):
                data = '{' + data
            if not data.endswith('}'):
                data = data + '}'
            
            return json.loads(data)
            
        except json.JSONDecodeError as e:
            preview = raw[:200].decode('utf-8', errors='replace')
            raise CGMinerError(
                f"Invalid JSON response: {str(e)[:50]}... Preview: {preview[:100]}",
                self.host, self.port, "parse"
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get miner summary info"""
        return self.send_command("summary")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detailed stats (temperature, chips, etc.)"""
        return self.send_command("stats")
    
    def get_pools(self) -> Dict[str, Any]:
        """Get pool configuration"""
        return self.send_command("pools")
    
    def get_devs(self) -> Dict[str, Any]:
        """Get device info"""
        return self.send_command("devs")
    
    def get_version(self) -> Dict[str, Any]:
        """Get firmware version"""
        return self.send_command("version")
    
    def is_alive(self) -> Tuple[bool, float]:
        """
        Quick connectivity check
        
        Returns:
            (is_alive, latency_ms)
        """
        try:
            self.get_version()
            return True, self._last_latency_ms
        except CGMinerError:
            return False, 0.0


def get_normalized_telemetry(client: CGMinerClient) -> Dict[str, Any]:
    """
    Get normalized telemetry from a miner
    
    Returns standardized dict with:
    - hashrate_5s: Current hashrate (GH/s)
    - hashrate_avg: Average hashrate (GH/s)
    - uptime: Uptime in seconds
    - accepted: Accepted shares
    - rejected: Rejected shares
    - temp_avg: Average temperature (C)
    - temp_max: Maximum temperature (C)
    - fan_speeds: List of fan speeds (RPM)
    - pool_url: Current pool URL
    - worker: Worker name
    - status: online/offline/error
    - as_of: ISO timestamp
    - latency_ms: Response latency
    """
    result = {
        "hashrate_5s": 0.0,
        "hashrate_avg": 0.0,
        "uptime": 0,
        "accepted": 0,
        "rejected": 0,
        "temp_avg": 0.0,
        "temp_max": 0.0,
        "fan_speeds": [],
        "pool_url": "",
        "worker": "",
        "status": "offline",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "latency_ms": 0.0,
        "error": None
    }
    
    try:
        summary = client.get_summary()
        result["latency_ms"] = client.last_latency_ms
        
        if "SUMMARY" in summary and summary["SUMMARY"]:
            s = summary["SUMMARY"][0]
            result["hashrate_5s"] = s.get("GHS 5s", s.get("MHS 5s", 0) / 1000)
            result["hashrate_avg"] = s.get("GHS av", s.get("MHS av", 0) / 1000)
            result["uptime"] = s.get("Elapsed", 0)
            result["accepted"] = s.get("Accepted", 0)
            result["rejected"] = s.get("Rejected", 0)
            result["status"] = "online"
        
        try:
            stats = client.get_stats()
            if "STATS" in stats:
                temps = []
                fans = []
                for stat in stats["STATS"]:
                    for key, value in stat.items():
                        if "temp" in key.lower() and isinstance(value, (int, float)) and value > 0:
                            temps.append(value)
                        if "fan" in key.lower() and isinstance(value, (int, float)) and value > 0:
                            fans.append(int(value))
                
                if temps:
                    result["temp_avg"] = sum(temps) / len(temps)
                    result["temp_max"] = max(temps)
                if fans:
                    result["fan_speeds"] = fans
        except CGMinerError:
            pass
        
        try:
            pools = client.get_pools()
            if "POOLS" in pools and pools["POOLS"]:
                active_pool = None
                for pool in pools["POOLS"]:
                    if pool.get("Status") == "Alive" and pool.get("Stratum Active"):
                        active_pool = pool
                        break
                if not active_pool:
                    active_pool = pools["POOLS"][0]
                
                result["pool_url"] = active_pool.get("URL", "")
                result["worker"] = active_pool.get("User", "")
        except CGMinerError:
            pass
        
        result["as_of"] = client.last_response_time.isoformat() + "Z" if client.last_response_time else result["as_of"]
        
    except CGMinerError as e:
        result["status"] = "error"
        result["error"] = str(e.message)
    
    return result


def quick_probe(host: str, port: int = 4028, timeout: float = 2.0) -> Dict[str, Any]:
    """
    Quick probe for CLI and health checks
    
    Returns:
        {
            "result": "OK" | "FAIL",
            "host": str,
            "port": int,
            "latency_ms": float,
            "hashrate_ghs": float,
            "temp_max": float,
            "status": str,
            "as_of": str,
            "error": Optional[str]
        }
    """
    result = {
        "result": "FAIL",
        "host": host,
        "port": port,
        "latency_ms": 0.0,
        "hashrate_ghs": 0.0,
        "temp_max": 0.0,
        "status": "offline",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "error": None
    }
    
    try:
        client = CGMinerClient(host, port, timeout, max_retries=1)
        telemetry = get_normalized_telemetry(client)
        
        result["result"] = "OK" if telemetry["status"] == "online" else "FAIL"
        result["latency_ms"] = telemetry["latency_ms"]
        result["hashrate_ghs"] = telemetry["hashrate_5s"]
        result["temp_max"] = telemetry["temp_max"]
        result["status"] = telemetry["status"]
        result["as_of"] = telemetry["as_of"]
        result["error"] = telemetry.get("error")
        
    except Exception as e:
        result["error"] = str(e)
    
    return result
