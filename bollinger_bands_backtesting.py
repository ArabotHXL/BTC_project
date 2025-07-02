"""
布林带策略回测系统
Bollinger Bands Strategy Backtesting System

实现布林带交易策略的历史回测，计算策略收益并与持有策略对比
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import psycopg2
import os
from dataclasses import dataclass
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """交易记录"""
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    trade_type: str = "buy"  # "buy" or "sell"
    profit_pct: Optional[float] = None
    
@dataclass
class BacktestResult:
    """回测结果"""
    strategy_return: float
    buy_hold_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Trade]
    equity_curve: List[Dict]

class BollingerBandsBacktester:
    """布林带策略回测器"""
    
    def __init__(self):
        self.db_url = os.environ.get("DATABASE_URL")
        
    def get_connection(self):
        """获取数据库连接"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def get_historical_data(self, days: int = 30) -> pd.DataFrame:
        """获取历史价格和布林带数据"""
        conn = self.get_connection()
        if not conn:
            return pd.DataFrame()
            
        try:
            # 获取市场数据和技术指标
            query = """
            SELECT 
                ma.timestamp,
                ma.btc_price,
                ti.bollinger_upper,
                ti.bollinger_lower,
                ti.sma_20,
                ti.rsi_14
            FROM market_analytics ma
            LEFT JOIN technical_indicators ti ON DATE(ma.timestamp) = DATE(ti.timestamp)
            WHERE ma.timestamp >= %s
            AND ma.btc_price IS NOT NULL
            AND ti.bollinger_upper IS NOT NULL
            AND ti.bollinger_lower IS NOT NULL
            ORDER BY ma.timestamp ASC
            """
            
            start_date = datetime.now() - timedelta(days=days)
            df = pd.read_sql_query(query, conn, params=[start_date])
            
            if df.empty:
                logger.warning("未找到足够的历史数据")
                return pd.DataFrame()
                
            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.dropna()
            
            logger.info(f"获取到 {len(df)} 条历史数据记录")
            return df
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def calculate_bollinger_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算布林带交易信号"""
        if df.empty:
            return df
            
        df = df.copy()
        
        # 布林带策略信号
        # 买入信号：价格跌破下轨
        df['buy_signal'] = (df['btc_price'] < df['bollinger_lower']).astype(int)
        
        # 卖出信号：价格突破上轨
        df['sell_signal'] = (df['btc_price'] > df['bollinger_upper']).astype(int)
        
        # 计算价格相对于布林带的位置 (%B指标)
        df['bb_percent'] = (df['btc_price'] - df['bollinger_lower']) / (df['bollinger_upper'] - df['bollinger_lower'])
        
        # 带宽指标
        df['bb_width'] = (df['bollinger_upper'] - df['bollinger_lower']) / df['sma_20']
        
        return df
    
    def simulate_strategy(self, df: pd.DataFrame, initial_capital: float = 10000) -> BacktestResult:
        """模拟布林带交易策略"""
        if df.empty:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0, [], [])
            
        trades = []
        equity_curve = []
        position = 0  # 0: 空仓, 1: 持有
        entry_price = 0
        entry_time = None
        capital = initial_capital
        equity = initial_capital
        
        # 记录初始状态
        equity_curve.append({
            'timestamp': df.iloc[0]['timestamp'],
            'strategy_equity': equity,
            'buy_hold_equity': initial_capital,
            'btc_price': df.iloc[0]['btc_price'],
            'position': position
        })
        
        for i, row in df.iterrows():
            current_price = row['btc_price']
            current_time = row['timestamp']
            
            # 买入信号且当前空仓
            if row['buy_signal'] == 1 and position == 0:
                position = 1
                entry_price = current_price
                entry_time = current_time
                
                # 记录买入交易
                trade = Trade(
                    entry_time=current_time,
                    entry_price=current_price,
                    trade_type="buy"
                )
                trades.append(trade)
                
            # 卖出信号且当前持有
            elif row['sell_signal'] == 1 and position == 1:
                position = 0
                exit_price = current_price
                exit_time = current_time
                
                # 计算收益
                profit_pct = (exit_price - entry_price) / entry_price
                capital *= (1 + profit_pct)
                equity = capital
                
                # 更新最后一笔交易
                if trades:
                    trades[-1].exit_time = exit_time
                    trades[-1].exit_price = exit_price
                    trades[-1].profit_pct = profit_pct
            
            # 计算Buy & Hold收益
            buy_hold_equity = initial_capital * (current_price / df.iloc[0]['btc_price'])
            
            # 如果持有仓位，计算当前未实现收益
            if position == 1:
                unrealized_profit_pct = (current_price - entry_price) / entry_price
                current_equity = capital * (1 + unrealized_profit_pct)
            else:
                current_equity = equity
            
            # 记录权益曲线
            equity_curve.append({
                'timestamp': current_time,
                'strategy_equity': current_equity,
                'buy_hold_equity': buy_hold_equity,
                'btc_price': current_price,
                'position': position,
                'bb_upper': row['bollinger_upper'],
                'bb_lower': row['bollinger_lower'],
                'buy_signal': row['buy_signal'],
                'sell_signal': row['sell_signal']
            })
        
        # 计算最终收益
        final_strategy_equity = equity_curve[-1]['strategy_equity']
        final_buy_hold_equity = equity_curve[-1]['buy_hold_equity']
        
        strategy_return = (final_strategy_equity - initial_capital) / initial_capital
        buy_hold_return = (final_buy_hold_equity - initial_capital) / initial_capital
        
        # 计算交易统计
        completed_trades = [t for t in trades if t.exit_price is not None]
        total_trades = len(completed_trades)
        winning_trades = len([t for t in completed_trades if t.profit_pct > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 计算最大回撤
        equity_values = [eq['strategy_equity'] for eq in equity_curve]
        max_drawdown = self.calculate_max_drawdown(equity_values)
        
        # 计算夏普比率（简化版本）
        returns = [eq['strategy_equity'] / initial_capital - 1 for eq in equity_curve[1:]]
        sharpe_ratio = self.calculate_sharpe_ratio(returns)
        
        return BacktestResult(
            strategy_return=strategy_return,
            buy_hold_return=buy_hold_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=completed_trades,
            equity_curve=equity_curve
        )
    
    def calculate_max_drawdown(self, equity_values: List[float]) -> float:
        """计算最大回撤"""
        if not equity_values:
            return 0
            
        peak = equity_values[0]
        max_dd = 0
        
        for value in equity_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
                
        return max_dd
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if not returns:
            return 0
            
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 365)  # 日化无风险收益率
        
        if np.std(excess_returns) == 0:
            return 0
            
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(365)
    
    def run_backtest(self, days: int = 30, initial_capital: float = 10000) -> Dict:
        """运行完整的回测"""
        logger.info(f"开始布林带策略回测，历史数据: {days} 天")
        
        # 获取历史数据
        df = self.get_historical_data(days)
        if df.empty:
            return {
                'success': False,
                'error': '无法获取足够的历史数据',
                'data': None
            }
        
        # 计算交易信号
        df = self.calculate_bollinger_signals(df)
        
        # 运行策略模拟
        result = self.simulate_strategy(df, initial_capital)
        
        # 准备返回数据
        return {
            'success': True,
            'data': {
                'strategy_return_pct': round(result.strategy_return * 100, 2),
                'buy_hold_return_pct': round(result.buy_hold_return * 100, 2),
                'outperformance_pct': round((result.strategy_return - result.buy_hold_return) * 100, 2),
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate_pct': round(result.win_rate * 100, 2),
                'max_drawdown_pct': round(result.max_drawdown * 100, 2),
                'sharpe_ratio': round(result.sharpe_ratio, 2),
                'equity_curve': result.equity_curve,
                'trades': [
                    {
                        'entry_time': trade.entry_time.isoformat(),
                        'entry_price': trade.entry_price,
                        'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                        'exit_price': trade.exit_price,
                        'profit_pct': round(trade.profit_pct * 100, 2) if trade.profit_pct else None
                    }
                    for trade in result.trades
                ],
                'data_points': len(df),
                'period_days': days,
                'initial_capital': initial_capital
            }
        }

def main():
    """测试函数"""
    backtester = BollingerBandsBacktester()
    result = backtester.run_backtest(days=7, initial_capital=10000)
    
    if result['success']:
        data = result['data']
        print(f"布林带策略回测结果:")
        print(f"策略收益: {data['strategy_return_pct']}%")
        print(f"持有收益: {data['buy_hold_return_pct']}%")
        print(f"超额收益: {data['outperformance_pct']}%")
        print(f"总交易次数: {data['total_trades']}")
        print(f"胜率: {data['win_rate_pct']}%")
        print(f"最大回撤: {data['max_drawdown_pct']}%")
        print(f"夏普比率: {data['sharpe_ratio']}")
    else:
        print(f"回测失败: {result['error']}")

if __name__ == "__main__":
    main()