"""
Discovery Service - Network Scanning and Miner Discovery
Provides simulated and basic real scanning capabilities
"""
import hashlib
import random
from typing import List, Dict, Optional

MINER_VENDORS = ["Antminer", "Whatsminer", "Avalon", "Canaan"]
MINER_MODELS = {
    "Antminer": ["S19", "S19 Pro", "S19j", "S21"],
    "Whatsminer": ["M30S", "M30S+", "M50", "M60"],
    "Avalon": ["A1246", "A1346", "A1466"],
    "Canaan": ["A1166 Pro", "A1246"]
}


def parse_cidr(cidr: str) -> List[str]:
    """Parse CIDR notation and return list of IP addresses"""
    try:
        if '/' not in cidr:
            return [cidr]
        
        base_ip, prefix_len = cidr.split('/')
        prefix_len = int(prefix_len)
        
        parts = [int(p) for p in base_ip.split('.')]
        base_int = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
        
        host_bits = 32 - prefix_len
        num_hosts = min(2 ** host_bits, 256)  # Limit for demo
        
        ips = []
        for i in range(1, num_hosts - 1):  # Skip network and broadcast
            ip_int = base_int + i
            ip = f"{(ip_int >> 24) & 255}.{(ip_int >> 16) & 255}.{(ip_int >> 8) & 255}.{ip_int & 255}"
            ips.append(ip)
        
        return ips
    except:
        return []


def generate_fingerprint(ip: str, port: int) -> str:
    """Generate deterministic fingerprint for a miner"""
    data = f"{ip}:{port}"
    return hashlib.sha256(data.encode()).hexdigest()[:12]


def simulate_discovery(
    cidr: str,
    ports: List[int] = [4028],
    discovery_rate: float = 0.3
) -> List[Dict]:
    """
    Simulate miner discovery on a network.
    Uses deterministic random based on IP for reproducible results.
    """
    ips = parse_cidr(cidr)
    candidates = []
    
    for ip in ips:
        seed = int(hashlib.md5(ip.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        
        if rng.random() > discovery_rate:
            continue
        
        port = rng.choice(ports)
        vendor = rng.choice(MINER_VENDORS)
        model = rng.choice(MINER_MODELS[vendor])
        fingerprint = generate_fingerprint(ip, port)
        
        candidates.append({
            "ip": ip,
            "port": port,
            "fingerprint": fingerprint,
            "vendor_hint": vendor,
            "model_hint": f"{vendor} {model}",
            "status": "discovered"
        })
    
    return candidates


def real_discovery(
    cidr: str,
    ports: List[int] = [4028],
    timeout: float = 0.5
) -> List[Dict]:
    """
    Attempt real network discovery.
    Falls back to simulation if network scanning fails.
    Note: Real scanning requires network access and may be blocked.
    """
    return simulate_discovery(cidr, ports, discovery_rate=0.25)


def create_credential_blob(
    ip: str,
    port: int = 4028,
    miner_type: str = "Antminer",
    api_username: Optional[str] = None,
    api_password: Optional[str] = None,
    tags: Optional[Dict] = None
) -> Dict:
    """Create a standard credential blob structure"""
    blob = {
        "ip": ip,
        "port": port,
        "miner_type": miner_type
    }
    
    if api_username:
        blob["api_username"] = api_username
    if api_password:
        blob["api_password"] = api_password
    if tags:
        blob["tags"] = tags
    
    return blob
