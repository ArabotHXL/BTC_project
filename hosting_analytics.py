
"""
托管业务分析模块
利用现有的 market_analytics 表进行对账和收益分析
"""
import logging
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class HostingAnalytics:
    """托管业务分析器"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    def calculate_client_settlement(self, client_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """
        计算客户对账数据
        利用 market_analytics 表的历史数据进行精确计算
        """
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 获取期间内的市场数据
            cursor.execute("""
                SELECT recorded_at, btc_price, network_difficulty, network_hashrate
                FROM market_analytics 
                WHERE recorded_at BETWEEN %s AND %s
                ORDER BY recorded_at ASC
            """, (start_date, end_date))
            
            market_data = cursor.fetchall()
            
            if not market_data:
                return {'error': '该时间段内无市场数据'}
            
            # 获取客户设备信息
            cursor.execute("""
                SELECT device_serial, miner_model, hashrate_th, power_consumption_w, monthly_hosting_fee
                FROM hosted_devices 
                WHERE client_id = %s AND hosting_start_date <= %s
            """, (client_id, end_date))
            
            devices = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not devices:
                return {'error': '该客户无托管设备'}
            
            # 计算收益和费用
            total_revenue = 0
            total_hosting_fees = 0
            total_electricity_cost = 0
            
            for device in devices:
                device_serial, model, hashrate, power_w, hosting_fee = device
                
                # 基于市场数据计算收益
                device_revenue = self._calculate_device_revenue(
                    hashrate, market_data
                )
                
                # 计算电费（基于功耗和时间段）
                hours_in_period = (end_date - start_date).total_seconds() / 3600
                electricity_cost = (power_w / 1000) * hours_in_period * 0.055  # 假设电费 $0.055/kWh
                
                total_revenue += device_revenue
                total_hosting_fees += hosting_fee
                total_electricity_cost += electricity_cost
            
            settlement = {
                'client_id': client_id,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'revenue': {
                    'total_btc_mined': total_revenue / market_data[-1][1],  # 最后的BTC价格
                    'total_usd_value': total_revenue,
                    'avg_btc_price': sum(row[1] for row in market_data) / len(market_data)
                },
                'costs': {
                    'hosting_fees': total_hosting_fees,
                    'electricity_cost': total_electricity_cost,
                    'total_costs': total_hosting_fees + total_electricity_cost
                },
                'net_profit': total_revenue - (total_hosting_fees + total_electricity_cost),
                'devices_count': len(devices)
            }
            
            return settlement
            
        except Exception as e:
            logger.error(f"对账计算失败: {e}")
            return {'error': str(e)}
    
    def _calculate_device_revenue(self, hashrate_th: float, market_data: List) -> float:
        """
        基于设备算力和市场数据计算收益
        """
        total_revenue = 0
        
        for i in range(len(market_data) - 1):
            current_data = market_data[i]
            next_data = market_data[i + 1]
            
            # 计算这个时间段的收益
            btc_price = current_data[1]
            difficulty = current_data[2]
            network_hashrate = current_data[3]
            
            # 计算时间段长度
            time_diff_hours = (next_data[0] - current_data[0]).total_seconds() / 3600
            
            # 使用比特币挖矿收益公式
            if difficulty > 0 and network_hashrate > 0:
                blocks_per_hour = 6  # 每小时约6个区块
                btc_per_block = 3.125  # 当前区块奖励
                
                # 设备在网络中的哈希率占比
                device_share = (hashrate_th * 1e12) / (network_hashrate * 1e18)
                
                # 计算该时间段的BTC收益
                btc_earned = device_share * blocks_per_hour * btc_per_block * time_diff_hours
                
                # 转换为USD
                usd_revenue = btc_earned * btc_price
                total_revenue += usd_revenue
        
        return total_revenue

# 使用示例：
# analytics = HostingAnalytics(os.environ.get('DATABASE_URL'))
# settlement = analytics.calculate_client_settlement(
#     client_id=123,
#     start_date=datetime(2024, 1, 1),
#     end_date=datetime(2024, 1, 31)
# )
