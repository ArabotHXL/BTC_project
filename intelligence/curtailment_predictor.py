"""
AI-Powered Curtailment Prediction Engine
Predicts optimal power curtailment schedule for next 24 hours based on:
- BTC price forecast (ARIMA)
- Network difficulty forecast (ARIMA)
- Electricity pricing
- Mining profitability optimization
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy import func

from app import db
from models import (
    HostingSite, HostingMiner, PowerPriceConfig, PriceMode,
    NetworkSnapshot, CurtailmentStrategy
)
from intelligence.forecast import forecast_btc_price, forecast_difficulty

logger = logging.getLogger(__name__)


class CurtailmentPredictor:
    """AI预测引擎 - 预测未来24小时最佳限电策略"""
    
    def __init__(self, site_id: int):
        self.site_id = site_id
        self.site = HostingSite.query.get(site_id)
        if not self.site:
            raise ValueError(f"Site {site_id} not found")
        
        # 获取活跃的电价配置
        self.price_config = PowerPriceConfig.query.filter_by(
            site_id=site_id,
            is_active=True
        ).first()
        
        if not self.price_config:
            raise ValueError(f"No active power price config found for site {site_id}")
        
        logger.info(f"Initialized CurtailmentPredictor for site {site_id} ({self.site.name})")
    
    def predict_24h_schedule(self, target_reduction_kw: Optional[float] = None) -> Dict:
        """
        预测未来24小时最佳限电时间表
        
        Args:
            target_reduction_kw: 目标功率削减量(kW)，如果为None则自动优化
            
        Returns:
            Dict containing:
                - hourly_schedule: 每小时的限电建议 [{hour, should_curtail, reduction_kw, net_benefit, btc_price, difficulty, power_cost}]
                - summary: 汇总信息 {total_hours_curtailed, total_power_saved, total_cost_saved, total_revenue_lost, net_benefit}
                - recommendation: 推荐策略 {optimal_hours, reason}
        """
        try:
            logger.info(f"开始预测未来24小时限电策略，目标削减: {target_reduction_kw} kW")
            
            # 1. 获取BTC价格和难度预测（hourly for 24 hours）
            btc_forecast = self._get_hourly_btc_forecast()
            difficulty_forecast = self._get_hourly_difficulty_forecast()
            
            # 2. 获取未来24小时电价
            hourly_prices = self._get_hourly_power_prices()
            
            # 3. 获取矿场当前算力和功耗
            site_stats = self._get_site_mining_stats()
            
            # 4. 计算每小时的盈亏分析
            hourly_analysis = []
            current_time = datetime.utcnow()
            
            for hour in range(24):
                hour_time = current_time + timedelta(hours=hour)
                hour_of_day = hour_time.hour
                
                # BTC价格和难度预测
                btc_price = btc_forecast[hour]
                difficulty = difficulty_forecast[hour]
                
                # 电价
                power_cost_per_kwh = hourly_prices[hour_of_day]
                
                # 计算挖矿收益 (BTC/小时)
                btc_per_hour = self._calculate_btc_revenue(
                    hashrate_th=site_stats['total_hashrate_th'],
                    difficulty=difficulty
                )
                
                # 收益价值 (USD/小时)
                revenue_usd = btc_per_hour * btc_price
                
                # 电力成本 (USD/小时)
                power_kw = site_stats['total_power_kw']
                power_cost_usd = power_kw * power_cost_per_kwh
                
                # 净利润 (USD/小时)
                net_profit = revenue_usd - power_cost_usd
                
                # 如果限电的收益分析
                if target_reduction_kw:
                    reduction_ratio = min(target_reduction_kw / power_kw, 1.0)
                else:
                    reduction_ratio = 1.0  # 完全关闭
                
                # 限电后的损失和节省
                revenue_lost = revenue_usd * reduction_ratio
                cost_saved = power_cost_usd * reduction_ratio
                net_benefit = cost_saved - revenue_lost
                
                hourly_analysis.append({
                    'hour': hour,
                    'hour_of_day': hour_of_day,
                    'timestamp': hour_time.isoformat(),
                    'btc_price': round(btc_price, 2),
                    'difficulty': round(difficulty, 0),
                    'power_cost_per_kwh': round(power_cost_per_kwh, 6),
                    'revenue_usd': round(revenue_usd, 2),
                    'power_cost_usd': round(power_cost_usd, 2),
                    'net_profit': round(net_profit, 2),
                    'reduction_kw': round(target_reduction_kw or power_kw, 2),
                    'revenue_lost': round(revenue_lost, 2),
                    'cost_saved': round(cost_saved, 2),
                    'net_benefit': round(net_benefit, 2),
                    'should_curtail': net_benefit > 0,  # 如果净收益为正，建议限电
                    'curtail_confidence': self._calculate_confidence(net_benefit, revenue_usd)
                })
            
            # 5. 生成推荐策略
            df = pd.DataFrame(hourly_analysis)
            
            # 找出应该限电的时段（净收益为正）
            curtail_hours = pd.DataFrame(df[df['should_curtail'] == True])
            
            # 汇总统计
            summary = {
                'total_hours_curtailed': len(curtail_hours),
                'total_power_saved_kwh': round(float(curtail_hours['reduction_kw'].sum()), 2),
                'total_cost_saved': round(float(curtail_hours['cost_saved'].sum()), 2),
                'total_revenue_lost': round(float(curtail_hours['revenue_lost'].sum()), 2),
                'net_benefit': round(float(curtail_hours['net_benefit'].sum()), 2),
                'avg_btc_price': round(df['btc_price'].mean(), 2),
                'avg_power_cost': round(df['power_cost_per_kwh'].mean(), 6)
            }
            
            # 推荐策略
            recommendation = self._generate_recommendation(curtail_hours, summary)
            
            logger.info(f"预测完成: {summary['total_hours_curtailed']} 小时建议限电, 净收益 ${summary['net_benefit']}")
            
            return {
                'success': True,
                'hourly_schedule': hourly_analysis,
                'summary': summary,
                'recommendation': recommendation,
                'site_stats': site_stats,
                'prediction_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"预测失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_hourly_btc_forecast(self) -> List[float]:
        """获取未来24小时BTC价格预测（hourly）"""
        try:
            # 调用ARIMA预测，获取未来1天的预测
            forecast_result = forecast_btc_price(days=1)
            
            if not forecast_result or 'predictions' not in forecast_result:
                raise ValueError("BTC price forecast failed")
            
            # 获取当前BTC价格作为基准
            latest_snapshot = NetworkSnapshot.query.filter_by(
                is_valid=True
            ).order_by(NetworkSnapshot.recorded_at.desc()).first()
            
            current_price = float(latest_snapshot.btc_price) if latest_snapshot else 50000.0
            
            # ARIMA返回的是每日预测，需要转换为每小时
            # 简化策略：使用当前价格和预测价格进行线性插值
            daily_prediction = forecast_result['predictions'][0]['price']
            
            # 生成24小时的价格序列（从当前价格到预测价格的平滑过渡）
            hourly_prices = []
            for hour in range(24):
                # 线性插值
                weight = hour / 24.0
                price = current_price * (1 - weight) + daily_prediction * weight
                hourly_prices.append(price)
            
            logger.info(f"BTC价格预测: 当前${current_price:.2f} -> 24h后${daily_prediction:.2f}")
            return hourly_prices
            
        except Exception as e:
            logger.warning(f"BTC预测失败，使用当前价格: {str(e)}")
            # 降级策略：使用当前价格
            latest_snapshot = NetworkSnapshot.query.filter_by(
                is_valid=True
            ).order_by(NetworkSnapshot.recorded_at.desc()).first()
            
            fallback_price = float(latest_snapshot.btc_price) if latest_snapshot else 50000.0
            return [fallback_price] * 24
    
    def _get_hourly_difficulty_forecast(self) -> List[float]:
        """获取未来24小时难度预测"""
        try:
            # 调用ARIMA预测
            forecast_result = forecast_difficulty(days=1)
            
            if not forecast_result or 'predictions' not in forecast_result:
                raise ValueError("Difficulty forecast failed")
            
            # 获取当前难度（数据库存储单位：万亿，需要转换为原始值）
            latest_snapshot = NetworkSnapshot.query.filter_by(
                is_valid=True
            ).order_by(NetworkSnapshot.recorded_at.desc()).first()
            
            current_diff_trillion = float(latest_snapshot.network_difficulty) if latest_snapshot else 60
            current_diff = current_diff_trillion * 1e12  # 转换为原始值
            
            # 难度变化较慢，使用当前值（24小时内变化不大）
            # ARIMA预测也以万亿为单位，需要转换
            daily_prediction_trillion = forecast_result['predictions'][0]['difficulty']
            daily_prediction = daily_prediction_trillion * 1e12  # 转换为原始值
            
            # 生成24小时序列（难度基本恒定）
            hourly_difficulty = [current_diff] * 24
            
            logger.info(f"难度预测: 当前{current_diff:.2e}, 24h后{daily_prediction:.2e}")
            return hourly_difficulty
            
        except Exception as e:
            logger.warning(f"难度预测失败，使用当前值: {str(e)}")
            latest_snapshot = NetworkSnapshot.query.filter_by(
                is_valid=True
            ).order_by(NetworkSnapshot.recorded_at.desc()).first()
            
            fallback_diff_trillion = float(latest_snapshot.network_difficulty) if latest_snapshot else 60
            fallback_diff = fallback_diff_trillion * 1e12  # 转换为原始值
            return [fallback_diff] * 24
    
    def _get_hourly_power_prices(self) -> List[float]:
        """获取未来24小时电价（USD/kWh）"""
        try:
            assert self.price_config is not None, "price_config must be initialized"
            config = self.price_config
            
            if config.price_mode == PriceMode.FIXED:
                # 固定电价
                price = float(config.fixed_price)
                return [price] * 24
            
            elif config.price_mode == PriceMode.PEAK_VALLEY:
                # 峰谷电价
                prices = []
                peak_start = config.peak_hours_start
                peak_end = config.peak_hours_end
                peak_price = float(config.peak_price)
                valley_price = float(config.valley_price)
                
                for hour in range(24):
                    if peak_start <= hour < peak_end:
                        prices.append(peak_price)
                    else:
                        prices.append(valley_price)
                return prices
            
            elif config.price_mode == PriceMode.HOURLY_24:
                # 24小时电价
                if config.hourly_prices:
                    hourly_data = json.loads(config.hourly_prices)
                    if isinstance(hourly_data, list) and len(hourly_data) == 24:
                        return [float(p) for p in hourly_data]
                
                # 降级到固定电价
                return [float(config.fixed_price or 0.1)] * 24
            
            elif config.price_mode == PriceMode.MONTHLY_CONTRACT:
                # 月度合约
                price = float(config.contract_price)
                return [price] * 24
            
            elif config.price_mode == PriceMode.API_REALTIME:
                # TODO: 调用外部API获取实时电价
                # 现在降级到固定电价
                logger.warning("API实时电价暂未实现，使用固定电价")
                return [float(config.fixed_price or 0.1)] * 24
            
            else:
                # 默认
                return [0.1] * 24
                
        except Exception as e:
            logger.error(f"获取电价失败: {str(e)}")
            return [0.1] * 24  # 降级默认值
    
    def _get_site_mining_stats(self) -> Dict:
        """获取矿场总算力和功耗"""
        try:
            miners = HostingMiner.query.filter_by(
                site_id=self.site_id,
                status='active'
            ).all()
            
            total_hashrate = sum(
                m.actual_hashrate or 
                (m.miner_model.reference_hashrate if m.miner_model else 0) 
                for m in miners
            )
            total_power = sum(
                m.actual_power or 
                (m.miner_model.reference_power if m.miner_model else 0) 
                for m in miners
            )
            
            return {
                'total_miners': len(miners),
                'total_hashrate_th': round(total_hashrate, 2),
                'total_power_kw': round(total_power / 1000, 2),  # W -> kW
                'avg_efficiency': round(total_power / total_hashrate, 2) if total_hashrate > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取矿场统计失败: {str(e)}")
            return {
                'total_miners': 0,
                'total_hashrate_th': 0,
                'total_power_kw': 0,
                'avg_efficiency': 0
            }
    
    def _calculate_btc_revenue(self, hashrate_th: float, difficulty: float) -> float:
        """
        计算每小时BTC产出
        
        Args:
            hashrate_th: 算力 (TH/s)
            difficulty: 网络难度
            
        Returns:
            BTC产出/小时
        """
        if hashrate_th <= 0 or difficulty <= 0:
            return 0.0
        
        # BTC产出公式: (hashrate / (difficulty * 2^32)) * block_reward * seconds_per_hour
        # hashrate / (difficulty * 2^32) = blocks_per_second
        # blocks_per_second * block_reward = BTC_per_second
        # BTC_per_second * seconds_per_hour = BTC_per_hour
        # 2^32 是Bitcoin挖矿难度算法的关键常数
        
        hashrate_hs = hashrate_th * 1e12  # TH/s -> H/s
        block_reward = 3.125
        seconds_per_hour = 3600  # 每小时3600秒
        
        # 每小时BTC产出（正确公式包含2^32因子和时间转换）
        btc_per_hour = (hashrate_hs / (difficulty * 2**32)) * block_reward * seconds_per_hour
        
        # DEBUG日志
        logger.info(f"BTC Revenue Calculation: hashrate={hashrate_th}TH/s, difficulty={difficulty}, btc_per_hour={btc_per_hour}")
        
        return btc_per_hour
    
    def _calculate_confidence(self, net_benefit: float, revenue: float) -> float:
        """
        计算限电决策的置信度 (0-1)
        
        Args:
            net_benefit: 净收益
            revenue: 总收益
            
        Returns:
            置信度 (0-1)
        """
        if revenue <= 0:
            return 0.0
        
        # 置信度 = |净收益| / 总收益
        confidence = abs(net_benefit) / revenue
        return min(confidence, 1.0)
    
    def _generate_recommendation(self, curtail_hours: pd.DataFrame, summary: Dict) -> Dict:
        """生成推荐策略"""
        try:
            if len(curtail_hours) == 0:
                return {
                    'action': 'no_curtailment',
                    'reason': '未来24小时无需限电，当前电价和BTC价格组合下持续挖矿更有利',
                    'optimal_hours': [],
                    'expected_benefit': 0
                }
            
            # 找出收益最高的连续时段
            curtail_hours = curtail_hours.sort_values('hour_of_day')
            optimal_hours = curtail_hours['hour_of_day'].tolist()
            
            # 生成推荐理由
            avg_benefit_per_hour = summary['net_benefit'] / len(curtail_hours)
            
            reason = f"建议在 {len(curtail_hours)} 个时段限电，预计净节省 ${summary['net_benefit']:.2f}。"
            reason += f"平均每小时节省 ${avg_benefit_per_hour:.2f}。"
            
            if summary['total_hours_curtailed'] >= 12:
                reason += "注意：限电时间较长，可能影响客户满意度。"
            
            return {
                'action': 'curtail',
                'reason': reason,
                'optimal_hours': optimal_hours,
                'expected_benefit': round(summary['net_benefit'], 2),
                'confidence': 'high' if avg_benefit_per_hour > 10 else 'medium'
            }
            
        except Exception as e:
            logger.error(f"生成推荐失败: {str(e)}")
            return {
                'action': 'error',
                'reason': str(e),
                'optimal_hours': [],
                'expected_benefit': 0
            }


def predict_optimal_curtailment(site_id: int, target_reduction_kw: Optional[float] = None) -> Dict:
    """
    预测最佳限电策略的便捷函数
    
    Args:
        site_id: 矿场ID
        target_reduction_kw: 目标功率削减量(kW)
        
    Returns:
        预测结果字典
    """
    try:
        predictor = CurtailmentPredictor(site_id)
        return predictor.predict_24h_schedule(target_reduction_kw)
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
