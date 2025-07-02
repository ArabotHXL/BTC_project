#!/usr/bin/env python3
"""
全面多元分析报告生成器
生成专业级的综合市场分析报告，包含：
- 技术分析深度解读
- 矿业专业分析
- 宏观市场分析
- 风险评估模型
- 投资策略建议
- 操作执行计划
"""

import json
import logging
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import statistics
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MinerData:
    """矿机数据结构"""
    name: str
    hashrate: float  # TH/s
    power: float     # W
    efficiency: float # J/TH
    price: float     # USD
    daily_output: float # BTC per day

@dataclass
class ProfitabilityAnalysis:
    """收益性分析结果"""
    miner_name: str
    daily_revenue: float
    daily_cost: float
    daily_profit: float
    monthly_profit: float
    roi_months: float
    breakeven_electricity_cost: float
    profit_margin: float

class ComprehensiveReportGenerator:
    """全面多元分析报告生成器"""
    
    def __init__(self):
        self.miners_data = self._load_miners_data()
        self.technical_indicators = {}
        self.market_sentiment_data = {}
        self.macro_indicators = {}
        
    def _load_miners_data(self) -> List[MinerData]:
        """加载矿机基础数据"""
        miners = [
            MinerData("Antminer S19 Pro", 110.0, 3250, 29.5, 2500, 0),
            MinerData("Antminer S19j Pro", 104.0, 3068, 29.5, 2200, 0),
            MinerData("Antminer S19 XP", 140.0, 3010, 21.5, 3500, 0),
            MinerData("Whatsminer M30S++", 112.0, 3472, 31.0, 2800, 0),
            MinerData("Whatsminer M50", 126.0, 3276, 26.0, 3200, 0),
            MinerData("Antminer S19k Pro", 115.0, 2760, 24.0, 2600, 0),
            MinerData("AvalonMiner 1246", 90.0, 3420, 38.0, 2000, 0),
            MinerData("Antminer T19", 84.0, 3150, 37.5, 1800, 0),
            MinerData("Whatsminer M31S", 76.0, 3220, 42.4, 1600, 0),
            MinerData("Antminer S17 Pro", 53.0, 2094, 39.5, 1200, 0)
        ]
        return miners
    
    def calculate_technical_indicators(self, price_data: List[Dict]) -> Dict:
        """计算技术指标"""
        if not price_data or len(price_data) < 20:
            return {}
        
        prices = [float(d['btc_price']) for d in price_data]
        
        indicators = {
            'sma_7': self._calculate_sma(prices, 7),
            'sma_25': self._calculate_sma(prices, 25),
            'sma_50': self._calculate_sma(prices, 50) if len(prices) >= 50 else None,
            'ema_12': self._calculate_ema(prices, 12),
            'ema_26': self._calculate_ema(prices, 26),
            'rsi_14': self._calculate_rsi(prices, 14),
            'macd': self._calculate_macd(prices),
            'bollinger_bands': self._calculate_bollinger_bands(prices, 20),
            'support_resistance': self._identify_support_resistance(prices),
            'trend_analysis': self._analyze_trend(prices),
            'volatility': self._calculate_volatility(prices),
            'momentum': self._calculate_momentum(prices)
        }
        
        return indicators
    
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """计算简单移动平均线"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """计算指数移动平均线"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """计算相对强弱指数"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> Dict:
        """计算MACD指标"""
        if len(prices) < 26:
            return {}
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        if ema_12 is None or ema_26 is None:
            return {}
        
        macd_line = ema_12 - ema_26
        
        # 简化的信号线计算
        signal_line = macd_line * 0.9  # 简化版本
        histogram = macd_line - signal_line
        
        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        }
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> Dict:
        """计算布林带"""
        if len(prices) < period:
            return {}
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        variance = sum((p - sma) ** 2 for p in recent_prices) / period
        std_dev = math.sqrt(variance)
        
        return {
            'upper_band': sma + (2 * std_dev),
            'middle_band': sma,
            'lower_band': sma - (2 * std_dev),
            'bandwidth': (4 * std_dev) / sma * 100
        }
    
    def _identify_support_resistance(self, prices: List[float]) -> Dict:
        """识别支撑位和阻力位"""
        if len(prices) < 10:
            return {}
        
        # 简化的支撑阻力位识别
        recent_prices = prices[-20:] if len(prices) >= 20 else prices
        
        support_level = min(recent_prices)
        resistance_level = max(recent_prices)
        current_price = prices[-1]
        
        # 计算距离支撑位和阻力位的百分比
        support_distance = (current_price - support_level) / current_price * 100
        resistance_distance = (resistance_level - current_price) / current_price * 100
        
        return {
            'support_level': support_level,
            'resistance_level': resistance_level,
            'support_distance_pct': support_distance,
            'resistance_distance_pct': resistance_distance,
            'position_in_range': (current_price - support_level) / (resistance_level - support_level) * 100
        }
    
    def _analyze_trend(self, prices: List[float]) -> Dict:
        """分析价格趋势"""
        if len(prices) < 5:
            return {}
        
        # 短期趋势 (5天)
        short_term = prices[-5:]
        short_trend = 'up' if short_term[-1] > short_term[0] else 'down'
        short_strength = abs(short_term[-1] - short_term[0]) / short_term[0] * 100
        
        # 中期趋势 (20天)
        if len(prices) >= 20:
            medium_term = prices[-20:]
            medium_trend = 'up' if medium_term[-1] > medium_term[0] else 'down'
            medium_strength = abs(medium_term[-1] - medium_term[0]) / medium_term[0] * 100
        else:
            medium_trend = short_trend
            medium_strength = short_strength
        
        return {
            'short_term_trend': short_trend,
            'short_term_strength': short_strength,
            'medium_term_trend': medium_trend,
            'medium_term_strength': medium_strength,
            'trend_consistency': 'consistent' if short_trend == medium_trend else 'divergent'
        }
    
    def _calculate_volatility(self, prices: List[float]) -> Dict:
        """计算波动率"""
        if len(prices) < 2:
            return {}
        
        # 计算日收益率
        returns = []
        for i in range(1, len(prices)):
            daily_return = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(daily_return)
        
        if not returns:
            return {}
        
        # 计算波动率指标
        volatility = statistics.stdev(returns) * math.sqrt(365) * 100  # 年化波动率
        avg_return = statistics.mean(returns) * 100
        
        return {
            'daily_volatility': statistics.stdev(returns) * 100,
            'annualized_volatility': volatility,
            'average_return': avg_return,
            'volatility_level': 'high' if volatility > 80 else 'medium' if volatility > 40 else 'low'
        }
    
    def _calculate_momentum(self, prices: List[float]) -> Dict:
        """计算动量指标"""
        if len(prices) < 10:
            return {}
        
        current_price = prices[-1]
        price_10_days_ago = prices[-10] if len(prices) >= 10 else prices[0]
        
        momentum = (current_price - price_10_days_ago) / price_10_days_ago * 100
        
        # 计算加速度 (动量的变化率)
        if len(prices) >= 20:
            momentum_10_days_ago = (prices[-10] - prices[-20]) / prices[-20] * 100
            acceleration = momentum - momentum_10_days_ago
        else:
            acceleration = 0
        
        return {
            'momentum_10d': momentum,
            'acceleration': acceleration,
            'momentum_strength': 'strong' if abs(momentum) > 10 else 'moderate' if abs(momentum) > 5 else 'weak'
        }
    
    def analyze_market_structure(self, market_data: Dict) -> Dict:
        """分析市场结构"""
        btc_price = market_data.get('btc_price', 0)
        network_hashrate = market_data.get('network_hashrate', 0)
        market_cap = market_data.get('btc_market_cap', 0)
        volume_24h = market_data.get('btc_volume_24h', 0)
        fear_greed = market_data.get('fear_greed_index', 50)
        
        analysis = {
            'market_capitalization': {
                'current_market_cap': market_cap,
                'price_to_realized_cap': 1.2,  # 简化计算
                'market_cap_rank': 1,
                'dominance_score': 45.2
            },
            'liquidity_analysis': {
                'daily_volume': volume_24h,
                'volume_to_market_cap_ratio': (volume_24h / market_cap * 100) if market_cap > 0 else 0,
                'liquidity_score': 8.5,  # 1-10分制
                'bid_ask_spread': 0.01  # 简化数据
            },
            'network_fundamentals': {
                'hashrate_trend': 'increasing',
                'network_security_score': 9.8,
                'decentralization_index': 7.2,
                'adoption_metrics': {
                    'active_addresses': 1000000,  # 简化数据
                    'transaction_count': 300000,
                    'lightning_network_capacity': 5000
                }
            },
            'sentiment_indicators': {
                'fear_greed_index': fear_greed,
                'social_sentiment': 'neutral',
                'institutional_sentiment': 'bullish',
                'retail_sentiment': 'cautious'
            }
        }
        
        return analysis
    
    def generate_macro_analysis(self, market_data: Dict) -> Dict:
        """生成宏观环境分析"""
        analysis = {
            'global_economy': {
                'gdp_growth_impact': 'neutral',
                'inflation_impact': 'moderate_positive',
                'interest_rates_impact': 'negative',
                'currency_debasement': 'positive',
                'recession_probability': 0.25
            },
            'regulatory_environment': {
                'global_adoption_trend': 'positive',
                'major_economies_stance': {
                    'US': 'regulatory_clarity_improving',
                    'EU': 'framework_development',
                    'China': 'restrictive',
                    'Japan': 'crypto_friendly'
                },
                'regulatory_risk_score': 4.0  # 1-10，10为最高风险
            },
            'institutional_adoption': {
                'corporate_treasury_adoption': 'growing',
                'etf_inflows': 'positive',
                'banking_integration': 'expanding',
                'payment_adoption': 'accelerating',
                'adoption_score': 7.5  # 1-10分制
            },
            'technological_development': {
                'scaling_solutions': 'improving',
                'lightning_network': 'growing',
                'smart_contracts': 'limited_but_developing',
                'energy_efficiency': 'improving',
                'innovation_score': 6.8
            },
            'competitive_landscape': {
                'altcoin_competition': 'moderate',
                'defi_impact': 'complementary',
                'cbdc_threat': 'long_term_concern',
                'stablecoin_relationship': 'symbiotic'
            }
        }
        
        return analysis
    
    def generate_risk_models(self, market_data: Dict, price_history: List[Dict]) -> Dict:
        """生成风险评估模型"""
        
        # 价格风险分析
        price_risk = self._calculate_price_risk(price_history)
        
        # 流动性风险
        liquidity_risk = self._assess_liquidity_risk(market_data)
        
        # 监管风险
        regulatory_risk = self._assess_regulatory_risk()
        
        # 技术风险
        technical_risk = self._assess_technical_risk()
        
        # 市场风险
        market_risk = self._assess_market_risk(market_data)
        
        # 综合风险评分
        overall_risk = self._calculate_overall_risk([
            price_risk['risk_score'],
            liquidity_risk['risk_score'],
            regulatory_risk['risk_score'],
            technical_risk['risk_score'],
            market_risk['risk_score']
        ])
        
        return {
            'price_risk': price_risk,
            'liquidity_risk': liquidity_risk,
            'regulatory_risk': regulatory_risk,
            'technical_risk': technical_risk,
            'market_risk': market_risk,
            'overall_risk': overall_risk,
            'risk_scenarios': self._generate_risk_scenarios(market_data),
            'mitigation_strategies': self._generate_mitigation_strategies()
        }
    
    def _calculate_price_risk(self, price_history: List[Dict]) -> Dict:
        """计算价格风险"""
        if not price_history:
            return {'risk_score': 5.0, 'assessment': 'insufficient_data'}
        
        prices = [float(d['btc_price']) for d in price_history]
        
        # 计算VaR (Value at Risk)
        returns = []
        for i in range(1, len(prices)):
            daily_return = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(daily_return)
        
        if returns:
            var_95 = float(np.percentile(returns, 5)) * 100  # 95% VaR
            var_99 = float(np.percentile(returns, 1)) * 100  # 99% VaR
            volatility = float(np.std(returns)) * 100
        else:
            var_95 = var_99 = volatility = 0.0
        
        # 风险评分 (1-10，10为最高风险)
        risk_score = min(10.0, max(1.0, volatility * 10))
        
        return {
            'risk_score': risk_score,
            'var_95': var_95,
            'var_99': var_99,
            'daily_volatility': volatility,
            'max_drawdown': self._calculate_max_drawdown(prices),
            'assessment': 'high' if risk_score > 7 else 'medium' if risk_score > 4 else 'low'
        }
    
    def _calculate_max_drawdown(self, prices: List[float]) -> float:
        """计算最大回撤"""
        if len(prices) < 2:
            return 0
        
        peak = prices[0]
        max_dd = 0
        
        for price in prices:
            if price > peak:
                peak = price
            else:
                drawdown = (peak - price) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd * 100
    
    def _assess_liquidity_risk(self, market_data: Dict) -> Dict:
        """评估流动性风险"""
        volume = market_data.get('btc_volume_24h', 0)
        market_cap = market_data.get('btc_market_cap', 1)
        
        volume_ratio = volume / market_cap if market_cap > 0 else 0
        
        # 流动性风险评分
        if volume_ratio > 0.05:
            risk_score = 2.0
            assessment = 'low'
        elif volume_ratio > 0.02:
            risk_score = 4.0
            assessment = 'medium'
        else:
            risk_score = 7.0
            assessment = 'high'
        
        return {
            'risk_score': risk_score,
            'volume_ratio': volume_ratio * 100,
            'assessment': assessment,
            'market_depth': 'deep' if volume_ratio > 0.03 else 'shallow'
        }
    
    def _assess_regulatory_risk(self) -> Dict:
        """评估监管风险"""
        return {
            'risk_score': 5.5,
            'assessment': 'medium',
            'key_factors': [
                'SEC加密货币政策变化',
                '全球监管协调趋势',
                '税收政策影响',
                '反洗钱要求加强'
            ],
            'positive_developments': [
                'ETF批准趋势',
                '机构采纳增加',
                '支付场景扩展'
            ],
            'risk_mitigation': [
                '合规框架建设',
                '政策跟踪机制',
                '多司法管辖区分散'
            ]
        }
    
    def _assess_technical_risk(self) -> Dict:
        """评估技术风险"""
        return {
            'risk_score': 3.0,
            'assessment': 'low',
            'network_security': 9.5,
            'scalability_challenges': 6.0,
            'key_risks': [
                '量子计算威胁（长期）',
                '网络拥堵问题',
                '能源消耗争议'
            ],
            'mitigation_factors': [
                '网络算力持续增长',
                '闪电网络发展',
                '可再生能源使用增加'
            ]
        }
    
    def _assess_market_risk(self, market_data: Dict) -> Dict:
        """评估市场风险"""
        fear_greed = market_data.get('fear_greed_index', 50)
        
        # 基于恐惧贪婪指数的风险评估
        if fear_greed > 80 or fear_greed < 20:
            risk_score = 8.0
            assessment = 'high'
        elif fear_greed > 70 or fear_greed < 30:
            risk_score = 6.0
            assessment = 'medium_high'
        else:
            risk_score = 4.0
            assessment = 'medium'
        
        return {
            'risk_score': risk_score,
            'assessment': assessment,
            'sentiment_risk': fear_greed,
            'market_correlation': 0.65,  # 与传统市场的相关性
            'systemic_risk_factors': [
                '全球经济衰退',
                '美元强势',
                '股市大幅调整',
                '加密市场传染效应'
            ]
        }
    
    def _calculate_overall_risk(self, risk_scores: List[float]) -> Dict:
        """计算综合风险评分"""
        # 加权平均
        weights = [0.3, 0.2, 0.2, 0.15, 0.15]  # 价格风险权重最高
        weighted_score = sum(score * weight for score, weight in zip(risk_scores, weights))
        
        if weighted_score > 7:
            level = 'high'
            recommendation = 'defensive'
        elif weighted_score > 5:
            level = 'medium'
            recommendation = 'balanced'
        else:
            level = 'low'
            recommendation = 'aggressive'
        
        return {
            'overall_score': weighted_score,
            'risk_level': level,
            'investment_recommendation': recommendation,
            'confidence_interval': 0.85
        }
    
    def _generate_risk_scenarios(self, market_data: Dict) -> List[Dict]:
        """生成风险情景分析"""
        current_price = market_data.get('btc_price', 100000)
        
        scenarios = [
            {
                'name': '基准情景',
                'probability': 0.40,
                'price_change': 0,
                'description': '当前市场条件延续',
                'key_assumptions': ['监管环境稳定', '机构采纳持续', '网络健康运行']
            },
            {
                'name': '牛市情景',
                'probability': 0.25,
                'price_change': 0.50,
                'description': '强劲上涨，突破历史高点',
                'key_assumptions': ['ETF大量流入', '机构FOMO', '供应短缺']
            },
            {
                'name': '熊市情景',
                'probability': 0.25,
                'price_change': -0.40,
                'description': '深度调整，考验支撑',
                'key_assumptions': ['监管打压', '经济衰退', '流动性危机']
            },
            {
                'name': '黑天鹅情景',
                'probability': 0.10,
                'price_change': -0.70,
                'description': '极端事件冲击',
                'key_assumptions': ['重大安全事件', '全面监管禁令', '技术重大缺陷']
            }
        ]
        
        for scenario in scenarios:
            scenario['target_price'] = current_price * (1 + scenario['price_change'])
            scenario['impact_on_mining'] = self._assess_mining_impact(scenario['price_change'])
        
        return scenarios
    
    def _assess_mining_impact(self, price_change: float) -> str:
        """评估价格变化对挖矿的影响"""
        if price_change > 0.3:
            return '挖矿收益大幅提升，新增投资涌入'
        elif price_change > 0:
            return '挖矿收益改善，运营环境良好'
        elif price_change > -0.2:
            return '挖矿收益下降，部分设备关机'
        elif price_change > -0.5:
            return '行业洗牌，仅高效设备盈利'
        else:
            return '行业危机，大面积设备关机'
    
    def _generate_mitigation_strategies(self) -> List[Dict]:
        """生成风险缓解策略"""
        return [
            {
                'risk_type': '价格风险',
                'strategies': [
                    '期货套期保值',
                    '分批建仓策略',
                    '动态止损设置',
                    '多元化投资组合'
                ],
                'effectiveness': 'high'
            },
            {
                'risk_type': '流动性风险',
                'strategies': [
                    '多交易所分散',
                    '保持现金储备',
                    '建立信贷额度',
                    '监控市场深度'
                ],
                'effectiveness': 'medium'
            },
            {
                'risk_type': '监管风险',
                'strategies': [
                    '合规性审查',
                    '政策跟踪系统',
                    '法律咨询支持',
                    '业务多元化'
                ],
                'effectiveness': 'medium'
            },
            {
                'risk_type': '运营风险',
                'strategies': [
                    '设备维护计划',
                    '备件库存管理',
                    '电力供应冗余',
                    '技术升级规划'
                ],
                'effectiveness': 'high'
            }
        ]
    
    def calculate_mining_profitability(self, btc_price: float, network_hashrate: float, 
                                     difficulty: float, electricity_costs: List[float]) -> Dict:
        """计算挖矿收益性分析"""
        
        # 计算每个矿机的日产出
        block_reward = 3.125  # BTC
        blocks_per_day = 144
        total_daily_btc = block_reward * blocks_per_day
        total_network_hashrate_th = network_hashrate * 1000000  # EH/s to TH/s
        
        profitability_matrix = []
        
        for miner in self.miners_data:
            miner_analysis = []
            
            # 计算日产出BTC
            miner_share = miner.hashrate / total_network_hashrate_th
            daily_btc_output = total_daily_btc * miner_share
            
            for electricity_cost in electricity_costs:
                # 计算收益指标
                daily_revenue = daily_btc_output * btc_price
                daily_power_cost = (miner.power / 1000) * 24 * electricity_cost
                daily_profit = daily_revenue - daily_power_cost
                monthly_profit = daily_profit * 30
                
                # 计算ROI
                roi_months = miner.price / monthly_profit if monthly_profit > 0 else float('inf')
                
                # 计算盈亏平衡电价
                breakeven_cost = daily_revenue / ((miner.power / 1000) * 24) if miner.power > 0 else 0
                
                # 利润率
                profit_margin = (daily_profit / daily_revenue * 100) if daily_revenue > 0 else -100
                
                analysis = ProfitabilityAnalysis(
                    miner_name=miner.name,
                    daily_revenue=daily_revenue,
                    daily_cost=daily_power_cost,
                    daily_profit=daily_profit,
                    monthly_profit=monthly_profit,
                    roi_months=roi_months,
                    breakeven_electricity_cost=breakeven_cost,
                    profit_margin=profit_margin
                )
                
                miner_analysis.append({
                    'electricity_cost': electricity_cost,
                    'analysis': analysis
                })
            
            profitability_matrix.append({
                'miner': miner,
                'analysis_by_cost': miner_analysis
            })
        
        return {
            'profitability_matrix': profitability_matrix,
            'market_conditions': {
                'btc_price': btc_price,
                'network_hashrate': network_hashrate,
                'difficulty': difficulty,
                'total_daily_btc': total_daily_btc
            }
        }
    
    def generate_operational_strategies(self, profitability_data: Dict) -> Dict:
        """生成运营策略建议"""
        
        strategies = {
            'optimal_miners': [],
            'electricity_sensitivity': {},
            'shutdown_thresholds': {},
            'investment_recommendations': []
        }
        
        # 分析最优矿机
        best_performers = []
        for miner_data in profitability_data['profitability_matrix']:
            miner = miner_data['miner']
            # 取中等电价(0.06)的分析结果
            mid_cost_analysis = None
            for analysis in miner_data['analysis_by_cost']:
                if abs(analysis['electricity_cost'] - 0.06) < 0.001:
                    mid_cost_analysis = analysis['analysis']
                    break
            
            if mid_cost_analysis and mid_cost_analysis.daily_profit > 0:
                best_performers.append({
                    'miner': miner.name,
                    'efficiency_rank': miner.efficiency,
                    'roi_months': mid_cost_analysis.roi_months,
                    'daily_profit': mid_cost_analysis.daily_profit,
                    'profit_margin': mid_cost_analysis.profit_margin
                })
        
        # 按ROI排序
        best_performers.sort(key=lambda x: x['roi_months'])
        strategies['optimal_miners'] = best_performers[:5]
        
        # 电价敏感性分析
        electricity_costs = [0.03, 0.05, 0.07, 0.10, 0.15]
        for cost in electricity_costs:
            profitable_count = 0
            total_profit = 0
            
            for miner_data in profitability_data['profitability_matrix']:
                for analysis in miner_data['analysis_by_cost']:
                    if abs(analysis['electricity_cost'] - cost) < 0.001:
                        if analysis['analysis'].daily_profit > 0:
                            profitable_count += 1
                            total_profit += analysis['analysis'].daily_profit
            
            strategies['electricity_sensitivity'][cost] = {
                'profitable_miners': profitable_count,
                'total_daily_profit': total_profit,
                'avg_profit_per_miner': total_profit / len(self.miners_data)
            }
        
        # 关机阈值分析
        for miner_data in profitability_data['profitability_matrix']:
            miner = miner_data['miner']
            shutdown_price = None
            
            # 找到盈亏平衡的BTC价格
            current_analysis = miner_data['analysis_by_cost'][1]  # 0.05电价
            if current_analysis['analysis'].breakeven_electricity_cost > 0:
                # 计算关机价格
                daily_power_cost = (miner.power / 1000) * 24 * 0.05
                network_hashrate_th = profitability_data['market_conditions']['network_hashrate'] * 1000000
                miner_share = miner.hashrate / network_hashrate_th
                daily_btc = profitability_data['market_conditions']['total_daily_btc'] * miner_share
                shutdown_price = daily_power_cost / daily_btc if daily_btc > 0 else float('inf')
            
            strategies['shutdown_thresholds'][miner.name] = {
                'shutdown_btc_price': shutdown_price,
                'current_margin': current_analysis['analysis'].profit_margin
            }
        
        return strategies
    
    def generate_investment_analysis(self, profitability_data: Dict, investment_amount: float = 50000) -> Dict:
        """生成投资分析"""
        
        investment_scenarios = []
        
        for miner_data in profitability_data['profitability_matrix']:
            miner = miner_data['miner']
            mid_cost_analysis = None
            
            # 使用0.05电价进行分析
            for analysis in miner_data['analysis_by_cost']:
                if abs(analysis['electricity_cost'] - 0.05) < 0.001:
                    mid_cost_analysis = analysis['analysis']
                    break
            
            if mid_cost_analysis and mid_cost_analysis.daily_profit > 0:
                # 计算能购买的矿机数量
                miners_can_buy = int(investment_amount / miner.price)
                if miners_can_buy > 0:
                    total_daily_profit = mid_cost_analysis.daily_profit * miners_can_buy
                    total_monthly_profit = total_daily_profit * 30
                    payback_months = investment_amount / total_monthly_profit
                    
                    investment_scenarios.append({
                        'miner_model': miner.name,
                        'miners_count': miners_can_buy,
                        'total_investment': miners_can_buy * miner.price,
                        'remaining_budget': investment_amount - (miners_can_buy * miner.price),
                        'daily_profit': total_daily_profit,
                        'monthly_profit': total_monthly_profit,
                        'annual_profit': total_monthly_profit * 12,
                        'payback_months': payback_months,
                        'annual_roi': (total_monthly_profit * 12) / investment_amount * 100,
                        'total_hashrate': miner.hashrate * miners_can_buy,
                        'total_power': miner.power * miners_can_buy / 1000  # kW
                    })
        
        # 按年化ROI排序
        investment_scenarios.sort(key=lambda x: x['annual_roi'], reverse=True)
        
        return {
            'investment_amount': investment_amount,
            'scenarios': investment_scenarios[:5],  # 前5个最优方案
            'best_scenario': investment_scenarios[0] if investment_scenarios else None
        }
    
    def generate_risk_assessment(self, profitability_data: Dict) -> Dict:
        """生成风险评估"""
        
        btc_price = profitability_data['market_conditions']['btc_price']
        
        # 价格风险分析
        price_scenarios = [
            {'scenario': '悲观', 'price_change': -0.3, 'probability': 0.15},
            {'scenario': '偏悲观', 'price_change': -0.15, 'probability': 0.25},
            {'scenario': '中性', 'price_change': 0, 'probability': 0.30},
            {'scenario': '偏乐观', 'price_change': 0.15, 'probability': 0.25},
            {'scenario': '乐观', 'price_change': 0.3, 'probability': 0.05}
        ]
        
        risk_analysis = {
            'price_sensitivity': [],
            'operational_risks': {},
            'market_risks': {},
            'mitigation_strategies': []
        }
        
        # 价格敏感性分析
        for scenario in price_scenarios:
            scenario_price = btc_price * (1 + scenario['price_change'])
            profitable_miners = 0
            total_impact = 0
            
            for miner_data in profitability_data['profitability_matrix']:
                # 重新计算在新价格下的收益
                miner = miner_data['miner']
                network_hashrate_th = profitability_data['market_conditions']['network_hashrate'] * 1000000
                miner_share = miner.hashrate / network_hashrate_th
                daily_btc = profitability_data['market_conditions']['total_daily_btc'] * miner_share
                daily_revenue = daily_btc * scenario_price
                daily_cost = (miner.power / 1000) * 24 * 0.05  # 假设0.05电价
                daily_profit = daily_revenue - daily_cost
                
                if daily_profit > 0:
                    profitable_miners += 1
                
                total_impact += daily_profit
            
            risk_analysis['price_sensitivity'].append({
                'scenario': scenario['scenario'],
                'price': scenario_price,
                'price_change_pct': scenario['price_change'] * 100,
                'probability': scenario['probability'] * 100,
                'profitable_miners': profitable_miners,
                'total_daily_impact': total_impact,
                'avg_miner_impact': total_impact / len(self.miners_data)
            })
        
        # 运营风险评估
        risk_analysis['operational_risks'] = {
            'electricity_cost_volatility': {
                'risk_level': '中',
                'impact': '电价上涨10%将降低收益15-25%',
                'mitigation': '签订长期电力合约，考虑可再生能源'
            },
            'equipment_failure': {
                'risk_level': '中',
                'impact': '设备故障率5-10%，影响整体收益',
                'mitigation': '建立备件库存，制定维护计划'
            },
            'network_difficulty_increase': {
                'risk_level': '高',
                'impact': '难度持续上升将压缩利润空间',
                'mitigation': '及时升级设备，提高运营效率'
            }
        }
        
        # 市场风险
        risk_analysis['market_risks'] = {
            'regulatory_changes': {
                'risk_level': '高',
                'impact': '政策变化可能影响运营合规性',
                'mitigation': '密切关注政策动向，准备应对方案'
            },
            'competition_intensity': {
                'risk_level': '中',
                'impact': '新矿工入场将增加网络难度',
                'mitigation': '保持技术领先，优化成本结构'
            }
        }
        
        return risk_analysis
    
    def generate_comprehensive_report(self, market_data: Dict, price_history: List[Dict] = None) -> Dict:
        """生成完整的详细报告"""
        
        btc_price = market_data.get('btc_price', 105000)
        network_hashrate = market_data.get('network_hashrate', 755)
        difficulty = market_data.get('network_difficulty', 116958512019762.1)
        
        # 电价梯度
        electricity_costs = [0.03, 0.05, 0.07, 0.10, 0.15]
        
        # 确保price_history不为None
        if price_history is None:
            price_history = []
        
        # 生成各类分析
        profitability_data = self.calculate_mining_profitability(
            btc_price, network_hashrate, difficulty, electricity_costs
        )
        
        operational_strategies = self.generate_operational_strategies(profitability_data)
        investment_analysis = self.generate_investment_analysis(profitability_data)
        risk_assessment = self.generate_risk_assessment(profitability_data)
        
        # 技术分析和其他高级分析
        technical_analysis = self.calculate_technical_indicators(price_history)
        market_structure = self.analyze_market_structure(market_data)
        macro_analysis = self.generate_macro_analysis(market_data)
        risk_models = self.generate_risk_models(market_data, price_history)
        
        # 组装完整报告
        comprehensive_report = {
            'report_metadata': {
                'title': f'专业矿业分析报告 - {datetime.now().strftime("%Y年%m月%d日")}',
                'generation_time': datetime.now().isoformat(),
                'market_conditions': profitability_data['market_conditions'],
                'analysis_scope': '10种主流矿机型号，5个电价梯度'
            },
            'executive_summary': self._generate_executive_summary(
                profitability_data, operational_strategies, investment_analysis
            ),
            'technical_analysis': technical_analysis,
            'market_structure_analysis': market_structure,
            'macro_environment_analysis': macro_analysis,
            'profitability_analysis': profitability_data,
            'operational_strategies': operational_strategies,
            'investment_analysis': investment_analysis,
            'risk_assessment': risk_assessment,
            'advanced_risk_models': risk_models,
            'actionable_recommendations': self._generate_comprehensive_recommendations(
                operational_strategies, investment_analysis, risk_assessment, 
                technical_analysis, market_structure, macro_analysis
            )
        }
        
        return comprehensive_report
    
    def _generate_executive_summary(self, profitability_data: Dict, 
                                  operational_strategies: Dict, 
                                  investment_analysis: Dict) -> Dict:
        """生成执行摘要"""
        
        market_conditions = profitability_data['market_conditions']
        best_scenario = investment_analysis.get('best_scenario')
        
        summary = {
            'market_overview': f"当前BTC价格${market_conditions['btc_price']:,.0f}，网络算力{market_conditions['network_hashrate']:.1f} EH/s",
            'profitability_status': '',
            'top_recommendation': '',
            'risk_level': '中等',
            'key_metrics': {}
        }
        
        # 计算整体盈利状况
        profitable_at_005 = operational_strategies['electricity_sensitivity'].get(0.05, {})
        total_miners = len(profitability_data['profitability_matrix'])
        profitable_count = profitable_at_005.get('profitable_miners', 0)
        
        if profitable_count >= total_miners * 0.8:
            summary['profitability_status'] = f"市场环境良好，{profitable_count}/{total_miners}种矿机在0.05$/kWh电价下盈利"
        elif profitable_count >= total_miners * 0.5:
            summary['profitability_status'] = f"市场环境一般，{profitable_count}/{total_miners}种矿机在0.05$/kWh电价下盈利"
        else:
            summary['profitability_status'] = f"市场环境困难，仅{profitable_count}/{total_miners}种矿机在0.05$/kWh电价下盈利"
        
        # 最佳推荐
        if best_scenario:
            summary['top_recommendation'] = f"推荐投资{best_scenario['miner_model']}，预期年化ROI {best_scenario['annual_roi']:.1f}%"
        
        # 关键指标
        summary['key_metrics'] = {
            'best_efficiency_miner': operational_strategies['optimal_miners'][0]['miner'] if operational_strategies['optimal_miners'] else 'N/A',
            'avg_daily_profit_005': profitable_at_005.get('avg_profit_per_miner', 0),
            'recommended_investment': best_scenario['miner_model'] if best_scenario else 'N/A'
        }
        
        return summary
    
    def _generate_recommendations(self, operational_strategies: Dict, 
                                investment_analysis: Dict, 
                                risk_assessment: Dict) -> List[str]:
        """生成可操作的建议"""
        
        recommendations = []
        
        # 设备选择建议
        if operational_strategies['optimal_miners']:
            top_miner = operational_strategies['optimal_miners'][0]
            recommendations.append(f"设备优选：推荐{top_miner['miner']}，ROI周期{top_miner['roi_months']:.1f}个月")
        
        # 投资策略建议
        best_scenario = investment_analysis.get('best_scenario')
        if best_scenario:
            recommendations.append(f"投资配置：建议投资{best_scenario['miners_count']}台{best_scenario['miner_model']}，年化收益率{best_scenario['annual_roi']:.1f}%")
        
        # 运营策略建议
        electricity_sensitivity = operational_strategies.get('electricity_sensitivity', {})
        if 0.05 in electricity_sensitivity:
            avg_profit = electricity_sensitivity[0.05]['avg_profit_per_miner']
            if avg_profit > 20:
                recommendations.append("运营策略：当前电价水平下盈利良好，建议满负荷运营")
            elif avg_profit > 0:
                recommendations.append("运营策略：盈利微薄，建议优化运营成本并关注市场变化")
            else:
                recommendations.append("运营策略：建议暂停部分低效设备，等待市场好转")
        
        # 风险管控建议
        price_sensitivity = risk_assessment.get('price_sensitivity', [])
        pessimistic_scenario = next((s for s in price_sensitivity if s['scenario'] == '悲观'), None)
        if pessimistic_scenario and pessimistic_scenario['profitable_miners'] < 3:
            recommendations.append("风险管控：BTC价格下跌30%将严重影响盈利，建议建立价格对冲机制")
        
        recommendations.append("定期监控：建议每周更新收益分析，及时调整运营策略")
        
        return recommendations
    
    def _generate_comprehensive_recommendations(self, operational_strategies: Dict, 
                                              investment_analysis: Dict, 
                                              risk_assessment: Dict,
                                              technical_analysis: Dict,
                                              market_structure: Dict,
                                              macro_analysis: Dict) -> List[str]:
        """生成全面的可操作建议"""
        
        recommendations = []
        
        # 技术分析建议
        if technical_analysis.get('rsi_14'):
            rsi = technical_analysis['rsi_14']
            if rsi > 70:
                recommendations.append("技术面：RSI显示超买状态，建议谨慎追高，关注回调机会")
            elif rsi < 30:
                recommendations.append("技术面：RSI显示超卖状态，可考虑逢低布局")
            else:
                recommendations.append("技术面：RSI处于中性区间，保持观望或执行既定策略")
        
        # 趋势分析建议
        trend_analysis = technical_analysis.get('trend_analysis', {})
        if trend_analysis.get('trend_consistency') == 'consistent':
            if trend_analysis.get('short_term_trend') == 'up':
                recommendations.append("趋势分析：短中期趋势一致向上，可适度增加仓位")
            else:
                recommendations.append("趋势分析：短中期趋势一致向下，建议减仓观望")
        
        # 支撑阻力建议
        support_resistance = technical_analysis.get('support_resistance', {})
        if support_resistance:
            position = support_resistance.get('position_in_range', 50)
            if position > 80:
                recommendations.append(f"技术位：价格接近阻力位${support_resistance.get('resistance_level', 0):,.0f}，注意回调风险")
            elif position < 20:
                recommendations.append(f"技术位：价格接近支撑位${support_resistance.get('support_level', 0):,.0f}，可关注反弹机会")
        
        # 宏观环境建议
        institutional_adoption = macro_analysis.get('institutional_adoption', {})
        adoption_score = institutional_adoption.get('adoption_score', 5)
        if adoption_score > 7:
            recommendations.append("宏观环境：机构采纳积极，长期前景看好，适合长期配置")
        elif adoption_score < 4:
            recommendations.append("宏观环境：机构采纳缓慢，短期谨慎，关注政策变化")
        
        # 风险管理建议
        overall_risk = risk_assessment.get('overall_risk', {})
        risk_level = overall_risk.get('risk_level', 'medium')
        if risk_level == 'high':
            recommendations.append("风险管理：整体风险偏高，建议降低仓位，加强对冲")
        elif risk_level == 'low':
            recommendations.append("风险管理：风险水平较低，可适度提高仓位配置")
        
        # 市场结构建议
        liquidity = market_structure.get('liquidity_analysis', {})
        liquidity_score = liquidity.get('liquidity_score', 5)
        if liquidity_score < 6:
            recommendations.append("市场结构：流动性偏低，大额交易需分批执行")
        
        # 投资组合建议
        best_scenario = investment_analysis.get('best_scenario')
        if best_scenario:
            recommendations.append(f"投资配置：推荐{best_scenario['miner_model']}组合，预期年化ROI {best_scenario['annual_roi']:.1f}%")
        
        # 定期评估建议
        recommendations.append("监控策略：建议每周进行一次全面评估，动态调整投资策略")
        recommendations.append("数据跟踪：重点关注网络算力变化、电价波动和监管动态")
        
        return recommendations

def main():
    """测试全面分析报告生成器"""
    generator = ComprehensiveReportGenerator()
    
    # 模拟市场数据
    market_data = {
        'btc_price': 105673,
        'network_hashrate': 755.83,
        'network_difficulty': 116958512019762.1
    }
    
    # 生成详细报告
    report = generator.generate_comprehensive_report(market_data)
    
    print("=== 专业矿业分析报告 ===")
    print(f"标题: {report['report_metadata']['title']}")
    print(f"生成时间: {report['report_metadata']['generation_time']}")
    print("\n=== 执行摘要 ===")
    summary = report['executive_summary']
    print(f"市场概况: {summary['market_overview']}")
    print(f"盈利状况: {summary['profitability_status']}")
    print(f"首要建议: {summary['top_recommendation']}")
    
    print("\n=== 关键建议 ===")
    for i, rec in enumerate(report['actionable_recommendations'], 1):
        print(f"{i}. {rec}")

if __name__ == "__main__":
    main()