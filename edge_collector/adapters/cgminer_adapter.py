"""
CGMiner Adapter
CGMiner API控制适配器

Implements miner control via CGMiner TCP API.
"""
import logging
from typing import Optional, Dict, Any
from .base import MinerAdapter, AdapterResult

logger = logging.getLogger(__name__)


class CGMinerAdapter(MinerAdapter):
    """CGMiner API control adapter"""
    
    POWER_MODE_FREQ = {
        'high': 700,
        'normal': 600,
        'eco': 500
    }
    
    def __init__(self, ip_address: str, port: int = 4028, credentials: Optional[Dict] = None):
        super().__init__(ip_address, port, credentials)
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from edge_collector.cgminer_client import CGMinerClient
            self._client = CGMinerClient(self.ip_address, self.port)
        return self._client
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Collect current metrics for before/after comparison"""
        try:
            summary = self.client.get_summary()
            if 'SUMMARY' in summary and summary['SUMMARY']:
                s = summary['SUMMARY'][0]
                return {
                    'hashrate_ghs': s.get('GHS 5s', 0),
                    'temperature': s.get('Temperature', 0),
                    'uptime': s.get('Elapsed', 0)
                }
        except Exception as e:
            logger.warning(f"Failed to get metrics: {e}")
        return {}
    
    def reboot(self, mode: str = 'soft') -> AdapterResult:
        """Reboot the miner"""
        metrics_before = self._get_current_metrics()
        
        try:
            if mode == 'hard':
                result = self.client.send_command("quit")
            else:
                result = self.client.send_command("restart")
            
            status = result.get('STATUS', [{}])[0]
            if status.get('STATUS') in ('S', 'I'):
                return AdapterResult(
                    success=True,
                    message=f"{mode.capitalize()} reboot initiated",
                    metrics={'before': metrics_before}
                )
            else:
                return AdapterResult(
                    success=False,
                    message=status.get('Msg', 'Reboot failed')
                )
        except Exception as e:
            return AdapterResult(success=False, message=str(e))
    
    def set_power_mode(self, mode: str) -> AdapterResult:
        """Set power mode by adjusting frequency"""
        freq = self.POWER_MODE_FREQ.get(mode, 600)
        return self.set_frequency(frequency_mhz=freq)
    
    def change_pool(self, pool_url: str, worker_name: str, password: str = '') -> AdapterResult:
        """Change mining pool"""
        try:
            add_result = self.client.send_command("addpool", f"{pool_url},{worker_name},{password}")
            
            pools_result = self.client.get_pools()
            pools = pools_result.get('POOLS', [])
            
            new_pool_id = None
            for pool in pools:
                if pool_url in pool.get('URL', ''):
                    new_pool_id = pool.get('POOL', 0)
                    break
            
            if new_pool_id is not None:
                switch_result = self.client.send_command("switchpool", str(new_pool_id))
                status = switch_result.get('STATUS', [{}])[0]
                
                if status.get('STATUS') in ('S', 'I'):
                    return AdapterResult(
                        success=True,
                        message=f"Pool changed to {pool_url}",
                        metrics={'pool_id': new_pool_id, 'pool_url': pool_url}
                    )
            
            return AdapterResult(
                success=False,
                message="Failed to switch to new pool"
            )
        except Exception as e:
            return AdapterResult(success=False, message=str(e))
    
    def set_frequency(self, frequency_mhz: Optional[int] = None, profile: Optional[str] = None) -> AdapterResult:
        """Set chip frequency"""
        if profile:
            profile_freq = {'stock': 600, 'overclock': 700, 'underclock': 500}
            frequency_mhz = profile_freq.get(profile, 600)
        
        if not frequency_mhz:
            return AdapterResult(success=False, message="Frequency or profile required")
        
        try:
            result = self.client.send_command("ascset", f"0,freq,{frequency_mhz}")
            status = result.get('STATUS', [{}])[0]
            
            if status.get('STATUS') in ('S', 'I'):
                return AdapterResult(
                    success=True,
                    message=f"Frequency set to {frequency_mhz} MHz",
                    metrics={'frequency_mhz': frequency_mhz}
                )
            else:
                return AdapterResult(
                    success=False,
                    message=status.get('Msg', 'Failed to set frequency')
                )
        except Exception as e:
            return AdapterResult(success=False, message=str(e))
    
    def set_thermal_policy(self, fan_mode: str = 'auto', fan_speed_pct: Optional[int] = None,
                          temp_warning_c: Optional[int] = None, temp_critical_c: Optional[int] = None) -> AdapterResult:
        """Set thermal/fan policy"""
        try:
            if fan_mode == 'manual' and fan_speed_pct is not None:
                for i in range(4):
                    self.client.send_command("fanctrl", f"{i},{fan_speed_pct}")
                
                return AdapterResult(
                    success=True,
                    message=f"Fan speed set to {fan_speed_pct}%",
                    metrics={'fan_mode': fan_mode, 'fan_speed_pct': fan_speed_pct}
                )
            elif fan_mode == 'auto':
                self.client.send_command("fanctrl", "auto")
                return AdapterResult(
                    success=True,
                    message="Fan set to auto mode",
                    metrics={'fan_mode': 'auto'}
                )
            else:
                return AdapterResult(
                    success=True,
                    message=f"Thermal policy updated ({fan_mode})",
                    metrics={'fan_mode': fan_mode}
                )
        except Exception as e:
            return AdapterResult(success=False, message=str(e))
    
    def set_led(self, state: str) -> AdapterResult:
        """Set LED state"""
        try:
            cmd = "ledon" if state == 'on' else "ledoff"
            result = self.client.send_command(cmd)
            status = result.get('STATUS', [{}])[0]
            
            if status.get('STATUS') in ('S', 'I'):
                return AdapterResult(
                    success=True,
                    message=f"LED turned {state}",
                    metrics={'led_state': state}
                )
            else:
                return AdapterResult(
                    success=False,
                    message=status.get('Msg', f'Failed to set LED {state}')
                )
        except Exception as e:
            return AdapterResult(success=False, message=str(e))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current miner status"""
        try:
            return self.client.get_all_data()
        except Exception as e:
            return {'error': str(e)}
