#!/usr/bin/env python3
"""
历史数据引擎
替换回测系统中的随机数据模拟
"""

import os
import logging
import requests
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HistoricalPrice:
    """历史价格数据点"""
    date: datetime
    price: float
    volume: float = 0
    market_cap: float = 0

class HistoricalDataEngine:
    """历史数据引擎"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HashInsight-Analytics/1.0'
        })
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def fetch_coingecko_historical_data(self, days: int = 365) -> List[HistoricalPrice]:
        """从CoinGecko获取历史价格数据"""
        try:
            url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': str(days),
                'interval': 'daily'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            prices = data['prices']
            volumes = data.get('total_volumes', [])
            market_caps = data.get('market_caps', [])
            
            historical_data = []
            for i, price_point in enumerate(prices):
                timestamp_ms = price_point[0]
                price = price_point[1]
                
                volume = volumes[i][1] if i < len(volumes) else 0
                market_cap = market_caps[i][1] if i < len(market_caps) else 0
                
                date = datetime.fromtimestamp(timestamp_ms / 1000)
                historical_data.append(HistoricalPrice(
                    date=date,
                    price=price,
                    volume=volume,
                    market_cap=market_cap
                ))
            
            logger.info(f"获取到{len(historical_data)}天的历史价格数据")
            return historical_data
            
        except Exception as e:
            logger.error(f"获取CoinGecko历史数据失败: {e}")
            return []
    
    def store_historical_data(self, historical_data: List[HistoricalPrice]):
        """存储历史数据到数据库"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 创建历史价格表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_prices (
                    id SERIAL PRIMARY KEY,
                    price_date DATE NOT NULL UNIQUE,
                    btc_price DECIMAL(12, 2) NOT NULL,
                    volume_24h DECIMAL(15, 2) DEFAULT 0,
                    market_cap DECIMAL(20, 2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_historical_prices_date ON historical_prices(price_date);")
            
            # 批量插入数据（忽略重复）
            for data_point in historical_data:
                cursor.execute("""
                    INSERT INTO historical_prices (price_date, btc_price, volume_24h, market_cap)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (price_date) 
                    DO UPDATE SET
                        btc_price = EXCLUDED.btc_price,
                        volume_24h = EXCLUDED.volume_24h,
                        market_cap = EXCLUDED.market_cap
                """, (
                    data_point.date.date(),
                    data_point.price,
                    data_point.volume,
                    data_point.market_cap
                ))
            
            conn.commit()
            logger.info(f"存储了{len(historical_data)}天的历史数据")
            return True
            
        except Exception as e:
            logger.error(f"存储历史数据失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_price_history(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """获取指定时间范围的价格历史"""
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price_date, btc_price, volume_24h, market_cap
                FROM historical_prices
                WHERE price_date >= %s AND price_date <= %s
                ORDER BY price_date
            """, (start_date.date(), end_date.date()))
            
            results = cursor.fetchall()
            if results:
                df = pd.DataFrame(results, columns=['date', 'price', 'volume', 'market_cap'])
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                return df
            else:
                logger.warning(f"未找到{start_date.date()}到{end_date.date()}的历史数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取价格历史失败: {e}")
            return pd.DataFrame()
        finally:
            cursor.close()
            conn.close()
    
    def run_real_backtest(self, strategy: str, start_date: str, end_date: str, 
                         initial_btc: float, portfolio_params: Dict) -> Dict:
        """运行基于真实历史数据的回测"""
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 获取历史价格数据
            price_df = self.get_price_history(start_dt, end_dt)
            
            if price_df.empty:
                # 如果数据库没有数据，尝试从API获取
                days_diff = (end_dt - start_dt).days
                historical_data = self.fetch_coingecko_historical_data(days_diff + 30)
                
                if historical_data:
                    # 存储到数据库
                    self.store_historical_data(historical_data)
                    # 重新获取
                    price_df = self.get_price_history(start_dt, end_dt)
                
                if price_df.empty:
                    return {'success': False, 'error': '无法获取历史数据'}
            
            # 执行回测逻辑
            return self._execute_backtest_strategy(
                price_df, strategy, initial_btc, portfolio_params
            )
            
        except Exception as e:
            logger.error(f"回测执行失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_backtest_strategy(self, price_df: pd.DataFrame, strategy: str, 
                                   initial_btc: float, portfolio_params: Dict) -> Dict:
        """执行回测策略"""
        try:
            prices = price_df['price'].values
            dates = price_df.index
            
            # 初始化回测参数
            btc_holdings = initial_btc
            cash_holdings = 0
            trades = []
            portfolio_values = []
            
            # 简化的卖出策略示例
            if strategy == 'layered_selling':
                # 分层卖出策略
                sell_levels = [1.1, 1.2, 1.3, 1.5]  # 10%, 20%, 30%, 50%利润时卖出
                avg_cost_basis = portfolio_params.get('avg_cost_basis', prices[0])
                
                for i, (date, price) in enumerate(zip(dates, prices)):
                    current_profit_ratio = price / avg_cost_basis
                    
                    # 检查卖出条件
                    for level in sell_levels:
                        if current_profit_ratio >= level and btc_holdings > 0:
                            sell_amount = btc_holdings * 0.1  # 每次卖出10%
                            if sell_amount > 0:
                                cash_holdings += sell_amount * price * 0.9975  # 扣除0.25%手续费
                                btc_holdings -= sell_amount
                                
                                trades.append({
                                    'date': date.strftime('%Y-%m-%d'),
                                    'type': 'sell',
                                    'amount': sell_amount,
                                    'price': price,
                                    'reason': f'Profit target {level:.1%}'
                                })
                    
                    # 计算当前投资组合价值
                    portfolio_value = btc_holdings * price + cash_holdings
                    portfolio_values.append(portfolio_value)
            
            elif strategy == 'hold':
                # 持有策略
                for price in prices:
                    portfolio_value = btc_holdings * price + cash_holdings
                    portfolio_values.append(portfolio_value)
            
            else:
                # 默认HODL策略
                for price in prices:
                    portfolio_value = btc_holdings * price + cash_holdings
                    portfolio_values.append(portfolio_value)
            
            # 计算回测指标
            portfolio_values = np.array(portfolio_values)
            initial_value = portfolio_values[0]
            final_value = portfolio_values[-1]
            
            # 计算日收益率
            daily_returns = np.diff(portfolio_values) / portfolio_values[:-1]
            
            # 计算指标
            total_return = ((final_value - initial_value) / initial_value) * 100
            
            # 计算最大回撤
            cumulative_max = np.maximum.accumulate(portfolio_values)
            drawdowns = (portfolio_values - cumulative_max) / cumulative_max * 100
            max_drawdown = abs(np.min(drawdowns))
            
            # 计算夏普比率（假设无风险收益率为0）
            if len(daily_returns) > 1 and np.std(daily_returns) > 0:
                sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(365)
            else:
                sharpe_ratio = 0
            
            # 计算胜率
            win_rate = (len([r for r in daily_returns if r > 0]) / len(daily_returns) * 100) if len(daily_returns) > 0 else 0
            
            # 构建回测结果
            result_dates = [d.strftime('%m-%d') for d in dates[-30:]]  # 最近30天
            result_values = portfolio_values[-30:].tolist()  # 最近30天的投资组合价值
            
            return {
                'success': True,
                'result': {
                    'dates': result_dates,
                    'values': result_values,
                    'total_return': round(total_return, 2),
                    'max_drawdown': round(max_drawdown, 2),
                    'sharpe_ratio': round(sharpe_ratio, 2),
                    'win_rate': round(win_rate, 1),
                    'total_trades': len(trades),
                    'final_btc_holdings': round(btc_holdings, 4),
                    'final_cash_holdings': round(cash_holdings, 2),
                    'data_source': 'historical_data',
                    'price_range': {
                        'start_price': float(prices[0]),
                        'end_price': float(prices[-1]),
                        'min_price': float(np.min(prices)),
                        'max_price': float(np.max(prices))
                    },
                    'trades_sample': trades[-5:] if trades else []  # 最近5笔交易
                }
            }
            
        except Exception as e:
            logger.error(f"回测策略执行失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_historical_data_daily(self):
        """每日更新历史数据"""
        try:
            # 获取最近7天的数据（包含今天）
            recent_data = self.fetch_coingecko_historical_data(7)
            if recent_data:
                self.store_historical_data(recent_data)
                logger.info("历史数据每日更新完成")
                return True
            else:
                logger.warning("历史数据更新失败")
                return False
        except Exception as e:
            logger.error(f"每日历史数据更新失败: {e}")
            return False

# 全局实例
historical_engine = HistoricalDataEngine()