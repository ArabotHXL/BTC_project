#!/usr/bin/env python3
"""
用户投资组合管理系统
替换Treasury Overview中的硬编码估算数据
"""

import os
import logging
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)

@dataclass
class PortfolioSnapshot:
    """投资组合快照数据"""
    user_id: int
    btc_inventory: float
    avg_cost_basis: float
    cash_reserves: float
    monthly_opex: float
    electricity_cost_kwh: float
    facility_capacity_mw: float
    recorded_at: datetime
    notes: str = ""

class UserPortfolioManager:
    """用户投资组合管理器"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def create_portfolio_table(self):
        """创建用户投资组合表"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_portfolios (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    btc_inventory DECIMAL(12, 8) NOT NULL DEFAULT 0,
                    avg_cost_basis DECIMAL(12, 2) NOT NULL DEFAULT 0,
                    cash_reserves DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    monthly_opex DECIMAL(12, 2) NOT NULL DEFAULT 0,
                    electricity_cost_kwh DECIMAL(6, 4) NOT NULL DEFAULT 0.05,
                    facility_capacity_mw DECIMAL(8, 3) NOT NULL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    
                    FOREIGN KEY (user_id) REFERENCES user_access(id) ON DELETE CASCADE,
                    UNIQUE(user_id)
                );
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON user_portfolios(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolios_active ON user_portfolios(is_active);")
            
            # 创建投资组合历史记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id SERIAL PRIMARY KEY,
                    portfolio_id INTEGER NOT NULL,
                    snapshot_date TIMESTAMP NOT NULL,
                    btc_inventory DECIMAL(12, 8) NOT NULL,
                    btc_price_usd DECIMAL(12, 2) NOT NULL,
                    inventory_value_usd DECIMAL(15, 2) NOT NULL,
                    unrealized_pl_percent DECIMAL(8, 4) NOT NULL,
                    cash_reserves DECIMAL(15, 2) NOT NULL,
                    total_portfolio_value DECIMAL(15, 2) NOT NULL,
                    
                    FOREIGN KEY (portfolio_id) REFERENCES user_portfolios(id) ON DELETE CASCADE
                );
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_portfolio_date ON portfolio_history(portfolio_id, snapshot_date);")
            
            conn.commit()
            logger.info("用户投资组合表创建完成")
            return True
            
        except Exception as e:
            logger.error(f"创建投资组合表失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_user_portfolio(self, user_id: int) -> Optional[Dict]:
        """获取用户投资组合数据"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    btc_inventory, avg_cost_basis, cash_reserves, monthly_opex,
                    electricity_cost_kwh, facility_capacity_mw, last_updated, notes
                FROM user_portfolios 
                WHERE user_id = %s AND is_active = TRUE
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'btc_inventory': float(result[0]),
                    'avg_cost_basis': float(result[1]),
                    'cash_reserves': float(result[2]),
                    'monthly_opex': float(result[3]),
                    'electricity_cost_kwh': float(result[4]),
                    'facility_capacity_mw': float(result[5]),
                    'last_updated': result[6],
                    'notes': result[7] or "",
                    'data_source': 'user_configured'
                }
            else:
                # 返回默认示例数据（用于演示）
                return self._get_demo_portfolio_data()
                
        except Exception as e:
            logger.error(f"获取用户投资组合失败: {e}")
            return self._get_demo_portfolio_data()
        finally:
            cursor.close()
            conn.close()
    
    def _get_demo_portfolio_data(self) -> Dict:
        """获取演示投资组合数据"""
        return {
            'btc_inventory': 12.5,
            'avg_cost_basis': 95000,
            'cash_reserves': 600000,        # $600K 现金储备 (修改以显示Cash Coverage计算差异)
            'monthly_opex': 200000,         # $200K 月度运营支出 (修改以显示Cash Coverage计算差异)
            'electricity_cost_kwh': 0.055,
            'facility_capacity_mw': 25.0,
            'max_daily_sell_pct': 0.25,    # 25% 最大日卖出比例限制
            'last_updated': datetime.now(),
            'notes': "Demo Portfolio - Configure your real data in Settings",
            'data_source': 'demo'
        }
    
    def create_or_update_portfolio(self, user_id: int, portfolio_data: Dict) -> bool:
        """创建或更新用户投资组合"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute("SELECT id FROM user_portfolios WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有记录
                cursor.execute("""
                    UPDATE user_portfolios SET
                        btc_inventory = %s,
                        avg_cost_basis = %s,
                        cash_reserves = %s,
                        monthly_opex = %s,
                        electricity_cost_kwh = %s,
                        facility_capacity_mw = %s,
                        last_updated = CURRENT_TIMESTAMP,
                        notes = %s
                    WHERE user_id = %s
                """, (
                    portfolio_data.get('btc_inventory', 0),
                    portfolio_data.get('avg_cost_basis', 0),
                    portfolio_data.get('cash_reserves', 0),
                    portfolio_data.get('monthly_opex', 0),
                    portfolio_data.get('electricity_cost_kwh', 0.05),
                    portfolio_data.get('facility_capacity_mw', 0),
                    portfolio_data.get('notes', ''),
                    user_id
                ))
                
                logger.info(f"更新用户投资组合: user_id={user_id}")
            else:
                # 创建新记录
                cursor.execute("""
                    INSERT INTO user_portfolios (
                        user_id, btc_inventory, avg_cost_basis, cash_reserves,
                        monthly_opex, electricity_cost_kwh, facility_capacity_mw, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    portfolio_data.get('btc_inventory', 0),
                    portfolio_data.get('avg_cost_basis', 0),
                    portfolio_data.get('cash_reserves', 0),
                    portfolio_data.get('monthly_opex', 0),
                    portfolio_data.get('electricity_cost_kwh', 0.05),
                    portfolio_data.get('facility_capacity_mw', 0),
                    portfolio_data.get('notes', '')
                ))
                
                logger.info(f"创建用户投资组合: user_id={user_id}")
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"保存用户投资组合失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def calculate_portfolio_metrics(self, portfolio_data: Dict, current_btc_price: float) -> Dict:
        """计算投资组合关键指标"""
        btc_inventory = portfolio_data.get('btc_inventory', 0)
        avg_cost_basis = portfolio_data.get('avg_cost_basis', 0)
        cash_reserves = portfolio_data.get('cash_reserves', 0)
        monthly_opex = portfolio_data.get('monthly_opex', 0)
        
        # 计算关键指标
        inventory_usd = btc_inventory * current_btc_price
        
        # 未实现盈亏
        if avg_cost_basis > 0:
            unrealized_pl = ((current_btc_price - avg_cost_basis) / avg_cost_basis) * 100
        else:
            unrealized_pl = 0
        
        # 现金覆盖天数计算修正
        if monthly_opex > 0:
            cash_coverage_days = int((cash_reserves / monthly_opex) * 30) if monthly_opex > 0 else 999
        else:
            cash_coverage_days = 999
        
        # 下月到期金额（包括10%缓冲）
        next_month_due = monthly_opex * 1.1
        
        # 总投资组合价值
        total_value = inventory_usd + cash_reserves
        
        return {
            'btc_inventory': btc_inventory,
            'btc_price': current_btc_price,
            'avg_cost_basis': avg_cost_basis,
            'inventory_usd': inventory_usd,
            'unrealized_pl': unrealized_pl,
            'cash_coverage_days': cash_coverage_days,
            'next_month_due': next_month_due,
            'cash_reserves': cash_reserves,
            'monthly_opex': monthly_opex,
            'total_portfolio_value': total_value,
            'portfolio_allocation': {
                'btc_percent': (inventory_usd / total_value * 100) if total_value > 0 else 0,
                'cash_percent': (cash_reserves / total_value * 100) if total_value > 0 else 0
            }
        }
    
    def record_daily_snapshot(self, user_id: int, current_btc_price: float):
        """记录每日投资组合快照"""
        portfolio_data = self.get_user_portfolio(user_id)
        if not portfolio_data:
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 获取投资组合ID
            cursor.execute("SELECT id FROM user_portfolios WHERE user_id = %s", (user_id,))
            portfolio_result = cursor.fetchone()
            if not portfolio_result:
                return False
            
            portfolio_id = portfolio_result[0]
            
            # 计算指标
            metrics = self.calculate_portfolio_metrics(portfolio_data, current_btc_price)
            
            # 检查今天是否已有快照
            today = datetime.now().date()
            cursor.execute("""
                SELECT id FROM portfolio_history 
                WHERE portfolio_id = %s AND DATE(snapshot_date) = %s
            """, (portfolio_id, today))
            
            if cursor.fetchone():
                # 更新今天的快照
                cursor.execute("""
                    UPDATE portfolio_history SET
                        btc_inventory = %s,
                        btc_price_usd = %s,
                        inventory_value_usd = %s,
                        unrealized_pl_percent = %s,
                        cash_reserves = %s,
                        total_portfolio_value = %s
                    WHERE portfolio_id = %s AND DATE(snapshot_date) = %s
                """, (
                    metrics['btc_inventory'], metrics['btc_price'],
                    metrics['inventory_usd'], metrics['unrealized_pl'],
                    metrics['cash_reserves'], metrics['total_portfolio_value'],
                    portfolio_id, today
                ))
            else:
                # 创建新的快照
                cursor.execute("""
                    INSERT INTO portfolio_history (
                        portfolio_id, snapshot_date, btc_inventory, btc_price_usd,
                        inventory_value_usd, unrealized_pl_percent, cash_reserves,
                        total_portfolio_value
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    portfolio_id, datetime.now(),
                    metrics['btc_inventory'], metrics['btc_price'],
                    metrics['inventory_usd'], metrics['unrealized_pl'],
                    metrics['cash_reserves'], metrics['total_portfolio_value']
                ))
            
            conn.commit()
            logger.info(f"投资组合快照已记录: user_id={user_id}, BTC=${current_btc_price}")
            return True
            
        except Exception as e:
            logger.error(f"记录投资组合快照失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

# 全局实例
portfolio_manager = UserPortfolioManager()