"""
高级算法交易策略引擎 - Phase 1实施
包含：Regime-Aware、Adaptive-ATR、Support/Resistance Confluence
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, NamedTuple, Union
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import translation function
try:
    from language_engine import language_engine
    ENHANCED_LANGUAGE = True
except ImportError:
    from translations import get_translation
    ENHANCED_LANGUAGE = False

def tr(text: str, **kwargs) -> str:
    """翻译函数，支持变量插值"""
    if ENHANCED_LANGUAGE:
        return language_engine.translate(text, **kwargs)
    else:
        from flask import g
        lang = getattr(g, 'language', 'en')
        return get_translation(text, to_lang=lang)

@dataclass
class FeaturePack:
    """特征数据包"""
    # 价格数据
    close: float
    high: float
    low: float
    
    # 移动平均线
    ma50: float
    ma200: float
    
    # 技术指标
    atr_pct: float
    pct_52w: float
    rsi14: float
    
    # 成交量
    vol_20d: float
    vol_today: float
    
    # 布林带和唐奇安通道
    donchian_20_high: float
    bb_upper: float
    bb_lower: float
    
    # 支撑阻力位
    sr_bands: List[Dict[str, float]] = field(default_factory=list)
    
    # 矿工数据（可选）
    hashprice_pctile: Optional[float] = None
    puell: Optional[float] = None

@dataclass
class ModuleScore:
    """模块评分结果"""
    name: str
    score: float  # -1到1之间
    confidence: float  # 0到1之间
    notes: List[str] = field(default_factory=list)

class AdvancedAlgorithmEngine:
    """高级算法策略引擎"""
    
    def __init__(self):
        self.atr_median_cache = None
        self.historical_data_cache = {}
        self.volume_cache = {}  # 量能数据缓存
        
    def calculate_atr_percentile(self, prices: List[float], periods: int = 14, lookback: int = 365) -> float:
        """计算ATR百分位数"""
        if len(prices) < periods + lookback:
            return 0.5  # 默认中位数
            
        atr_values = []
        for i in range(periods, len(prices)):
            high_low = max(prices[i-j] for j in range(periods)) - min(prices[i-j] for j in range(periods))
            atr_values.append(high_low / prices[i])
            
        if not atr_values:
            return 0.5
            
        return float(np.percentile(atr_values[-lookback:], 50))
    
    def regime_aware_module(self, features: FeaturePack, atr_median: float = 0.02) -> ModuleScore:
        """
        A. Regime-Aware 自适应模块
        判断趋势和波动状态，调整分层门槛
        """
        notes = []
        
        # 趋势判断：MA斜率
        if features.ma200 > 0:
            trend_slope = (features.ma50 - features.ma200) / features.ma200
            trend_up = trend_slope > 0.001  # 0.1%以上斜率认为上升趋势
        else:
            trend_up = features.ma50 > features.ma200
            
        # 波动判断：ATR相对位置
        low_volatility = features.atr_pct < 0.8 * atr_median
        high_volatility = features.atr_pct > 1.2 * atr_median
        
        # 价格位置：52周百分位
        high_price_zone = features.pct_52w > 0.75
        
        score = 0.0
        confidence = 0.7
        
        # 评分逻辑
        if trend_up and low_volatility:
            score += 0.2  # 上升趋势+低波动：提高门槛（延迟卖出）
            notes.append(tr("uptrend_low_vol"))
        elif not trend_up and high_volatility:
            score -= 0.3  # 下降趋势+高波动：降低门槛（加速卖出）
            notes.append(tr("downtrend_high_vol"))
        
        if high_price_zone and high_volatility:
            score += 0.15  # 高位+高波动：谨慎信号
            notes.append(tr("high_price_volatility"))
            
        return ModuleScore("regime_aware", score, confidence, notes)
    
    def adaptive_atr_module(self, features: FeaturePack, base_multiple: float = 2.0, 
                           atr_median: float = 0.02, k: float = 4.0) -> ModuleScore:
        """
        D. Adaptive-ATR 分层模块
        根据波动调整分层倍数
        """
        notes = []
        
        # 计算动态倍数
        atr_deviation = features.atr_pct - atr_median
        effective_multiple = base_multiple * (1 + k * max(0, atr_deviation))
        
        # 动能过滤
        momentum_confirmed = features.rsi14 >= 55  # RSI确认动能
        
        score = 0.0
        confidence = 0.8
        
        if effective_multiple > base_multiple * 1.3:
            score -= 0.1  # 高波动时拉远层距，减少卖出信号
            notes.append(tr("high_volatility_adjustment", multiple=f"{effective_multiple:.1f}"))
        elif effective_multiple < base_multiple * 0.8:
            score += 0.1  # 低波动时缩小层距，增加卖出机会
            notes.append(tr("low_volatility_adjustment", multiple=f"{effective_multiple:.1f}"))
            
        if momentum_confirmed:
            notes.append(tr("momentum_confirmed"))
        else:
            score -= 0.05  # 缺乏动能确认
            notes.append(tr("momentum_insufficient"))
            
        return ModuleScore("adaptive_atr", score, confidence, notes)
    
    def confluence_module(self, features: FeaturePack) -> ModuleScore:
        """
        C. 支撑/阻力共振模块
        识别价格聚集的支撑阻力区域
        """
        notes = []
        score = 0.0
        confidence = 0.6
        
        if not features.sr_bands:
            # 如果没有提供支撑阻力位，使用技术指标近似
            resistance_levels = [
                features.bb_upper,
                features.donchian_20_high,
                features.close * 1.02  # 简单的2%阻力位
            ]
            
            # 检查当前价格是否接近阻力位
            band_width = 0.003 * features.close  # ±0.3%
            
            near_resistance = False
            for level in resistance_levels:
                if abs(features.close - level) <= band_width:
                    near_resistance = True
                    notes.append(tr("near_resistance", level=f"${level:.0f}"))
                    break
            
            if near_resistance:
                # 检查拒绝形态（简化版）
                if features.close < features.high * 0.995:  # 收盘价低于最高价0.5%
                    score += 0.25
                    notes.append(tr("rejection_pattern_detected"))
                    confidence = 0.7
        else:
            # 使用提供的支撑阻力位
            band_width = 0.003 * features.close
            total_strength = 0
            
            for sr_level in features.sr_bands:
                if abs(features.close - sr_level['price']) <= band_width:
                    total_strength += sr_level['strength']
                    
            if total_strength >= 3:
                score += min(0.3, total_strength * 0.1)
                notes.append(tr("resonance_zone", strength=f"{total_strength:.1f}"))
                confidence = 0.8
        
        return ModuleScore("confluence", score, confidence, notes)
    
    def breakout_exhaustion_module(self, features: FeaturePack) -> ModuleScore:
        """
        D. 突破衰竭检测模块 (Phase 2)
        识别虚假突破和衰竭信号，防止追高风险
        """
        notes = []
        score = 0.0
        confidence = 0.7
        
        # 检查是否处于潜在突破位置
        near_resistance = features.close >= features.donchian_20_high * 0.995
        near_bb_upper = features.close >= features.bb_upper * 0.995
        
        if near_resistance or near_bb_upper:
            # 在阻力位附近，检查衰竭信号
            
            # 1. 成交量衰竭检查
            volume_exhaustion = False
            if hasattr(features, 'vol_today') and hasattr(features, 'vol_20d'):
                if features.vol_today < features.vol_20d * 0.8:  # 成交量低于20日均量80%
                    volume_exhaustion = True
                    score += 0.2  # 低量突破，偏向卖出
                    notes.append(tr("volume_exhaustion_signal"))
                    confidence = 0.8
            
            # 2. RSI背离检查 (简化版)
            if features.rsi14 > 75:  # 极度超买
                score += 0.25
                notes.append(tr("rsi_extremely_overbought"))
                confidence = 0.85
            elif features.rsi14 > 65:  # 超买区域
                score += 0.1
                notes.append(tr("rsi_overbought_watch"))
            
            # 3. 价格行为分析
            # 检查是否有长上影线（衰竭征象）
            if features.close < features.high * 0.98:  # 收盘价低于最高价2%
                score += 0.15
                notes.append(tr("long_upper_shadow"))
            
            # 4. ATR扩张检查
            if features.atr_pct > 0.08:  # ATR超过8%（高波动）
                score += 0.1
                notes.append(tr("volatility_expansion"))
        
        else:
            # 不在突破位置，降低衰竭模块权重
            score = 0.0
            notes.append(tr("module_inactive"))
            confidence = 0.3
        
        return ModuleScore("breakout_exhaustion", score, confidence, notes)
    
    def miner_cycle_module(self, features: FeaturePack) -> ModuleScore:
        """
        E. 挖矿周期整合模块 (Phase 2)  
        整合矿工行为和市场周期，提供宏观卖出时机
        """
        notes = []
        score = 0.0
        confidence = 0.6
        
        # 使用Puell Multiple评估矿工压力
        if features.puell is not None:
            if features.puell > 4.0:
                # 极高Puell Multiple，强烈卖出信号
                score += 0.4
                notes.append(tr("puell_extremely_high", value=f"{features.puell:.2f}"))
                confidence = 0.9
            elif features.puell > 2.5:
                # 高Puell Multiple，卖出信号
                score += 0.25
                notes.append(tr("puell_high", value=f"{features.puell:.2f}"))
                confidence = 0.8
            elif features.puell > 1.5:
                # 中性偏高区域
                score += 0.1
                notes.append(tr("puell_neutral", value=f"{features.puell:.2f}"))
            else:
                # 低Puell Multiple，矿工卖压较小
                score -= 0.1
                notes.append(tr("puell_low", value=f"{features.puell:.2f}"))
        
        # 使用Hash Price Percentile评估矿工盈利能力
        if features.hashprice_pctile is not None:
            if features.hashprice_pctile > 0.9:
                # 矿工处于极高盈利状态，卖出压力大
                score += 0.2
                notes.append(tr("hashprice_high", percentile=f"{features.hashprice_pctile*100:.0f}"))
                confidence = max(confidence, 0.8)
            elif features.hashprice_pctile > 0.7:
                # 矿工高盈利状态
                score += 0.1
                notes.append(tr("hashprice_elevated", percentile=f"{features.hashprice_pctile*100:.0f}"))
            elif features.hashprice_pctile < 0.3:
                # 矿工盈利较低，卖压减小
                score -= 0.1
                notes.append(tr("hashprice_low", percentile=f"{features.hashprice_pctile*100:.0f}"))
        
        # 价格位置与挖矿成本的关系
        if features.pct_52w > 0.8:
            # 价格处于52周高位，结合矿工指标
            if features.puell and features.puell > 2.0:
                score += 0.15
                notes.append(tr("sell_timing_optimal"))
                confidence = 0.85
        
        # 市场周期判断（基于移动平均线）
        if features.close > features.ma50 * 1.2:  # 价格显著高于50日MA
            score += 0.1
            notes.append(tr("price_overheated"))
        
        return ModuleScore("miner_cycle", score, confidence, notes)
    
    def pattern_target_module(self, features: FeaturePack) -> ModuleScore:
        """
        F. 形态目标引擎（Triangle/Rectangle/Channel）
        识别突破形态并计算价格目标
        """
        notes = []
        score = 0.0
        confidence = 0.6
        
        # 简化形态识别：使用布林带和移动平均线判断
        price_range = features.bb_upper - features.bb_lower
        range_pct = price_range / features.close
        
        # 识别收敛形态（窄幅震荡）
        if range_pct < 0.05:  # 布林带收窄，可能形成三角形
            notes.append(tr("convergence_pattern_detected"))
            
            # 检查突破
            if features.close > features.bb_upper * 0.998:  # 接近上轨突破
                # 计算目标位（形态高度投射）
                pattern_height = price_range
                target_0618 = features.close + pattern_height * 0.618
                target_100 = features.close + pattern_height * 1.0
                
                # 量能确认
                if features.vol_today > features.vol_20d * 1.5:
                    score += 0.2
                    notes.append(tr("pattern_breakout_confirmed", target=f"${target_0618:.0f}"))
                    confidence = 0.75
                else:
                    score += 0.1
                    notes.append(tr("pattern_breakout_weak_volume"))
                
        elif range_pct > 0.08:  # 宽幅震荡，矩形形态
            # 检查是否在阻力位附近
            if features.close > features.bb_upper * 0.995:
                score += 0.15
                notes.append(tr("rectangle_resistance_test"))
        
        # 通道形态检查（移动平均线发散）
        ma_spread = abs(features.ma50 - features.ma200) / features.close
        if ma_spread > 0.1:  # MA发散，可能是上升通道
            if features.close > features.ma50:
                notes.append(tr("uptrend_channel_active"))
            else:
                score += 0.1  # 跌破通道支撑，卖出信号
                notes.append(tr("channel_support_broken"))
                confidence = 0.7
        
        return ModuleScore("pattern_target", score, confidence, notes)
    
    def derivatives_pressure_module(self, features: FeaturePack) -> ModuleScore:
        """
        G. 衍生品压力与对冲选择
        监控期货基差和资金费率变化
        """
        notes = []
        score = 0.0
        confidence = 0.5  # 需要外部API数据，置信度较低
        
        # 模拟衍生品数据（实际应从交易所API获取）
        # 基于当前价格波动率估算
        estimated_funding_rate = features.atr_pct * 10  # ATR转换为年化基差估算
        basis_premium = min(0.15, estimated_funding_rate)  # 基差上限15%
        
        # 资金费率分析
        if basis_premium > 0.12:  # 年化基差>12%
            score += 0.3
            notes.append(tr("high_basis_premium", rate=f"{basis_premium*100:.1f}%"))
            notes.append(tr("hedge_opportunity"))
            confidence = 0.7
        elif basis_premium > 0.08:  # 年化基差>8%
            score += 0.15
            notes.append(tr("elevated_basis", rate=f"{basis_premium*100:.1f}%"))
        
        # 未平仓量变化（简化估算）
        # 基于RSI和价格位置推断市场情绪
        if features.rsi14 > 70 and features.pct_52w > 0.8:
            # 高位+超买，可能资金费率为正
            score += 0.1
            notes.append(tr("positive_funding_pressure"))
        elif features.rsi14 < 30:
            # 超卖，资金费率可能转负
            score += 0.15  # 防守性卖出信号
            notes.append(tr("negative_funding_defensive"))
            confidence = 0.6
        
        return ModuleScore("derivatives_pressure", score, confidence, notes)
    
    def microstructure_executor_module(self, features: FeaturePack) -> ModuleScore:
        """
        H. 微观结构执行器（Liquidity-Aware）
        基于流动性评估最优执行策略
        """
        notes = []
        score = 0.0
        confidence = 0.8
        
        # 使用24h成交量评估流动性
        daily_turnover = features.vol_today
        
        # 估算订单规模影响（假设卖出$100万）
        order_usd = 1000000  # $1M示例订单
        volume_ratio = order_usd / daily_turnover if daily_turnover > 0 else 1.0
        
        # 滑点估算
        estimated_slippage = volume_ratio * 0.5  # 简化滑点模型
        
        if estimated_slippage > 0.003:  # 滑点>0.3%
            # 建议TWAP执行
            window_minutes = int(60 * (volume_ratio ** 0.6))  # 执行时间窗口
            notes.append(tr("high_slippage_risk", slippage=f"{estimated_slippage*100:.2f}%"))
            notes.append(tr("recommend_twap", window=f"{window_minutes}min"))
            score -= 0.1  # 执行困难，降低卖出评分
        elif estimated_slippage > 0.001:  # 滑点>0.1%
            notes.append(tr("moderate_liquidity", slippage=f"{estimated_slippage*100:.2f}%"))
            notes.append(tr("recommend_split_orders"))
        else:
            notes.append(tr("excellent_liquidity"))
            score += 0.05  # 流动性充足，轻微加分
        
        # 市场深度评估（基于波动率）
        if features.atr_pct < 0.03:  # 低波动，通常意味着更好的流动性
            notes.append(tr("stable_market_conditions"))
            confidence = 0.85
        elif features.atr_pct > 0.08:  # 高波动，执行风险增加
            notes.append(tr("volatile_market_caution"))
            score -= 0.05
        
        return ModuleScore("microstructure", score, confidence, notes)
    
    def bandit_sizing_module(self, features: FeaturePack, historical_performance: Optional[Dict] = None) -> ModuleScore:
        """
        I. Bandit-Sizing（分层配额自学习）
        基于历史表现动态调整分层配额
        """
        notes = []
        score = 0.0
        confidence = 0.7
        
        # 简化的Thompson Sampling实现
        # 实际应维护beta分布参数并更新
        
        # 默认分层配额（5-25%范围）
        base_allocation = 0.15  # 15%基础配额
        
        # 基于历史表现调整（模拟数据）
        if historical_performance:
            avg_return = historical_performance.get('avg_return', 0.0)
            win_rate = historical_performance.get('win_rate', 0.5)
            
            if win_rate > 0.7 and avg_return > 0.02:
                # 历史表现优秀，增加配额
                adjusted_allocation = min(0.25, base_allocation * 1.3)
                score += 0.1
                notes.append(tr("increase_allocation", rate=f"{adjusted_allocation*100:.0f}%"))
            elif win_rate < 0.4:
                # 表现不佳，减少配额
                adjusted_allocation = max(0.05, base_allocation * 0.7)
                score -= 0.1
                notes.append(tr("reduce_allocation", rate=f"{adjusted_allocation*100:.0f}%"))
            else:
                adjusted_allocation = base_allocation
                notes.append(tr("maintain_allocation"))
        else:
            # 无历史数据，使用保守配额
            adjusted_allocation = 0.12
            notes.append(tr("conservative_sizing"))
        
        # 市场条件调整
        if features.atr_pct > 0.1:  # 高波动环境
            adjusted_allocation *= 0.8  # 减少单次卖出量
            notes.append(tr("volatility_size_reduction"))
        
        # 日卖出限制检查
        daily_limit = 0.5  # 假设单日最大卖出50%
        if adjusted_allocation > daily_limit:
            adjusted_allocation = daily_limit
            notes.append(tr("daily_limit_applied"))
        
        return ModuleScore("bandit_sizing", score, confidence, notes)
    
    def ensemble_aggregation_module(self, module_scores: List[ModuleScore], 
                                   priority_weights: Optional[Dict[str, float]] = None) -> Dict[str, Union[float, str, List[str], int]]:
        """
        J. Ensemble 聚合评分 → 单一"Sell Window"
        整合所有模块输出为统一决策信号
        """
        if priority_weights is None:
            # Phase 3 完整权重配置 - 10个模块
            priority_weights = {
                # 核心技术模块 (高权重)
                'regime_aware': 0.15,           # A - 趋势识别
                'breakout_exhaustion': 0.12,    # B - 突破衰竭
                'confluence': 0.12,             # C - 支撑阻力共振
                'adaptive_atr': 0.10,           # D - ATR自适应
                'pattern_target': 0.10,         # F - 形态目标
                
                # 宏观指标模块 (中权重)
                'miner_cycle': 0.12,            # E - 挖矿周期
                'derivatives_pressure': 0.08,   # G - 衍生品压力
                
                # 执行优化模块 (低权重)
                'microstructure': 0.06,         # H - 微观结构
                'bandit_sizing': 0.08,          # I - 配额自学习
                
                # OPEX/风控优先级 (动态调整)
                'opex_priority': 0.07,          # 运营费用覆盖
            }
        
        # 计算加权聚合得分
        weighted_sum = 0.0
        total_weight = 0.0
        all_notes = []
        confidence_avg = 0.0
        
        for module in module_scores:
            weight = priority_weights.get(module.name, 0.05)
            
            # 置信度调整权重
            adjusted_weight = weight * module.confidence
            weighted_sum += adjusted_weight * module.score
            total_weight += adjusted_weight
            
            # 收集重要信号
            if abs(module.score) > 0.1:  # 只保留重要信号
                all_notes.extend(module.notes[:2])  # 每个模块最多2条注释
            
            confidence_avg += module.confidence
        
        # 归一化得分
        if total_weight > 0:
            final_score = weighted_sum / total_weight
        else:
            final_score = 0.0
        
        confidence_avg = confidence_avg / len(module_scores) if module_scores else 0.0
        
        # 映射到0-100评分系统
        sell_score = max(0, min(100, 50 + 50 * final_score))
        
        # 三级决策阈值系统
        if sell_score >= 70:
            recommendation = "SELL"
            action_level = "High"
            # 添加紧急性提示
            if sell_score >= 85:
                all_notes.insert(0, tr("urgent_sell_signal"))
        elif sell_score >= 50:
            recommendation = "WATCH" 
            action_level = "Medium"
            # 添加观察要点
            all_notes.insert(0, tr("monitor_conditions"))
        else:
            recommendation = "HOLD"
            action_level = "Low"
            all_notes.insert(0, tr("maintain_position"))
        
        # 限制显示的注释数量，优先显示重要信息
        important_notes = all_notes[:6]
        
        return {
            'sell_score': round(sell_score, 1),
            'recommendation': recommendation, 
            'action_level': action_level,
            'confidence': round(confidence_avg, 2),
            'notes': important_notes,
            'raw_score': round(final_score, 3),
            'modules_count': len(module_scores),
            'phase': "Phase 3 (10 Modules: A-J)",
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_volume_average(self, days: int) -> Optional[float]:
        """获取历史量能平均值"""
        try:
            import os
            import time
            import psycopg2
            
            # 检查缓存
            cache_key = f"vol_{days}d"
            if cache_key in self.volume_cache:
                cache_time, value = self.volume_cache[cache_key]
                # 缓存5分钟有效
                if time.time() - cache_time < 300:
                    return value
            
            # 从数据库获取量能数据
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                return None
                
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT AVG(btc_volume_24h) 
                FROM market_analytics 
                WHERE btc_volume_24h IS NOT NULL 
                AND btc_volume_24h > 0
                AND recorded_at >= NOW() - INTERVAL '%s days'
            """, (days,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result and result[0]:
                avg_volume = float(result[0])
                # 更新缓存
                self.volume_cache[cache_key] = (time.time(), avg_volume)
                return avg_volume
            else:
                return None
                
        except Exception as e:
            logger.debug(f"获取量能平均值失败: {e}")
            return None
    
    def calculate_features_from_data(self, market_data: Dict, technical_data: Dict, 
                                    historical_prices: Optional[List[float]] = None) -> FeaturePack:
        """从市场数据计算特征包"""
        
        # 基础价格数据
        close = float(market_data.get('btc_price', 0))
        
        # 技术指标数据
        ma50 = float(technical_data.get('sma_50', close))
        ma200 = float(technical_data.get('sma_20', close))  # 暂用20日MA代替200日
        rsi14 = float(technical_data.get('rsi', 50))
        bb_upper = float(technical_data.get('bollinger_upper', close * 1.02))
        bb_lower = float(technical_data.get('bollinger_lower', close * 0.98))
        
        # ATR百分比（使用30天波动率）
        volatility = float(technical_data.get('volatility', 0.05))
        atr_pct = volatility / 100.0 if volatility > 1 else volatility  # 确保是小数格式
        
        # 52周百分位（估算）
        if historical_prices and len(historical_prices) >= 365:
            year_high = max(historical_prices[-365:])
            year_low = min(historical_prices[-365:])
            pct_52w = (close - year_low) / (year_high - year_low) if year_high > year_low else 0.5
        else:
            pct_52w = 0.75  # 假设当前在高位
        
        # 唐奇安通道（20日高点）
        donchian_20_high = close * 1.05  # 简化估算
        
        # 真实量能数据集成 ✅
        vol_today = float(market_data.get('btc_volume_24h', 20000000000))  # 实际24h成交量
        vol_20d = self.get_volume_average(20) or vol_today * 0.8  # 20日平均量，备用为当日80%
        
        return FeaturePack(
            close=close,
            high=close * 1.01,  # 估算
            low=close * 0.99,   # 估算
            ma50=ma50,
            ma200=ma200,
            atr_pct=atr_pct,
            pct_52w=pct_52w,
            rsi14=rsi14,
            vol_20d=vol_20d,    # 真实20日平均量
            vol_today=vol_today,  # 真实当日量
            donchian_20_high=donchian_20_high,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            hashprice_pctile=0.8,  # 估算矿工数据：80%分位（高盈利）
            puell=1.2,  # Puell Multiple：1.2（中性偏高）
            sr_bands=[]  # 支撑阻力位待完善
        )
    
    def aggregate_scores(self, module_scores: List[ModuleScore], 
                        weights: Optional[Dict[str, float]] = None) -> Dict[str, Union[float, str, List[str], int]]:
        """聚合各模块评分"""
        
        if weights is None:
            # Phase 2权重配置 - 5个模块均衡分布
            weights = {
                'regime_aware': 0.25,           # 模块A - 趋势识别
                'adaptive_atr': 0.20,           # 模块B - ATR自适应
                'confluence': 0.25,             # 模块C - 支撑阻力共振
                'breakout_exhaustion': 0.15,    # 模块D - 突破衰竭检测
                'miner_cycle': 0.15             # 模块E - 挖矿周期整合
            }
        
        weighted_sum = 0.0
        total_weight = 0.0
        all_notes = []
        confidence_avg = 0.0
        
        for module in module_scores:
            weight = weights.get(module.name, 1.0)
            weighted_sum += weight * module.score * module.confidence
            total_weight += weight * module.confidence
            all_notes.extend(module.notes)
            confidence_avg += module.confidence
            
        if total_weight > 0:
            final_score = weighted_sum / total_weight
        else:
            final_score = 0.0
            
        confidence_avg = confidence_avg / len(module_scores) if module_scores else 0.0
        
        # 映射到0-100分数
        sell_score = max(0, min(100, 50 + 50 * final_score))
        
        # 决策阈值
        if sell_score >= 70:
            recommendation = "SELL"
            action_level = "High"
        elif sell_score >= 50:
            recommendation = "WATCH"
            action_level = "Medium"
        else:
            recommendation = "HOLD"
            action_level = "Low"
            
        return {
            'sell_score': round(sell_score, 1),
            'recommendation': recommendation,
            'action_level': action_level,
            'confidence': round(confidence_avg, 2),
            'notes': all_notes[:5],  # 限制显示前5条
            'raw_score': round(final_score, 3),
            'modules_count': len(module_scores)
        }
    
    def generate_advanced_signals(self, market_data: Dict, technical_data: Dict) -> Dict[str, Union[float, str, List[str], int]]:
        """生成高级算法信号 - Phase 3 完整版（10个模块）"""
        try:
            logger.info("开始生成Phase 3高级算法信号（10模块）")
            
            # 计算特征包
            features = self.calculate_features_from_data(market_data, technical_data)
            
            # ATR中位数（缓存或估算）
            atr_median = 0.025  # 默认2.5%
            
            # 执行所有10个模块
            module_scores = []
            
            # 核心技术模块组 (A-E)
            module_scores.append(self.regime_aware_module(features, atr_median))              # A
            module_scores.append(self.breakout_exhaustion_module(features))                   # B  
            module_scores.append(self.confluence_module(features))                           # C
            module_scores.append(self.adaptive_atr_module(features, atr_median=atr_median)) # D
            module_scores.append(self.miner_cycle_module(features))                          # E
            
            # 高级策略模块组 (F-I)
            module_scores.append(self.pattern_target_module(features))                       # F
            module_scores.append(self.derivatives_pressure_module(features))                # G  
            module_scores.append(self.microstructure_executor_module(features))             # H
            module_scores.append(self.bandit_sizing_module(features))                       # I
            
            # J. Ensemble聚合 - 替代原aggregate_scores函数
            result = self.ensemble_aggregation_module(module_scores)
            
            logger.info(f"Phase 3高级算法信号生成完成：{result['modules_count']}个模块，评分{result['sell_score']}, 建议{result['recommendation']}")
            
            return result
            
        except Exception as e:
            logger.error(f"高级算法信号生成错误：{str(e)}")
            return {
                'sell_score': 50.0,
                'recommendation': 'WATCH',
                'action_level': 'Medium',
                'confidence': 0.0,
                'notes': ['算法模块暂时不可用'],
                'phase': "Phase 3 (Error)",
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }

# 全局实例
advanced_engine = AdvancedAlgorithmEngine()