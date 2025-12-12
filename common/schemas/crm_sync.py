"""
CRM-Hosting Sync Data Schemas
数据验证和类型定义
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MinerDataSchema:
    """矿机数据结构"""
    id: int
    name: str
    model: str
    quantity: int
    hashrate: float
    total_hashrate: float
    power: int
    total_power: int
    status: str
    location: Optional[str] = None
    electricity_cost: float = 0.05
    daily_electricity_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'model': self.model,
            'quantity': self.quantity,
            'hashrate': self.hashrate,
            'total_hashrate': self.total_hashrate,
            'power': self.power,
            'total_power': self.total_power,
            'status': self.status,
            'location': self.location,
            'electricity_cost': self.electricity_cost,
            'daily_electricity_cost': self.daily_electricity_cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MinerDataSchema':
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            model=data.get('model', ''),
            quantity=data.get('quantity', 1),
            hashrate=data.get('hashrate', 0.0),
            total_hashrate=data.get('total_hashrate', 0.0),
            power=data.get('power', 0),
            total_power=data.get('total_power', 0),
            status=data.get('status', 'active'),
            location=data.get('location'),
            electricity_cost=data.get('electricity_cost', 0.05),
            daily_electricity_cost=data.get('daily_electricity_cost', 0.0),
        )


@dataclass
class ModelStatsSchema:
    """按型号统计结构"""
    count: int = 0
    hashrate: float = 0.0
    power: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'count': self.count,
            'hashrate': self.hashrate,
            'power': self.power,
        }


@dataclass
class HostingStatsSchema:
    """托管统计数据结构"""
    has_hosting: bool = False
    user_access_id: Optional[int] = None
    miners_count: int = 0
    total_hashrate: float = 0.0
    total_power: int = 0
    total_power_mw: float = 0.0
    active_miners: int = 0
    offline_miners: int = 0
    maintenance_miners: int = 0
    estimated_daily_btc: float = 0.0
    estimated_daily_usd: float = 0.0
    avg_efficiency: float = 0.0
    miners: List[Dict[str, Any]] = field(default_factory=list)
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    electricity_cost_daily: float = 0.0
    net_profit_daily: float = 0.0
    btc_price: float = 95000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'has_hosting': self.has_hosting,
            'user_access_id': self.user_access_id,
            'miners_count': self.miners_count,
            'total_hashrate': self.total_hashrate,
            'total_power': self.total_power,
            'total_power_mw': self.total_power_mw,
            'active_miners': self.active_miners,
            'offline_miners': self.offline_miners,
            'maintenance_miners': self.maintenance_miners,
            'estimated_daily_btc': self.estimated_daily_btc,
            'estimated_daily_usd': self.estimated_daily_usd,
            'avg_efficiency': self.avg_efficiency,
            'miners': self.miners,
            'by_model': self.by_model,
            'by_status': self.by_status,
            'electricity_cost_daily': self.electricity_cost_daily,
            'net_profit_daily': self.net_profit_daily,
            'btc_price': self.btc_price,
        }

    @classmethod
    def empty(cls) -> 'HostingStatsSchema':
        return cls(
            by_status={'active': 0, 'offline': 0, 'maintenance': 0, 'sold': 0}
        )


@dataclass
class SyncStatusSchema:
    """同步状态数据结构"""
    total_customers: int = 0
    linked_customers: int = 0
    unlinked_customers: int = 0
    link_rate: float = 0.0
    last_sync: Optional[datetime] = None
    sync_health: str = 'unknown'
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_customers': self.total_customers,
            'linked_customers': self.linked_customers,
            'unlinked_customers': self.unlinked_customers,
            'link_rate': round(self.link_rate, 2),
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_health': self.sync_health,
            'issues': self.issues,
        }

    def calculate_health(self) -> str:
        issues = []
        if self.link_rate < 10:
            issues.append('low_link_rate')
        if self.total_customers > 0 and self.linked_customers == 0:
            issues.append('no_linked_customers')
        
        self.issues = issues
        
        if len(issues) == 0:
            self.sync_health = 'healthy'
        elif len(issues) == 1:
            self.sync_health = 'warning'
        else:
            self.sync_health = 'critical'
        
        return self.sync_health


@dataclass
class SyncResultSchema:
    """同步结果数据结构"""
    total: int = 0
    synced: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'synced': self.synced,
            'skipped': self.skipped,
            'errors': self.errors,
            'error_details': self.error_details if self.errors > 0 else [],
        }


def validate_miner_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """验证矿机数据"""
    errors = []
    
    required_fields = ['id', 'name', 'model', 'status']
    for field in required_fields:
        if field not in data:
            errors.append(f'Missing required field: {field}')
    
    if 'status' in data and data['status'] not in ['active', 'offline', 'maintenance', 'sold']:
        errors.append(f"Invalid status: {data['status']}")
    
    if 'quantity' in data and (not isinstance(data['quantity'], int) or data['quantity'] < 1):
        errors.append('Quantity must be a positive integer')
    
    if 'hashrate' in data and (not isinstance(data['hashrate'], (int, float)) or data['hashrate'] < 0):
        errors.append('Hashrate must be a non-negative number')
    
    return len(errors) == 0, errors


def validate_hosting_stats(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """验证托管统计数据"""
    errors = []
    
    required_fields = ['has_hosting', 'miners_count', 'total_hashrate', 'total_power']
    for field in required_fields:
        if field not in data:
            errors.append(f'Missing required field: {field}')
    
    numeric_fields = ['miners_count', 'total_hashrate', 'total_power', 'active_miners', 
                      'offline_miners', 'estimated_daily_btc', 'estimated_daily_usd']
    for field in numeric_fields:
        if field in data and not isinstance(data[field], (int, float)):
            errors.append(f'{field} must be a number')
    
    return len(errors) == 0, errors
