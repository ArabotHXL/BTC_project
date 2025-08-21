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
            notes.append("上升趋势+低波动：建议提高分层门槛")
        elif not trend_up and high_volatility:
            score -= 0.3  # 下降趋势+高波动：降低门槛（加速卖出）
            notes.append("震荡/下降+高波动：建议降低门槛")
        
        if high_price_zone and high_volatility:
            score += 0.15  # 高位+高波动：谨慎信号
            notes.append("价格高位+波动增加：谨慎观察")
            
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
            notes.append(f"高波动环境：分层倍数调整至{effective_multiple:.1f}x")
        elif effective_multiple < base_multiple * 0.8:
            score += 0.1  # 低波动时缩小层距，增加卖出机会
            notes.append(f"低波动环境：分层倍数调整至{effective_multiple:.1f}x")
            
        if momentum_confirmed:
            notes.append("动能确认：RSI≥55")
        else:
            score -= 0.05  # 缺乏动能确认
            notes.append("动能不足：RSI<55")
            
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
                    notes.append(f"接近阻力位：${level:.0f}")
                    break
            
            if near_resistance:
                # 检查拒绝形态（简化版）
                if features.close < features.high * 0.995:  # 收盘价低于最高价0.5%
                    score += 0.25
                    notes.append("检测到拒绝形态：上影线")
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
                notes.append(f"共振区域：强度{total_strength:.1f}")
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
                    notes.append("成交量衰竭：突破缺乏量能支撑")
                    confidence = 0.8
            
            # 2. RSI背离检查 (简化版)
            if features.rsi14 > 75:  # 极度超买
                score += 0.25
                notes.append("RSI极度超买：>75，突破乏力风险高")
                confidence = 0.85
            elif features.rsi14 > 65:  # 超买区域
                score += 0.1
                notes.append("RSI超买区域，关注背离")
            
            # 3. 价格行为分析
            # 检查是否有长上影线（衰竭征象）
            if features.close < features.high * 0.98:  # 收盘价低于最高价2%
                score += 0.15
                notes.append("长上影线：卖压显现")
            
            # 4. ATR扩张检查
            if features.atr_pct > 0.08:  # ATR超过8%（高波动）
                score += 0.1
                notes.append("波动率扩张：突破可能不持续")
        
        else:
            # 不在突破位置，降低衰竭模块权重
            score = 0.0
            notes.append("未处于突破位置，模块不活跃")
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
                notes.append(f"Puell Multiple极高：{features.puell:.2f} (>4.0)")
                confidence = 0.9
            elif features.puell > 2.5:
                # 高Puell Multiple，卖出信号
                score += 0.25
                notes.append(f"Puell Multiple偏高：{features.puell:.2f} (>2.5)")
                confidence = 0.8
            elif features.puell > 1.5:
                # 中性偏高区域
                score += 0.1
                notes.append(f"Puell Multiple中性：{features.puell:.2f}")
            else:
                # 低Puell Multiple，矿工卖压较小
                score -= 0.1
                notes.append(f"Puell Multiple偏低：{features.puell:.2f} (矿工卖压小)")
        
        # 使用Hash Price Percentile评估矿工盈利能力
        if features.hashprice_pctile is not None:
            if features.hashprice_pctile > 0.9:
                # 矿工处于极高盈利状态，卖出压力大
                score += 0.2
                notes.append(f"Hash Price高位：{features.hashprice_pctile*100:.0f}%分位")
                confidence = max(confidence, 0.8)
            elif features.hashprice_pctile > 0.7:
                # 矿工高盈利状态
                score += 0.1
                notes.append(f"Hash Price偏高：{features.hashprice_pctile*100:.0f}%分位")
            elif features.hashprice_pctile < 0.3:
                # 矿工盈利较低，卖压减小
                score -= 0.1
                notes.append(f"Hash Price偏低：{features.hashprice_pctile*100:.0f}%分位 (矿工惜售)")
        
        # 价格位置与挖矿成本的关系
        if features.pct_52w > 0.8:
            # 价格处于52周高位，结合矿工指标
            if features.puell and features.puell > 2.0:
                score += 0.15
                notes.append("价格高位+矿工高收益：卖出时机成熟")
                confidence = 0.85
        
        # 市场周期判断（基于移动平均线）
        if features.close > features.ma50 * 1.2:  # 价格显著高于50日MA
            score += 0.1
            notes.append("价格过热：高于50日MA 20%+")
        
        return ModuleScore("miner_cycle", score, confidence, notes)
    
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
        
        # ATR百分比（估算）
        volatility = float(technical_data.get('volatility', 0.05))
        atr_pct = volatility  # 使用波动率作为ATR百分比的近似
        
        # 52周百分位（估算）
        if historical_prices and len(historical_prices) >= 365:
            year_high = max(historical_prices[-365:])
            year_low = min(historical_prices[-365:])
            pct_52w = (close - year_low) / (year_high - year_low) if year_high > year_low else 0.5
        else:
            pct_52w = 0.75  # 假设当前在高位
        
        # 唐奇安通道（20日高点）
        donchian_20_high = close * 1.05  # 简化估算
        
        return FeaturePack(
            close=close,
            high=close * 1.01,  # 估算
            low=close * 0.99,   # 估算
            ma50=ma50,
            ma200=ma200,
            atr_pct=atr_pct,
            pct_52w=pct_52w,
            rsi14=rsi14,
            vol_20d=1000000,  # 估算成交量
            vol_today=1200000,
            donchian_20_high=donchian_20_high,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            hashprice_pctile=0.8,  # 估算矿工数据
            puell=1.2
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
        """生成高级算法信号"""
        try:
            logger.info("开始生成高级算法信号")
            
            # 计算特征包
            features = self.calculate_features_from_data(market_data, technical_data)
            
            # ATR中位数（缓存或估算）
            atr_median = 0.025  # 默认2.5%
            
            # 执行各个模块
            module_scores = []
            
            # A. Regime-Aware模块
            regime_score = self.regime_aware_module(features, atr_median)
            module_scores.append(regime_score)
            
            # D. Adaptive-ATR模块  
            atr_score = self.adaptive_atr_module(features, atr_median=atr_median)
            module_scores.append(atr_score)
            
            # C. Confluence模块
            confluence_score = self.confluence_module(features)
            module_scores.append(confluence_score)
            
            # Phase 2 新增模块
            # D. 突破衰竭检测模块
            breakout_score = self.breakout_exhaustion_module(features)
            module_scores.append(breakout_score)
            
            # E. 挖矿周期整合模块
            miner_cycle_score = self.miner_cycle_module(features)
            module_scores.append(miner_cycle_score)
            
            # 聚合评分 - Phase 2权重配置
            result = self.aggregate_scores(module_scores)
            
            logger.info(f"高级算法信号生成完成：评分{result['sell_score']}, 建议{result['recommendation']}")
            
            return result
            
        except Exception as e:
            logger.error(f"高级算法信号生成错误：{str(e)}")
            return {
                'sell_score': 50.0,
                'recommendation': 'WATCH',
                'action_level': 'Medium',
                'confidence': 0.0,
                'notes': ['算法模块暂时不可用'],
                'error': str(e)
            }

# 全局实例
advanced_engine = AdvancedAlgorithmEngine()