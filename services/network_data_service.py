"""
网络数据收集和分析服务
自动记录BTC网络统计数据并提供历史分析功能
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from sqlalchemy import func, desc, asc
from models import NetworkSnapshot
from db import db
import pytz

# 设置时区为美国东部时间
EST = pytz.timezone('US/Eastern')

class NetworkDataCollector:
    """网络数据收集器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_current_network_data(self) -> Optional[Dict]:
        """获取当前网络数据"""
        start_time = time.time()
        
        try:
            # 获取BTC价格
            btc_price = self._get_btc_price()
            if not btc_price:
                return None
                
            # 获取网络难度
            difficulty = self._get_network_difficulty()
            if not difficulty:
                return None
                
            # 获取网络算力
            hashrate = self._get_network_hashrate()
            if not hashrate:
                return None
                
            # 获取区块奖励
            block_reward = self._get_block_reward()
            
            api_response_time = time.time() - start_time
            
            # 获取EST时间
            utc_time = datetime.utcnow()
            est_time = pytz.utc.localize(utc_time).astimezone(EST)
            
            return {
                'btc_price': btc_price,
                'network_difficulty': difficulty,
                'network_hashrate': hashrate,
                'block_reward': block_reward,
                'api_response_time': api_response_time,
                'recorded_at': est_time.replace(tzinfo=None)
            }
            
        except Exception as e:
            self.logger.error(f"获取网络数据失败: {e}")
            return None
    
    def _get_btc_price(self) -> Optional[float]:
        """从CoinGecko获取BTC价格"""
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return float(data['bitcoin']['usd'])
        except Exception as e:
            self.logger.error(f"获取BTC价格失败: {e}")
        return None
    
    def _get_network_difficulty(self) -> Optional[float]:
        """从Blockchain.info获取网络难度"""
        try:
            response = requests.get("https://blockchain.info/q/getdifficulty", timeout=10)
            if response.status_code == 200:
                return float(response.text) / 1e12  # 转换为T
        except Exception as e:
            self.logger.error(f"获取网络难度失败: {e}")
        return None
    
    def _get_network_hashrate(self) -> Optional[float]:
        """从minerstat API获取网络算力（专业挖矿数据源）"""
        try:
            # 优先使用minerstat API
            response = requests.get("https://api.minerstat.com/v2/coins?list=BTC", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    btc_data = data[0]
                    hashrate_hs = float(btc_data.get('network_hashrate', 0))
                    return hashrate_hs / 1e18  # H/s to EH/s
            
            # 备用：blockchain.info hashrate API
            response = requests.get("https://blockchain.info/q/hashrate", timeout=10)
            if response.status_code == 200:
                hashrate_gh = float(response.text)
                return hashrate_gh / 1e9  # GH/s to EH/s
                
        except Exception as e:
            self.logger.error(f"获取网络算力失败: {e}")
        return None
    
    def _get_block_reward(self) -> float:
        """获取当前区块奖励"""
        try:
            response = requests.get("https://blockchain.info/q/getblockcount", timeout=10)
            if response.status_code == 200:
                block_height = int(response.text)
                # 比特币减半逻辑
                halvings = block_height // 210000
                return 50 / (2 ** halvings)
        except Exception as e:
            self.logger.error(f"获取区块奖励失败: {e}")
        return 3.125  # 当前默认值
    
    def record_network_snapshot(self) -> bool:
        """记录当前网络快照到数据库"""
        data = self.get_current_network_data()
        if not data:
            return False
            
        try:
            snapshot = NetworkSnapshot(
                btc_price=data['btc_price'],
                network_difficulty=data['network_difficulty'],
                network_hashrate=data['network_hashrate'],
                block_reward=data['block_reward'],
                api_response_time=data['api_response_time'],
                recorded_at=data['recorded_at']  # 已经是EST时间
            )
            
            db.session.add(snapshot)
            db.session.commit()
            
            self.logger.info(f"网络快照记录成功: BTC=${data['btc_price']}, 难度={data['network_difficulty']:.2f}T")
            return True
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"记录网络快照失败: {e}")
            return False

class NetworkDataAnalyzer:
    """网络数据分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_price_trend(self, days: int = 7) -> Dict:
        """获取价格趋势分析"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            snapshots = NetworkSnapshot.query.filter(
                NetworkSnapshot.recorded_at >= start_date,
                NetworkSnapshot.is_valid == True
            ).order_by(asc(NetworkSnapshot.recorded_at)).all()
            
            if not snapshots:
                return {'error': '没有历史数据'}
            
            prices = [s.btc_price for s in snapshots]
            timestamps = [s.recorded_at.isoformat() for s in snapshots]
            
            # 计算统计信息
            current_price = prices[-1]
            previous_price = prices[0]
            price_change = current_price - previous_price
            price_change_percent = (price_change / previous_price) * 100
            
            return {
                'period_days': days,
                'data_points': len(snapshots),
                'current_price': current_price,
                'previous_price': previous_price,
                'price_change': price_change,
                'price_change_percent': price_change_percent,
                'max_price': max(prices),
                'min_price': min(prices),
                'avg_price': sum(prices) / len(prices),
                'timestamps': timestamps,
                'prices': prices
            }
            
        except Exception as e:
            self.logger.error(f"价格趋势分析失败: {e}")
            return {'error': str(e)}
    
    def get_difficulty_trend(self, days: int = 30) -> Dict:
        """获取难度调整趋势"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            snapshots = NetworkSnapshot.query.filter(
                NetworkSnapshot.recorded_at >= start_date,
                NetworkSnapshot.is_valid == True
            ).order_by(asc(NetworkSnapshot.recorded_at)).all()
            
            if not snapshots:
                return {'error': '没有历史数据'}
            
            difficulties = [s.network_difficulty for s in snapshots]
            timestamps = [s.recorded_at.isoformat() for s in snapshots]
            
            current_difficulty = difficulties[-1]
            previous_difficulty = difficulties[0]
            difficulty_change_percent = ((current_difficulty - previous_difficulty) / previous_difficulty) * 100
            
            return {
                'period_days': days,
                'data_points': len(snapshots),
                'current_difficulty': current_difficulty,
                'previous_difficulty': previous_difficulty,
                'difficulty_change_percent': difficulty_change_percent,
                'max_difficulty': max(difficulties),
                'min_difficulty': min(difficulties),
                'avg_difficulty': sum(difficulties) / len(difficulties),
                'timestamps': timestamps,
                'difficulties': difficulties
            }
            
        except Exception as e:
            self.logger.error(f"难度趋势分析失败: {e}")
            return {'error': str(e)}
    
    def get_hashrate_analysis(self, days: int = 7) -> Dict:
        """获取算力分析"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            snapshots = NetworkSnapshot.query.filter(
                NetworkSnapshot.recorded_at >= start_date,
                NetworkSnapshot.is_valid == True
            ).order_by(asc(NetworkSnapshot.recorded_at)).all()
            
            if not snapshots:
                return {'error': '没有历史数据'}
            
            hashrates = [s.network_hashrate for s in snapshots]
            timestamps = [s.recorded_at.isoformat() for s in snapshots]
            
            current_hashrate = hashrates[-1]
            previous_hashrate = hashrates[0]
            hashrate_change_percent = ((current_hashrate - previous_hashrate) / previous_hashrate) * 100
            
            return {
                'period_days': days,
                'data_points': len(snapshots),
                'current_hashrate': current_hashrate,
                'previous_hashrate': previous_hashrate,
                'hashrate_change_percent': hashrate_change_percent,
                'max_hashrate': max(hashrates),
                'min_hashrate': min(hashrates),
                'avg_hashrate': sum(hashrates) / len(hashrates),
                'timestamps': timestamps,
                'hashrates': hashrates
            }
            
        except Exception as e:
            self.logger.error(f"算力分析失败: {e}")
            return {'error': str(e)}
    
    def get_profitability_forecast(self, miner_model: str, electricity_cost: float, days_back: int = 30) -> Dict:
        """基于历史数据预测挖矿收益"""
        try:
            # 矿机规格数据
            MINER_DATA = {
                "Antminer S21": {"hashrate": 200, "power_watt": 3500},
                "Antminer S19 Pro": {"hashrate": 110, "power_watt": 3250},
                "Antminer S19j Pro": {"hashrate": 104, "power_watt": 3068},
                "Whatsminer M50S": {"hashrate": 126, "power_watt": 3276},
                "Whatsminer M53S": {"hashrate": 226, "power_watt": 6554}
            }
            
            if miner_model not in MINER_DATA:
                return {'error': f'不支持的矿机型号: {miner_model}'}
            
            miner_specs = MINER_DATA[miner_model]
            hashrate_th = miner_specs['hashrate']
            power_w = miner_specs['power_watt']
            
            # 获取历史数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            snapshots = NetworkSnapshot.query.filter(
                NetworkSnapshot.recorded_at >= start_date,
                NetworkSnapshot.is_valid == True
            ).order_by(desc(NetworkSnapshot.recorded_at)).limit(50).all()
            
            if not snapshots:
                return {'error': '没有足够的历史数据'}
            
            # 计算历史收益
            daily_profits = []
            for snapshot in snapshots:
                # 每日BTC产出计算
                daily_btc = (hashrate_th * 1e12 * 86400 * snapshot.block_reward) / (snapshot.network_difficulty * 1e12 * 2**32)
                
                # 每日收入
                daily_revenue = daily_btc * snapshot.btc_price
                
                # 每日电费
                daily_electricity = (power_w / 1000) * 24 * electricity_cost
                
                # 每日净利润
                daily_profit = daily_revenue - daily_electricity
                
                daily_profits.append({
                    'date': snapshot.recorded_at.isoformat(),
                    'btc_price': snapshot.btc_price,
                    'daily_btc': daily_btc,
                    'daily_revenue': daily_revenue,
                    'daily_electricity': daily_electricity,
                    'daily_profit': daily_profit,
                    'profit_margin': (daily_profit / daily_revenue * 100) if daily_revenue > 0 else 0
                })
            
            # 计算统计数据
            profits = [p['daily_profit'] for p in daily_profits]
            avg_profit = sum(profits) / len(profits)
            max_profit = max(profits)
            min_profit = min(profits)
            
            profitable_days = len([p for p in profits if p > 0])
            profitability_rate = (profitable_days / len(profits)) * 100
            
            return {
                'miner_model': miner_model,
                'hashrate_th': hashrate_th,
                'power_w': power_w,
                'electricity_cost': electricity_cost,
                'analysis_period': days_back,
                'data_points': len(daily_profits),
                'avg_daily_profit': avg_profit,
                'max_daily_profit': max_profit,
                'min_daily_profit': min_profit,
                'profitability_rate': profitability_rate,
                'monthly_profit_estimate': avg_profit * 30,
                'yearly_profit_estimate': avg_profit * 365,
                'daily_profits': daily_profits[-30:]  # 返回最近30天
            }
            
        except Exception as e:
            self.logger.error(f"收益预测分析失败: {e}")
            return {'error': str(e)}
    
    def get_network_statistics(self) -> Dict:
        """获取网络统计概览"""
        try:
            total_records = NetworkSnapshot.query.count()
            
            if total_records == 0:
                return {'error': '没有历史数据'}
            
            # 最近记录
            latest = NetworkSnapshot.query.order_by(desc(NetworkSnapshot.recorded_at)).first()
            
            # 24小时前的记录
            day_ago = datetime.utcnow() - timedelta(days=1)
            day_ago_record = NetworkSnapshot.query.filter(
                NetworkSnapshot.recorded_at >= day_ago
            ).order_by(asc(NetworkSnapshot.recorded_at)).first()
            
            # 7天前的记录
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_ago_record = NetworkSnapshot.query.filter(
                NetworkSnapshot.recorded_at >= week_ago
            ).order_by(asc(NetworkSnapshot.recorded_at)).first()
            
            stats = {
                'total_records': total_records,
                'latest_record': latest.to_dict() if latest else None,
                'data_coverage_days': None
            }
            
            if latest:
                first_record = NetworkSnapshot.query.order_by(asc(NetworkSnapshot.recorded_at)).first()
                if first_record:
                    coverage_days = (latest.recorded_at - first_record.recorded_at).days
                    stats['data_coverage_days'] = coverage_days
                
                # 24小时变化
                if day_ago_record:
                    stats['24h_changes'] = {
                        'price_change': latest.btc_price - day_ago_record.btc_price,
                        'price_change_percent': ((latest.btc_price - day_ago_record.btc_price) / day_ago_record.btc_price) * 100,
                        'hashrate_change_percent': ((latest.network_hashrate - day_ago_record.network_hashrate) / day_ago_record.network_hashrate) * 100
                    }
                
                # 7天变化
                if week_ago_record:
                    stats['7d_changes'] = {
                        'price_change': latest.btc_price - week_ago_record.btc_price,
                        'price_change_percent': ((latest.btc_price - week_ago_record.btc_price) / week_ago_record.btc_price) * 100,
                        'difficulty_change_percent': ((latest.network_difficulty - week_ago_record.network_difficulty) / week_ago_record.network_difficulty) * 100
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取网络统计失败: {e}")
            return {'error': str(e)}

# 全局实例
network_collector = NetworkDataCollector()
network_analyzer = NetworkDataAnalyzer()