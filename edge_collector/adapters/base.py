"""
Base Miner Adapter Interface
矿机控制适配器基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class CommandType(Enum):
    REBOOT = "REBOOT"
    POWER_MODE = "POWER_MODE"
    CHANGE_POOL = "CHANGE_POOL"
    SET_FREQ = "SET_FREQ"
    THERMAL_POLICY = "THERMAL_POLICY"
    LED = "LED"


@dataclass
class AdapterResult:
    """Result of a miner control command"""
    success: bool
    message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': 'SUCCEEDED' if self.success else 'FAILED',
            'message': self.message,
            'metrics': self.metrics
        }


class MinerAdapter(ABC):
    """Abstract base class for miner control adapters"""
    
    def __init__(self, ip_address: str, port: int = 4028, credentials: Optional[Dict] = None):
        self.ip_address = ip_address
        self.port = port
        self.credentials = credentials or {}
    
    @abstractmethod
    def reboot(self, mode: str = 'soft') -> AdapterResult:
        """Reboot the miner (soft or hard)"""
        pass
    
    @abstractmethod
    def set_power_mode(self, mode: str) -> AdapterResult:
        """Set power mode (high, normal, eco)"""
        pass
    
    @abstractmethod
    def change_pool(self, pool_url: str, worker_name: str, password: str = '') -> AdapterResult:
        """Change mining pool"""
        pass
    
    @abstractmethod
    def set_frequency(self, frequency_mhz: Optional[int] = None, profile: Optional[str] = None) -> AdapterResult:
        """Set chip frequency"""
        pass
    
    @abstractmethod
    def set_thermal_policy(self, fan_mode: str = 'auto', fan_speed_pct: Optional[int] = None,
                          temp_warning_c: Optional[int] = None, temp_critical_c: Optional[int] = None) -> AdapterResult:
        """Set thermal/fan policy"""
        pass
    
    @abstractmethod
    def set_led(self, state: str) -> AdapterResult:
        """Set LED state (on/off)"""
        pass
    
    def execute(self, command_type: str, payload: Dict[str, Any]) -> AdapterResult:
        """Execute a command with payload"""
        if command_type == 'REBOOT':
            return self.reboot(payload.get('mode', 'soft'))
        elif command_type == 'POWER_MODE':
            return self.set_power_mode(payload.get('mode', 'normal'))
        elif command_type == 'CHANGE_POOL':
            return self.change_pool(
                pool_url=payload.get('pool_url', ''),
                worker_name=payload.get('worker_name', ''),
                password=payload.get('password', '')
            )
        elif command_type == 'SET_FREQ':
            return self.set_frequency(
                frequency_mhz=payload.get('frequency_mhz'),
                profile=payload.get('profile')
            )
        elif command_type == 'THERMAL_POLICY':
            return self.set_thermal_policy(
                fan_mode=payload.get('fan_mode', 'auto'),
                fan_speed_pct=payload.get('fan_speed_pct'),
                temp_warning_c=payload.get('temp_warning_c'),
                temp_critical_c=payload.get('temp_critical_c')
            )
        elif command_type == 'LED':
            return self.set_led(payload.get('state', 'off'))
        else:
            return AdapterResult(success=False, message=f"Unknown command type: {command_type}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current miner status (for metrics collection)"""
        return {}
