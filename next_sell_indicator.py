"""
Next Sell Price Indicator - HashInsight Treasury
智能卖出建议系统，基于分层策略、波动率调整和技术分析
"""

from typing import Dict, List, Optional, Tuple, TypedDict
import math
from dataclasses import dataclass
from datetime import datetime

class NextSellInput(TypedDict):
    """输入参数结构"""
    spot: float                      # 当前价格
    inventory_btc: float            # BTC库存
    blended_cost: float            # 混合成本基准
    max_daily_sell_pct: float      # 最大日卖百分比 (0.10 ~ 0.25)
    next_base_multiple: float       # 下一未触发分层倍数，如 1.5
    next_quota_pct: float          # 该层配额百分比，如 0.15
    rsi14: float                   # 14日RSI
    rsi_filter: float              # RSI过滤阈值，通常65
    atr_pct: float                 # ATR百分比 (ATR/Close)
    atr_pct_median_365: float      # 365日ATR中位数
    k_atr: float                   # ATR系数 (3~5)
    confluence: Optional[Dict]      # 共振阻力 {'strength': float, 'center_px': float}
    slip_pct: float                # 滑点容忍度 0.002 = 0.2%
    trailing_stop_px: float        # 保护止损价
    opex_gap_usd: float           # OPEX缺口金额，0表示无缺口

class NextSellOutput(TypedDict):
    """输出结果结构"""
    next_price: int                # 目标中价
    zone_low: int                  # 目标区间下限
    zone_high: int                 # 目标区间上限
    qty_btc: float                # 建议数量
    confidence: str                # 置信度: 'high'|'medium'|'low'
    reasons: List[str]             # 推理过程
    fallback_stop: int            # 保护止损价
    proximity_pct: float          # 当前价格接近度百分比
    opex_reserved_btc: float      # 为OPEX预留的BTC数量
    timestamp: str                # 时间戳
    status: str                   # 状态
    layer: str                    # 层级

@dataclass
class NextSellIndicator:
    """Next Sell Price 指标计算器"""
    
    @staticmethod
    def compute_next_sell_indicator(input_data: NextSellInput) -> NextSellOutput:
        """
        计算下一个卖出建议指标
        """
        reasons = []
        
        # 1) ATR 自适应层价调整
        atr_factor = max(0, input_data['atr_pct'] - input_data['atr_pct_median_365'])
        factor = min(max(1 + input_data['k_atr'] * atr_factor, 0.9), 1.4)
        adj_multiple = input_data['next_base_multiple'] * factor
        target = input_data['blended_cost'] * adj_multiple
        
        reasons.append(f"Ladder {input_data['next_base_multiple']:.2f}× → adj {adj_multiple:.2f}×")
        
        # 2) 目标区间计算
        zone_low = target * (1 - input_data['slip_pct'])
        zone_high = target * (1 + input_data['slip_pct'])
        
        # 3) 共振阻力位调整
        confluence = input_data.get('confluence')
        if confluence and confluence.get('strength', 0) >= 0.6:
            
            confluence_strength = confluence['strength']
            # 区间宽度 0.2%~0.3% 基于强度
            width = 0.002 + 0.001 * (confluence_strength - 0.6)
            target = confluence['center_px']
            zone_low = target * (1 - width)
            zone_high = target * (1 + width)
            
            reasons.append(f"S/R confluence near ${int(target)} (strength {confluence_strength:.2f})")
        
        # 4) 数量计算（先预留OPEX缺口）
        opex_qty = 0
        if input_data['opex_gap_usd'] > 0:
            opex_qty = input_data['opex_gap_usd'] / max(input_data['spot'], 1e-9)
            
        daily_cap = input_data['inventory_btc'] * input_data['max_daily_sell_pct']
        layer_qty = input_data['inventory_btc'] * input_data['next_quota_pct']
        qty = min(daily_cap, max(0, layer_qty - opex_qty))
        
        # 小额时保底
        if qty < 1e-4:
            qty = max(0, min(daily_cap, layer_qty))
            
        # 5) 置信度评估
        confidence = 'medium'
        if input_data['rsi14'] >= input_data['rsi_filter']:
            confidence = 'high'
        elif input_data['spot'] < zone_low * 0.98:  # 价格离目标较远
            confidence = 'low'
            
        rsi_status = '≥' if input_data['rsi14'] >= input_data['rsi_filter'] else '<'
        reasons.append(f"RSI {input_data['rsi14']:.1f} {rsi_status} {input_data['rsi_filter']}")
        
        # 6) 接近度计算
        proximity_pct = (input_data['spot'] / target) * 100 if target > 0 else 0
        
        return NextSellOutput(
            next_price=int(round(target)),
            zone_low=int(round(zone_low)),
            zone_high=int(round(zone_high)),
            qty_btc=round(qty, 4),
            confidence=confidence,
            reasons=reasons,
            fallback_stop=int(round(input_data['trailing_stop_px'])),
            proximity_pct=round(proximity_pct, 1),
            opex_reserved_btc=round(opex_qty, 4)
        )
    
    @staticmethod
    def get_sample_calculation() -> NextSellOutput:
        """
        获取示例计算结果（用于演示）
        """
        sample_input: NextSellInput = {
            'spot': 113800,
            'inventory_btc': 5.0,
            'blended_cost': 75000,
            'max_daily_sell_pct': 0.25,
            'next_base_multiple': 1.52,
            'next_quota_pct': 0.15,
            'rsi14': 68.5,
            'rsi_filter': 65,
            'atr_pct': 0.025,
            'atr_pct_median_365': 0.022,
            'k_atr': 3.5,
            'confluence': {'strength': 0.75, 'center_px': 113800},
            'slip_pct': 0.002,
            'trailing_stop_px': 104120,
            'opex_gap_usd': 0
        }
        
        return NextSellIndicator.compute_next_sell_indicator(sample_input)

def get_next_sell_recommendation(user_id: int = 1) -> Dict:
    """
    获取用户的下一步卖出建议
    集成用户投资组合数据和当前市场状况
    """
    try:
        # 延迟导入避免循环依赖
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        
        try:
            from user_portfolio_management import portfolio_manager
            from models import TechnicalIndicator, MarketAnalytics
        except ImportError as e:
            return {"error": f"Import failed: {str(e)}"}
        from datetime import datetime, timedelta
        import numpy as np
        
        # 获取用户投资组合
        portfolio = portfolio_manager.get_user_portfolio(user_id)
        if not portfolio:
            return {"error": "Portfolio not found"}
            
        # 获取最新技术指标
        latest_tech = TechnicalIndicator.query.order_by(TechnicalIndicator.timestamp.desc()).first()
        if not latest_tech:
            return {"error": "Technical indicators not available"}
            
        # 获取最新市场数据
        latest_market = MarketAnalytics.query.order_by(MarketAnalytics.timestamp.desc()).first()
        if not latest_market:
            return {"error": "Market data not available"}
            
        # 计算ATR中位数（简化版，使用当前ATR的0.9倍作为中位数）
        atr_pct = (latest_tech.atr or 2500) / latest_market.btc_price
        atr_median = atr_pct * 0.9  # 简化估算
        
        # 构建输入参数
        input_data: NextSellInput = {
            'spot': latest_market.btc_price,
            'inventory_btc': portfolio.get('btc_inventory', 5.0),
            'blended_cost': portfolio.get('avg_cost_basis', 75000),  # 修复字段名
            'max_daily_sell_pct': portfolio.get('max_daily_sell_pct', 0.15),
            'next_base_multiple': 1.52,  # L2 层级
            'next_quota_pct': 0.15,      # 15%配额
            'rsi14': latest_tech.rsi or 50,
            'rsi_filter': 65,
            'atr_pct': atr_pct,
            'atr_pct_median_365': atr_median,
            'k_atr': 3.5,
            'confluence': None,  # 暂不实现共振阻力检测
            'slip_pct': 0.002,
            'trailing_stop_px': latest_market.btc_price * 0.85,  # 15%止损
            'opex_gap_usd': max(0, portfolio.get('monthly_opex', 50000) - portfolio.get('cash_reserves', 100000))
        }
        
        # 计算建议
        result = NextSellIndicator.compute_next_sell_indicator(input_data)
        
        # 添加时间戳和状态
        result['timestamp'] = datetime.utcnow().isoformat()
        result['status'] = 'active'
        result['layer'] = 'L2'
        
        return {'success': True, 'data': result}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    # 测试样例
    sample = NextSellIndicator.get_sample_calculation()
    print("Next Sell Indicator Sample:")
    print(f"Target: ${sample['next_price']:,}")
    print(f"Zone: ${sample['zone_low']:,} - ${sample['zone_high']:,}")
    print(f"Quantity: {sample['qty_btc']} BTC")
    print(f"Confidence: {sample['confidence']}")
    print(f"Proximity: {sample['proximity_pct']}%")
    print("Reasons:")
    for reason in sample['reasons']:
        print(f"  • {reason}")