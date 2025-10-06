"""
Mining Operations Anomaly Detection Module
Uses statistical methods to detect anomalies in hashrate, power consumption, and ROI
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings

import pandas as pd
import numpy as np
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import UserMiner, MinerTelemetry, NetworkSnapshot, HostingMiner

logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore', category=RuntimeWarning)


def detect_hashrate_anomalies(user_id: int, lookback_days: int = 30) -> List[Dict]:
    """
    Detect hashrate anomalies using MAD (Median Absolute Deviation) method
    
    Args:
        user_id: User ID to analyze
        lookback_days: Number of days to look back (default 30)
        
    Returns:
        List of anomalies with timestamps and severity levels
        [
            {
                'timestamp': datetime,
                'miner_id': int,
                'hashrate': float,
                'expected_hashrate': float,
                'deviation': float,
                'severity': str,  # 'low', 'medium', 'high', 'critical'
                'anomaly_type': 'hashrate_drop' or 'hashrate_spike'
            }
        ]
    """
    try:
        logger.info(f"Starting hashrate anomaly detection for user {user_id}, lookback {lookback_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        user_miners = UserMiner.query.filter_by(user_id=user_id, status='active').all()
        
        if not user_miners:
            logger.warning(f"No active miners found for user {user_id}")
            return []
        
        all_anomalies = []
        
        for user_miner in user_miners:
            miner_telemetry = db.session.query(MinerTelemetry).join(HostingMiner).filter(
                HostingMiner.customer_id == user_id,
                MinerTelemetry.recorded_at >= cutoff_date
            ).order_by(MinerTelemetry.recorded_at.asc()).all()
            
            if len(miner_telemetry) < 10:
                logger.info(f"Insufficient telemetry data for miner {user_miner.id}, skipping")
                continue
            
            df = pd.DataFrame([
                {
                    'timestamp': t.recorded_at,
                    'miner_id': t.miner_id,
                    'hashrate': float(t.hashrate)
                }
                for t in miner_telemetry
            ])
            
            median_hashrate = df['hashrate'].median()
            mad = np.median(np.abs(df['hashrate'] - median_hashrate))
            
            if mad == 0:
                mad = df['hashrate'].std()
                if mad == 0:
                    logger.info(f"No variation in hashrate for miner {user_miner.id}, skipping")
                    continue
            
            threshold_multiplier = 3.0
            lower_bound = median_hashrate - threshold_multiplier * mad
            upper_bound = median_hashrate + threshold_multiplier * mad
            
            for _, row in df.iterrows():
                hashrate = row['hashrate']
                
                if hashrate < lower_bound or hashrate > upper_bound:
                    deviation_pct = abs((hashrate - median_hashrate) / median_hashrate * 100)
                    
                    if deviation_pct > 50:
                        severity = 'critical'
                    elif deviation_pct > 30:
                        severity = 'high'
                    elif deviation_pct > 15:
                        severity = 'medium'
                    else:
                        severity = 'low'
                    
                    anomaly_type = 'hashrate_drop' if hashrate < median_hashrate else 'hashrate_spike'
                    
                    anomaly = {
                        'timestamp': row['timestamp'],
                        'miner_id': int(row['miner_id']),
                        'hashrate': float(hashrate),
                        'expected_hashrate': float(median_hashrate),
                        'deviation': float(deviation_pct),
                        'severity': severity,
                        'anomaly_type': anomaly_type
                    }
                    all_anomalies.append(anomaly)
                    logger.debug(f"Detected {severity} hashrate anomaly: {anomaly}")
        
        logger.info(f"Found {len(all_anomalies)} hashrate anomalies for user {user_id}")
        return all_anomalies
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in hashrate anomaly detection: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in hashrate anomaly detection: {e}", exc_info=True)
        return []


def detect_power_anomalies(user_id: int, lookback_days: int = 30) -> List[Dict]:
    """
    Detect unusual power consumption patterns using statistical thresholds (mean ± 3*std)
    
    Args:
        user_id: User ID to analyze
        lookback_days: Number of days to look back (default 30)
        
    Returns:
        List of power consumption anomalies with details
        [
            {
                'timestamp': datetime,
                'miner_id': int,
                'power_consumption': float,
                'expected_power': float,
                'deviation': float,
                'severity': str,
                'anomaly_type': 'power_spike' or 'power_drop'
            }
        ]
    """
    try:
        logger.info(f"Starting power anomaly detection for user {user_id}, lookback {lookback_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        miner_telemetry = db.session.query(MinerTelemetry).join(HostingMiner).filter(
            HostingMiner.customer_id == user_id,
            MinerTelemetry.recorded_at >= cutoff_date
        ).order_by(MinerTelemetry.recorded_at.asc()).all()
        
        if len(miner_telemetry) < 10:
            logger.warning(f"Insufficient telemetry data for user {user_id}")
            return []
        
        df = pd.DataFrame([
            {
                'timestamp': t.recorded_at,
                'miner_id': t.miner_id,
                'power_consumption': float(t.power_consumption)
            }
            for t in miner_telemetry
        ])
        
        mean_power = df['power_consumption'].mean()
        std_power = df['power_consumption'].std()
        
        if std_power == 0:
            logger.info(f"No variation in power consumption for user {user_id}")
            return []
        
        lower_bound = mean_power - 3 * std_power
        upper_bound = mean_power + 3 * std_power
        
        anomalies = []
        
        for _, row in df.iterrows():
            power = row['power_consumption']
            
            if power < lower_bound or power > upper_bound:
                deviation_pct = abs((power - mean_power) / mean_power * 100)
                
                if deviation_pct > 40:
                    severity = 'critical'
                elif deviation_pct > 25:
                    severity = 'high'
                elif deviation_pct > 15:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                anomaly_type = 'power_drop' if power < mean_power else 'power_spike'
                
                anomaly = {
                    'timestamp': row['timestamp'],
                    'miner_id': int(row['miner_id']),
                    'power_consumption': float(power),
                    'expected_power': float(mean_power),
                    'deviation': float(deviation_pct),
                    'severity': severity,
                    'anomaly_type': anomaly_type
                }
                anomalies.append(anomaly)
                logger.debug(f"Detected {severity} power anomaly: {anomaly}")
        
        logger.info(f"Found {len(anomalies)} power consumption anomalies for user {user_id}")
        return anomalies
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in power anomaly detection: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in power anomaly detection: {e}", exc_info=True)
        return []


def detect_roi_anomalies(user_id: int) -> List[Dict]:
    """
    Monitor ROI degradation patterns and detect sudden drops >10%
    
    Args:
        user_id: User ID to analyze
        
    Returns:
        List of ROI anomalies with impact analysis
        [
            {
                'timestamp': datetime,
                'miner_id': int,
                'miner_name': str,
                'current_roi': float,
                'previous_roi': float,
                'roi_drop_pct': float,
                'severity': str,
                'impact_analysis': str,
                'estimated_loss_daily': float
            }
        ]
    """
    try:
        logger.info(f"Starting ROI anomaly detection for user {user_id}")
        
        user_miners = UserMiner.query.filter_by(user_id=user_id, status='active').all()
        
        if not user_miners:
            logger.warning(f"No active miners found for user {user_id}")
            return []
        
        latest_snapshot = NetworkSnapshot.query.filter_by(is_valid=True).order_by(
            NetworkSnapshot.recorded_at.desc()
        ).first()
        
        if not latest_snapshot:
            logger.error("No network snapshot available for ROI calculation")
            return []
        
        btc_price = float(latest_snapshot.btc_price)
        network_difficulty = float(latest_snapshot.network_difficulty)
        block_reward = float(latest_snapshot.block_reward)
        
        anomalies = []
        
        for miner in user_miners:
            current_hashrate = float(miner.actual_hashrate)
            original_hashrate = float(miner.original_hashrate) if miner.original_hashrate else current_hashrate
            power_consumption = float(miner.actual_power) / 1000.0
            electricity_cost = float(miner.electricity_cost)
            initial_cost = float(miner.actual_price)
            
            blocks_per_day = 144
            network_hashrate_th = network_difficulty * (2**32) / 600 / 1e12
            
            btc_per_day_current = (current_hashrate / network_hashrate_th) * block_reward * blocks_per_day
            revenue_per_day_current = btc_per_day_current * btc_price
            cost_per_day = power_consumption * 24 * electricity_cost
            profit_per_day_current = revenue_per_day_current - cost_per_day
            
            if initial_cost > 0:
                roi_current = (profit_per_day_current * 365 / initial_cost) * 100
            else:
                roi_current = 0
            
            btc_per_day_original = (original_hashrate / network_hashrate_th) * block_reward * blocks_per_day
            revenue_per_day_original = btc_per_day_original * btc_price
            profit_per_day_original = revenue_per_day_original - cost_per_day
            
            if initial_cost > 0:
                roi_original = (profit_per_day_original * 365 / initial_cost) * 100
            else:
                roi_original = 0
            
            if roi_original > 0:
                roi_drop_pct = ((roi_original - roi_current) / roi_original) * 100
            else:
                roi_drop_pct = 0
            
            if roi_drop_pct > 10:
                if roi_drop_pct > 50:
                    severity = 'critical'
                elif roi_drop_pct > 30:
                    severity = 'high'
                elif roi_drop_pct > 20:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                estimated_loss_daily = profit_per_day_original - profit_per_day_current
                
                impact_analysis = f"ROI degraded from {roi_original:.2f}% to {roi_current:.2f}%. "
                if roi_drop_pct > 30:
                    impact_analysis += "Immediate action required. Consider equipment upgrade or optimization."
                elif roi_drop_pct > 20:
                    impact_analysis += "Schedule maintenance to restore performance."
                else:
                    impact_analysis += "Monitor closely for further degradation."
                
                anomaly = {
                    'timestamp': datetime.utcnow(),
                    'miner_id': miner.id,
                    'miner_name': miner.custom_name or (miner.miner_model.model_name if miner.miner_model else 'Unknown'),
                    'current_roi': float(roi_current),
                    'previous_roi': float(roi_original),
                    'roi_drop_pct': float(roi_drop_pct),
                    'severity': severity,
                    'impact_analysis': impact_analysis,
                    'estimated_loss_daily': float(estimated_loss_daily)
                }
                anomalies.append(anomaly)
                logger.warning(f"Detected {severity} ROI anomaly: {anomaly}")
        
        logger.info(f"Found {len(anomalies)} ROI anomalies for user {user_id}")
        return anomalies
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in ROI anomaly detection: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in ROI anomaly detection: {e}", exc_info=True)
        return []


def generate_anomaly_report(user_id: int) -> Dict:
    """
    Generate comprehensive anomaly report combining all detection methods
    
    Args:
        user_id: User ID to analyze
        
    Returns:
        Comprehensive anomaly report
        {
            'user_id': int,
            'report_timestamp': datetime,
            'hashrate_anomalies': List[Dict],
            'power_anomalies': List[Dict],
            'roi_anomalies': List[Dict],
            'summary': {
                'total_anomalies': int,
                'critical_count': int,
                'high_count': int,
                'medium_count': int,
                'low_count': int,
                'overall_status': str,
                'recommendations': List[str]
            }
        }
    """
    try:
        logger.info(f"Generating comprehensive anomaly report for user {user_id}")
        
        hashrate_anomalies = detect_hashrate_anomalies(user_id, lookback_days=30)
        power_anomalies = detect_power_anomalies(user_id, lookback_days=30)
        roi_anomalies = detect_roi_anomalies(user_id)
        
        all_anomalies = hashrate_anomalies + power_anomalies + roi_anomalies
        
        critical_count = sum(1 for a in all_anomalies if a.get('severity') == 'critical')
        high_count = sum(1 for a in all_anomalies if a.get('severity') == 'high')
        medium_count = sum(1 for a in all_anomalies if a.get('severity') == 'medium')
        low_count = sum(1 for a in all_anomalies if a.get('severity') == 'low')
        
        if critical_count > 0:
            overall_status = 'CRITICAL'
        elif high_count > 0:
            overall_status = 'WARNING'
        elif medium_count > 0:
            overall_status = 'ATTENTION'
        elif low_count > 0:
            overall_status = 'MONITOR'
        else:
            overall_status = 'NORMAL'
        
        recommendations = []
        
        if len(hashrate_anomalies) > 0:
            severe_hashrate = [a for a in hashrate_anomalies if a['severity'] in ['critical', 'high']]
            if severe_hashrate:
                recommendations.append("Critical hashrate drops detected. Schedule immediate equipment inspection.")
        
        if len(power_anomalies) > 0:
            severe_power = [a for a in power_anomalies if a['severity'] in ['critical', 'high']]
            if severe_power:
                recommendations.append("Unusual power consumption patterns detected. Check cooling systems and electrical connections.")
        
        if len(roi_anomalies) > 0:
            severe_roi = [a for a in roi_anomalies if a['severity'] in ['critical', 'high']]
            if severe_roi:
                recommendations.append("Significant ROI degradation detected. Consider equipment upgrade or operational optimization.")
        
        if len(all_anomalies) == 0:
            recommendations.append("All systems operating normally. Continue regular monitoring.")
        
        report = {
            'user_id': user_id,
            'report_timestamp': datetime.utcnow(),
            'hashrate_anomalies': hashrate_anomalies,
            'power_anomalies': power_anomalies,
            'roi_anomalies': roi_anomalies,
            'summary': {
                'total_anomalies': len(all_anomalies),
                'critical_count': critical_count,
                'high_count': high_count,
                'medium_count': medium_count,
                'low_count': low_count,
                'overall_status': overall_status,
                'recommendations': recommendations
            }
        }
        
        logger.info(f"Anomaly report generated for user {user_id}: {overall_status} status with {len(all_anomalies)} total anomalies")
        return report
        
    except Exception as e:
        logger.error(f"Error generating anomaly report: {e}", exc_info=True)
        return {
            'user_id': user_id,
            'report_timestamp': datetime.utcnow(),
            'hashrate_anomalies': [],
            'power_anomalies': [],
            'roi_anomalies': [],
            'summary': {
                'total_anomalies': 0,
                'critical_count': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0,
                'overall_status': 'ERROR',
                'recommendations': ['Error generating report. Please check logs.']
            }
        }
