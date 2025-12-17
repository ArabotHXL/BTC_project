"""
Simulated Miner Adapter
模拟矿机控制适配器 - 用于开发测试

Always succeeds and generates fake metrics for testing purposes.
"""
import random
import time
import logging
from typing import Optional, Dict, Any
from .base import MinerAdapter, AdapterResult

logger = logging.getLogger(__name__)


class SimulatedAdapter(MinerAdapter):
    """Simulated miner adapter for testing"""
    
    def __init__(self, ip_address: str, port: int = 4028, credentials: Optional[Dict] = None,
                 failure_rate: float = 0.0, delay_range: tuple = (0.1, 0.5)):
        super().__init__(ip_address, port, credentials)
        self.failure_rate = failure_rate
        self.delay_range = delay_range
        
        self._state = {
            'power_mode': 'normal',
            'frequency_mhz': 600,
            'fan_mode': 'auto',
            'fan_speed_pct': 75,
            'led_state': 'off',
            'pool_url': 'stratum+tcp://btc.f2pool.com:3333',
            'worker_name': 'test.worker1',
            'hashrate_ths': random.uniform(200, 240),
            'temperature_c': random.uniform(65, 80),
            'uptime_hours': random.uniform(100, 1000)
        }
    
    def _simulate_delay(self):
        """Simulate network/processing delay"""
        time.sleep(random.uniform(*self.delay_range))
    
    def _maybe_fail(self) -> Optional[AdapterResult]:
        """Randomly fail based on failure_rate"""
        if random.random() < self.failure_rate:
            return AdapterResult(
                success=False,
                message="Simulated random failure"
            )
        return None
    
    def _generate_metrics(self, **extra) -> Dict[str, Any]:
        """Generate simulated metrics"""
        metrics = {
            'hashrate_before_ths': self._state['hashrate_ths'],
            'temperature_before_c': self._state['temperature_c'],
            'simulated': True,
            'ip_address': self.ip_address
        }
        metrics.update(extra)
        return metrics
    
    def reboot(self, mode: str = 'soft') -> AdapterResult:
        """Simulate reboot"""
        self._simulate_delay()
        
        if fail := self._maybe_fail():
            return fail
        
        logger.info(f"[SIMULATED] Rebooting {self.ip_address} ({mode})")
        
        self._state['uptime_hours'] = 0
        self._state['hashrate_ths'] = random.uniform(200, 240)
        
        return AdapterResult(
            success=True,
            message=f"Simulated {mode} reboot successful",
            metrics=self._generate_metrics(reboot_mode=mode)
        )
    
    def set_power_mode(self, mode: str) -> AdapterResult:
        """Simulate power mode change"""
        self._simulate_delay()
        
        if fail := self._maybe_fail():
            return fail
        
        freq_map = {'high': 700, 'normal': 600, 'eco': 500}
        hashrate_map = {'high': (230, 250), 'normal': (200, 230), 'eco': (170, 200)}
        
        old_mode = self._state['power_mode']
        self._state['power_mode'] = mode
        self._state['frequency_mhz'] = freq_map.get(mode, 600)
        self._state['hashrate_ths'] = random.uniform(*hashrate_map.get(mode, (200, 230)))
        
        logger.info(f"[SIMULATED] Power mode changed on {self.ip_address}: {old_mode} -> {mode}")
        
        return AdapterResult(
            success=True,
            message=f"Power mode changed to {mode}",
            metrics=self._generate_metrics(
                power_mode=mode,
                frequency_mhz=self._state['frequency_mhz'],
                hashrate_after_ths=self._state['hashrate_ths']
            )
        )
    
    def change_pool(self, pool_url: str, worker_name: str, password: str = '') -> AdapterResult:
        """Simulate pool change"""
        self._simulate_delay()
        
        if fail := self._maybe_fail():
            return fail
        
        old_pool = self._state['pool_url']
        self._state['pool_url'] = pool_url
        self._state['worker_name'] = worker_name
        
        logger.info(f"[SIMULATED] Pool changed on {self.ip_address}: {old_pool} -> {pool_url}")
        
        return AdapterResult(
            success=True,
            message=f"Pool changed to {pool_url}",
            metrics=self._generate_metrics(
                pool_url=pool_url,
                worker_name=worker_name,
                old_pool=old_pool
            )
        )
    
    def set_frequency(self, frequency_mhz: Optional[int] = None, profile: Optional[str] = None) -> AdapterResult:
        """Simulate frequency change"""
        self._simulate_delay()
        
        if fail := self._maybe_fail():
            return fail
        
        if profile:
            profile_freq = {'stock': 600, 'overclock': 700, 'underclock': 500}
            frequency_mhz = profile_freq.get(profile, 600)
        
        if not frequency_mhz:
            return AdapterResult(success=False, message="Frequency or profile required")
        
        old_freq = self._state['frequency_mhz']
        self._state['frequency_mhz'] = frequency_mhz
        
        hashrate_factor = frequency_mhz / 600
        self._state['hashrate_ths'] = 220 * hashrate_factor * random.uniform(0.95, 1.05)
        
        logger.info(f"[SIMULATED] Frequency changed on {self.ip_address}: {old_freq} -> {frequency_mhz} MHz")
        
        return AdapterResult(
            success=True,
            message=f"Frequency set to {frequency_mhz} MHz",
            metrics=self._generate_metrics(
                frequency_mhz=frequency_mhz,
                old_frequency_mhz=old_freq,
                hashrate_after_ths=self._state['hashrate_ths']
            )
        )
    
    def set_thermal_policy(self, fan_mode: str = 'auto', fan_speed_pct: Optional[int] = None,
                          temp_warning_c: Optional[int] = None, temp_critical_c: Optional[int] = None) -> AdapterResult:
        """Simulate thermal policy change"""
        self._simulate_delay()
        
        if fail := self._maybe_fail():
            return fail
        
        old_fan_mode = self._state['fan_mode']
        self._state['fan_mode'] = fan_mode
        
        if fan_speed_pct is not None:
            self._state['fan_speed_pct'] = fan_speed_pct
            if fan_speed_pct > 80:
                self._state['temperature_c'] = random.uniform(60, 70)
            elif fan_speed_pct < 50:
                self._state['temperature_c'] = random.uniform(75, 85)
        
        logger.info(f"[SIMULATED] Thermal policy changed on {self.ip_address}: {old_fan_mode} -> {fan_mode}")
        
        return AdapterResult(
            success=True,
            message=f"Thermal policy updated ({fan_mode})",
            metrics=self._generate_metrics(
                fan_mode=fan_mode,
                fan_speed_pct=self._state['fan_speed_pct'],
                temperature_after_c=self._state['temperature_c']
            )
        )
    
    def set_led(self, state: str) -> AdapterResult:
        """Simulate LED control"""
        self._simulate_delay()
        
        if fail := self._maybe_fail():
            return fail
        
        old_state = self._state['led_state']
        self._state['led_state'] = state
        
        logger.info(f"[SIMULATED] LED changed on {self.ip_address}: {old_state} -> {state}")
        
        return AdapterResult(
            success=True,
            message=f"LED turned {state}",
            metrics=self._generate_metrics(led_state=state)
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get simulated miner status"""
        return {
            'ip_address': self.ip_address,
            'online': True,
            'simulated': True,
            **self._state
        }
