"""
矿机性能评分引擎
Miner Performance Scoring Engine

计算矿机性能评分（0-100分），基于算力比例、能效比和在线时长
Calculates miner performance scores (0-100) based on hashrate ratio, power efficiency, and uptime
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import MinerPerformanceScore, HostingMiner, MinerTelemetry, MinerModel

logger = logging.getLogger(__name__)


def _floor_to_15_minutes(dt: datetime) -> datetime:
    """
    将时间向下取整到15分钟边界（floor-bucket逻辑）
    Floor datetime to 15-minute boundary (floor-bucket logic)
    
    确保同一个15分钟时段内的所有运行都映射到相同时间戳
    Ensures all runs within the same 15-minute period map to the same timestamp
    
    Args:
        dt: 输入时间 Input datetime
        
    Returns:
        向下取整后的时间 Floored datetime
        
    Examples:
        10:05 -> 10:00
        10:10 -> 10:00
        10:14 -> 10:00
        10:15 -> 10:15
        10:29 -> 10:15
    """
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


def calculate_miner_performance(miner_id: int, evaluation_period_hours: int = 24) -> Optional[Dict]:
    """
    计算单个矿机性能评分
    Calculate performance score for a single miner
    
    Args:
        miner_id: 矿机ID Miner ID
        evaluation_period_hours: 评估周期（小时），默认24小时 Evaluation period in hours, default 24
        
    Returns:
        Dict containing performance metrics or None if failed:
        {
            'miner_id': int,
            'performance_score': float,
            'hashrate_ratio': float,
            'power_efficiency_ratio': float,
            'uptime_ratio': float,
            'temperature_avg': float,
            'error_rate': float,
            'calculated_at': datetime
        }
    """
    try:
        logger.info(f"开始计算矿机 {miner_id} 的性能评分，评估周期：{evaluation_period_hours}小时")
        logger.info(f"Starting performance calculation for miner {miner_id}, period: {evaluation_period_hours}h")
        
        # 获取矿机信息 Get miner info
        miner = HostingMiner.query.get(miner_id)
        if not miner:
            logger.error(f"矿机 {miner_id} 不存在 Miner {miner_id} not found")
            return None
        
        # 获取矿机型号信息 Get miner model info
        miner_model = MinerModel.query.get(miner.miner_model_id)
        if not miner_model:
            logger.error(f"矿机型号 {miner.miner_model_id} 不存在 Miner model {miner.miner_model_id} not found")
            return None
        
        # 计算时间范围 Calculate time range
        current_time = datetime.utcnow()
        start_time = current_time - timedelta(hours=evaluation_period_hours)
        
        # 查询遥测数据 Query telemetry data
        telemetry_records = MinerTelemetry.query.filter(
            MinerTelemetry.miner_id == miner_id,
            MinerTelemetry.recorded_at >= start_time,
            MinerTelemetry.recorded_at <= current_time
        ).order_by(MinerTelemetry.recorded_at.desc()).all()
        
        # 向下取整计算时间到15分钟边界 Floor calculated_at to 15-minute boundary
        calculated_at = _floor_to_15_minutes(current_time)
        
        if not telemetry_records:
            logger.warning(f"矿机 {miner_id} 在过去 {evaluation_period_hours} 小时内无遥测数据，保存评分为0")
            logger.warning(f"No telemetry data for miner {miner_id} in the past {evaluation_period_hours} hours, saving score as 0")
            
            # 保存性能评分为0，标记为"无数据"状态
            # Save performance score as 0, mark as "no data" status
            try:
                existing_record = MinerPerformanceScore.query.filter_by(
                    miner_id=miner_id,
                    calculated_at=calculated_at
                ).first()
                
                if existing_record:
                    existing_record.performance_score = Decimal('0')
                    existing_record.hashrate_ratio = Decimal('0')
                    existing_record.power_efficiency_ratio = Decimal('0')
                    existing_record.uptime_ratio = Decimal('0')
                    existing_record.temperature_avg = None
                    existing_record.error_rate = None
                    existing_record.evaluation_period_hours = evaluation_period_hours
                else:
                    new_record = MinerPerformanceScore(
                        miner_id=miner_id,
                        performance_score=Decimal('0'),
                        hashrate_ratio=Decimal('0'),
                        power_efficiency_ratio=Decimal('0'),
                        uptime_ratio=Decimal('0'),
                        temperature_avg=None,
                        error_rate=None,
                        evaluation_period_hours=evaluation_period_hours,
                        calculated_at=calculated_at
                    )
                    db.session.add(new_record)
                
                db.session.commit()
                logger.info(f"矿机 {miner_id} 无数据，已保存评分为0 Miner {miner_id} has no data, saved score as 0")
                
                return {
                    'miner_id': miner_id,
                    'performance_score': 0.0,
                    'hashrate_ratio': 0.0,
                    'power_efficiency_ratio': 0.0,
                    'uptime_ratio': 0.0,
                    'temperature_avg': None,
                    'error_rate': None,
                    'evaluation_period_hours': evaluation_period_hours,
                    'calculated_at': calculated_at,
                    'no_data': True
                }
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"保存离线矿机评分失败 Failed to save offline miner score: {e}")
                return None
        
        logger.info(f"找到 {len(telemetry_records)} 条遥测记录 Found {len(telemetry_records)} telemetry records")
        
        # 计算平均值 Calculate averages
        total_hashrate = 0.0
        total_power = 0.0
        total_temperature = 0.0
        temp_count = 0
        total_accepted_shares = 0
        total_rejected_shares = 0
        
        for record in telemetry_records:
            total_hashrate += float(record.hashrate)
            total_power += float(record.power_consumption)
            
            if record.temperature is not None:
                total_temperature += float(record.temperature)
                temp_count += 1
            
            if record.accepted_shares is not None:
                total_accepted_shares += record.accepted_shares
            if record.rejected_shares is not None:
                total_rejected_shares += record.rejected_shares
        
        num_records = len(telemetry_records)
        avg_hashrate = total_hashrate / num_records
        avg_power = total_power / num_records
        avg_temperature = total_temperature / temp_count if temp_count > 0 else None
        
        # 计算算力比例 Calculate hashrate ratio
        if miner_model.reference_hashrate <= 0:
            logger.error(f"参考算力为0或负数，无法计算 Reference hashrate is 0 or negative")
            return None
        hashrate_ratio = avg_hashrate / float(miner_model.reference_hashrate)
        
        # 计算能效比 Calculate power efficiency ratio
        # 公式：reference_power / avg_power (越节能，比例越高)
        # Formula: reference_power / avg_power (higher ratio = more efficient)
        if avg_power <= 0:
            logger.error(f"平均功耗为0或负数，无法计算 Average power is 0 or negative")
            return None
        power_efficiency_ratio = float(miner_model.reference_power) / avg_power
        
        # 计算在线时长比例 Calculate uptime ratio
        # 每15分钟一个数据点，evaluation_period_hours * 4 个点
        # One data point per 15 minutes, evaluation_period_hours * 4 points
        expected_data_points = evaluation_period_hours * 4
        actual_data_points = num_records
        uptime_ratio = min(actual_data_points / expected_data_points, 1.0)  # 不超过1.0 Cap at 1.0
        
        # 计算错误率 Calculate error rate
        total_shares = total_accepted_shares + total_rejected_shares
        error_rate = (total_rejected_shares / total_shares) if total_shares > 0 else 0.0
        
        # 计算综合性能评分 Calculate composite performance score
        # 公式：performance_score = (hashrate_ratio × 70%) + (power_efficiency_ratio × 20%) + (uptime_ratio × 10%)
        # Formula: performance_score = (hashrate_ratio × 70%) + (power_efficiency_ratio × 20%) + (uptime_ratio × 10%)
        performance_score = (
            hashrate_ratio * 0.70 +
            power_efficiency_ratio * 0.20 +
            uptime_ratio * 0.10
        ) * 100.0  # 转换为0-100分 Convert to 0-100 scale
        
        # 限制评分范围 Cap score range
        performance_score = max(0.0, min(100.0, performance_score))
        
        # 准备结果 Prepare result
        result = {
            'miner_id': miner_id,
            'performance_score': round(performance_score, 2),
            'hashrate_ratio': round(hashrate_ratio, 4),
            'power_efficiency_ratio': round(power_efficiency_ratio, 4),
            'uptime_ratio': round(uptime_ratio, 4),
            'temperature_avg': round(avg_temperature, 2) if avg_temperature is not None else None,
            'error_rate': round(error_rate, 4),
            'evaluation_period_hours': evaluation_period_hours,
            'calculated_at': calculated_at
        }
        
        # 保存到数据库 Save to database
        try:
            # 检查是否已存在记录 Check if record exists
            existing_record = MinerPerformanceScore.query.filter_by(
                miner_id=miner_id,
                calculated_at=calculated_at
            ).first()
            
            if existing_record:
                # 更新现有记录 Update existing record
                logger.info(f"更新现有性能评分记录 Updating existing performance score record")
                existing_record.performance_score = Decimal(str(result['performance_score']))
                existing_record.hashrate_ratio = Decimal(str(result['hashrate_ratio']))
                existing_record.power_efficiency_ratio = Decimal(str(result['power_efficiency_ratio']))
                existing_record.uptime_ratio = Decimal(str(result['uptime_ratio']))
                existing_record.temperature_avg = Decimal(str(result['temperature_avg'])) if result['temperature_avg'] is not None else None
                existing_record.error_rate = Decimal(str(result['error_rate']))
                existing_record.evaluation_period_hours = evaluation_period_hours
            else:
                # 创建新记录 Create new record
                logger.info(f"创建新性能评分记录 Creating new performance score record")
                new_record = MinerPerformanceScore(
                    miner_id=miner_id,
                    performance_score=Decimal(str(result['performance_score'])),
                    hashrate_ratio=Decimal(str(result['hashrate_ratio'])),
                    power_efficiency_ratio=Decimal(str(result['power_efficiency_ratio'])),
                    uptime_ratio=Decimal(str(result['uptime_ratio'])),
                    temperature_avg=Decimal(str(result['temperature_avg'])) if result['temperature_avg'] is not None else None,
                    error_rate=Decimal(str(result['error_rate'])),
                    evaluation_period_hours=evaluation_period_hours,
                    calculated_at=calculated_at
                )
                db.session.add(new_record)
            
            db.session.commit()
            logger.info(f"矿机 {miner_id} 性能评分已保存：{result['performance_score']:.2f}分")
            logger.info(f"Miner {miner_id} performance score saved: {result['performance_score']:.2f}")
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"保存性能评分失败 Failed to save performance score: {e}")
            raise
        
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"数据库错误 Database error in calculate_miner_performance: {e}")
        db.session.rollback()
        return None
    except Exception as e:
        logger.error(f"计算矿机性能评分时发生错误 Error in calculate_miner_performance: {e}")
        db.session.rollback()
        return None


def calculate_all_miners_performance(site_id: Optional[int] = None, evaluation_period_hours: int = 24) -> Dict:
    """
    批量计算所有矿机的性能评分（优化版本，使用聚合查询）
    Calculate performance scores for all miners in batch (optimized version using aggregation queries)
    
    性能优化：使用SQLAlchemy聚合函数一次性查询所有矿机数据，避免N+1查询问题
    Performance optimization: Use SQLAlchemy aggregation to query all miner data at once, avoiding N+1 query problem
    
    Args:
        site_id: 站点ID（可选），如果提供则只计算该站点的矿机 Site ID (optional), if provided only calculate miners at this site
        evaluation_period_hours: 评估周期（小时），默认24小时 Evaluation period in hours, default 24
        
    Returns:
        Dict containing:
        {
            'total_miners': int,
            'successful': int,
            'failed': int,
            'results': List[Dict],
            'errors': List[Dict]
        }
    """
    try:
        logger.info(f"开始批量计算矿机性能评分（优化版本）Starting batch performance calculation (optimized version)")
        if site_id:
            logger.info(f"仅计算站点 {site_id} 的矿机 Only calculating miners for site {site_id}")
        
        # 计算时间范围 Calculate time range
        current_time = datetime.utcnow()
        start_time = current_time - timedelta(hours=evaluation_period_hours)
        calculated_at = _floor_to_15_minutes(current_time)
        
        # 构建矿机查询 Build miner query
        # 获取所有矿机（包括离线、维护、错误状态的矿机）
        # Get all miners (including offline, maintenance, error status miners)
        miner_query = db.session.query(
            HostingMiner.id,
            HostingMiner.miner_model_id,
            MinerModel.reference_hashrate,
            MinerModel.reference_power
        ).join(
            MinerModel,
            HostingMiner.miner_model_id == MinerModel.id
        )
        
        if site_id:
            miner_query = miner_query.filter(HostingMiner.site_id == site_id)
        
        miners_data = miner_query.all()
        
        if not miners_data:
            logger.warning(f"未找到符合条件的矿机 No miners found matching criteria")
            return {
                'total_miners': 0,
                'successful': 0,
                'failed': 0,
                'results': [],
                'errors': []
            }
        
        logger.info(f"找到 {len(miners_data)} 个矿机待计算 Found {len(miners_data)} miners to calculate")
        
        # 批量查询所有矿机的遥测聚合数据 Batch query telemetry aggregation for all miners
        # 一次性获取所有矿机的平均算力、功耗、温度和份额统计
        # Get avg hashrate, power, temperature and share stats for all miners in one query
        telemetry_agg = db.session.query(
            MinerTelemetry.miner_id,
            func.avg(MinerTelemetry.hashrate).label('avg_hashrate'),
            func.avg(MinerTelemetry.power_consumption).label('avg_power'),
            func.avg(MinerTelemetry.temperature).label('avg_temp'),
            func.count(MinerTelemetry.id).label('data_points'),
            func.sum(MinerTelemetry.accepted_shares).label('total_accepted'),
            func.sum(MinerTelemetry.rejected_shares).label('total_rejected')
        ).filter(
            MinerTelemetry.recorded_at >= start_time,
            MinerTelemetry.recorded_at <= current_time
        ).group_by(MinerTelemetry.miner_id).all()
        
        # 转换为字典以便快速查找 Convert to dict for fast lookup
        telemetry_dict = {
            row.miner_id: {
                'avg_hashrate': float(row.avg_hashrate) if row.avg_hashrate else 0.0,
                'avg_power': float(row.avg_power) if row.avg_power else 0.0,
                'avg_temp': float(row.avg_temp) if row.avg_temp else None,
                'data_points': row.data_points,
                'total_accepted': row.total_accepted or 0,
                'total_rejected': row.total_rejected or 0
            }
            for row in telemetry_agg
        }
        
        logger.info(f"批量查询获取了 {len(telemetry_dict)} 个矿机的遥测数据 Batch query retrieved telemetry for {len(telemetry_dict)} miners")
        
        # 批量计算性能评分 Calculate performance scores in batch
        results = []
        errors = []
        successful = 0
        failed = 0
        expected_data_points = evaluation_period_hours * 4
        
        # 准备批量插入/更新的记录 Prepare records for batch insert/update
        scores_to_save = []
        
        for miner_id, miner_model_id, reference_hashrate, reference_power in miners_data:
            try:
                telemetry = telemetry_dict.get(miner_id)
                
                # 如果没有遥测数据，保存评分为0 If no telemetry data, save score as 0
                if not telemetry or telemetry['data_points'] == 0:
                    logger.debug(f"矿机 {miner_id} 无遥测数据，保存评分为0 Miner {miner_id} has no telemetry, saving score as 0")
                    scores_to_save.append({
                        'miner_id': miner_id,
                        'performance_score': 0.0,
                        'hashrate_ratio': 0.0,
                        'power_efficiency_ratio': 0.0,
                        'uptime_ratio': 0.0,
                        'temperature_avg': None,
                        'error_rate': None,
                        'no_data': True
                    })
                    successful += 1
                    continue
                
                # 计算性能指标 Calculate performance metrics
                avg_hashrate = telemetry['avg_hashrate']
                avg_power = telemetry['avg_power']
                avg_temp = telemetry['avg_temp']
                data_points = telemetry['data_points']
                total_accepted = telemetry['total_accepted']
                total_rejected = telemetry['total_rejected']
                
                # 验证参考值 Validate reference values
                if reference_hashrate <= 0 or reference_power <= 0:
                    logger.warning(f"矿机 {miner_id} 参考值无效 Miner {miner_id} has invalid reference values")
                    failed += 1
                    errors.append({
                        'miner_id': miner_id,
                        'error': '参考算力或功耗为0或负数 Reference hashrate or power is 0 or negative'
                    })
                    continue
                
                if avg_power <= 0:
                    logger.warning(f"矿机 {miner_id} 平均功耗无效 Miner {miner_id} has invalid average power")
                    failed += 1
                    errors.append({
                        'miner_id': miner_id,
                        'error': '平均功耗为0或负数 Average power is 0 or negative'
                    })
                    continue
                
                # 计算比例 Calculate ratios
                hashrate_ratio = avg_hashrate / float(reference_hashrate)
                power_efficiency_ratio = float(reference_power) / avg_power
                uptime_ratio = min(data_points / expected_data_points, 1.0)
                
                # 计算错误率 Calculate error rate
                total_shares = total_accepted + total_rejected
                error_rate = (total_rejected / total_shares) if total_shares > 0 else 0.0
                
                # 计算综合性能评分 Calculate composite performance score
                performance_score = (
                    hashrate_ratio * 0.70 +
                    power_efficiency_ratio * 0.20 +
                    uptime_ratio * 0.10
                ) * 100.0
                
                # 限制评分范围 Cap score range
                performance_score = max(0.0, min(100.0, performance_score))
                
                scores_to_save.append({
                    'miner_id': miner_id,
                    'performance_score': round(performance_score, 2),
                    'hashrate_ratio': round(hashrate_ratio, 4),
                    'power_efficiency_ratio': round(power_efficiency_ratio, 4),
                    'uptime_ratio': round(uptime_ratio, 4),
                    'temperature_avg': round(avg_temp, 2) if avg_temp is not None else None,
                    'error_rate': round(error_rate, 4),
                    'no_data': False
                })
                successful += 1
                
            except Exception as e:
                failed += 1
                errors.append({
                    'miner_id': miner_id,
                    'error': str(e)
                })
                logger.error(f"计算矿机 {miner_id} 性能时发生错误 Error calculating miner {miner_id}: {e}")
        
        # 批量保存到数据库 Batch save to database
        logger.info(f"开始批量保存 {len(scores_to_save)} 条性能评分记录 Starting batch save of {len(scores_to_save)} performance score records")
        
        try:
            for score_data in scores_to_save:
                miner_id = score_data['miner_id']
                
                # 检查是否已存在记录 Check if record exists
                existing_record = MinerPerformanceScore.query.filter_by(
                    miner_id=miner_id,
                    calculated_at=calculated_at
                ).first()
                
                if existing_record:
                    # 更新现有记录 Update existing record
                    existing_record.performance_score = Decimal(str(score_data['performance_score']))
                    existing_record.hashrate_ratio = Decimal(str(score_data['hashrate_ratio']))
                    existing_record.power_efficiency_ratio = Decimal(str(score_data['power_efficiency_ratio']))
                    existing_record.uptime_ratio = Decimal(str(score_data['uptime_ratio']))
                    existing_record.temperature_avg = Decimal(str(score_data['temperature_avg'])) if score_data['temperature_avg'] is not None else None
                    existing_record.error_rate = Decimal(str(score_data['error_rate'])) if score_data['error_rate'] is not None else None
                    existing_record.evaluation_period_hours = evaluation_period_hours
                else:
                    # 创建新记录 Create new record
                    new_record = MinerPerformanceScore(
                        miner_id=miner_id,
                        performance_score=Decimal(str(score_data['performance_score'])),
                        hashrate_ratio=Decimal(str(score_data['hashrate_ratio'])),
                        power_efficiency_ratio=Decimal(str(score_data['power_efficiency_ratio'])),
                        uptime_ratio=Decimal(str(score_data['uptime_ratio'])),
                        temperature_avg=Decimal(str(score_data['temperature_avg'])) if score_data['temperature_avg'] is not None else None,
                        error_rate=Decimal(str(score_data['error_rate'])) if score_data['error_rate'] is not None else None,
                        evaluation_period_hours=evaluation_period_hours,
                        calculated_at=calculated_at
                    )
                    db.session.add(new_record)
                
                # 添加到结果列表 Add to results list
                results.append({
                    'miner_id': miner_id,
                    'performance_score': score_data['performance_score'],
                    'hashrate_ratio': score_data['hashrate_ratio'],
                    'power_efficiency_ratio': score_data['power_efficiency_ratio'],
                    'uptime_ratio': score_data['uptime_ratio'],
                    'temperature_avg': score_data['temperature_avg'],
                    'error_rate': score_data['error_rate'],
                    'evaluation_period_hours': evaluation_period_hours,
                    'calculated_at': calculated_at,
                    'no_data': score_data.get('no_data', False)
                })
            
            # 一次性提交所有更改 Commit all changes at once
            db.session.commit()
            logger.info(f"批量保存完成 Batch save completed")
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"批量保存失败 Batch save failed: {e}")
            raise
        
        summary = {
            'total_miners': len(miners_data),
            'successful': successful,
            'failed': failed,
            'results': results,
            'errors': errors
        }
        
        logger.info(f"批量计算完成：成功 {successful}，失败 {failed}")
        logger.info(f"Batch calculation completed: {successful} successful, {failed} failed")
        logger.info(f"性能提升：批量查询替代了 {len(miners_data)} 次单独查询")
        logger.info(f"Performance improvement: Batch query replaced {len(miners_data)} individual queries")
        
        return summary
        
    except SQLAlchemyError as e:
        logger.error(f"数据库错误 Database error in calculate_all_miners_performance: {e}")
        db.session.rollback()
        return {
            'total_miners': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'errors': [{'error': str(e)}]
        }
    except Exception as e:
        logger.error(f"批量计算时发生错误 Error in calculate_all_miners_performance: {e}")
        db.session.rollback()
        return {
            'total_miners': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'errors': [{'error': str(e)}]
        }


def get_latest_performance_scores(site_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
    """
    获取最新的性能评分记录
    Get latest performance score records
    
    Args:
        site_id: 站点ID（可选），如果提供则只获取该站点的矿机 Site ID (optional), if provided only get miners at this site
        limit: 返回记录数限制，默认100 Limit number of records returned, default 100
        
    Returns:
        List of performance score dicts
    """
    try:
        logger.info(f"获取最新性能评分，限制 {limit} 条 Getting latest performance scores, limit {limit}")
        
        # 构建查询 Build query
        query = db.session.query(
            MinerPerformanceScore,
            HostingMiner.serial_number,
            HostingMiner.site_id,
            MinerModel.model_name
        ).join(
            HostingMiner,
            MinerPerformanceScore.miner_id == HostingMiner.id
        ).join(
            MinerModel,
            HostingMiner.miner_model_id == MinerModel.id
        )
        
        # 如果指定站点，添加过滤 Add site filter if specified
        if site_id:
            query = query.filter(HostingMiner.site_id == site_id)
            logger.info(f"仅获取站点 {site_id} 的记录 Only getting records for site {site_id}")
        
        # 按计算时间降序排列 Order by calculated_at descending
        query = query.order_by(MinerPerformanceScore.calculated_at.desc())
        
        # 限制记录数 Limit records
        records = query.limit(limit).all()
        
        if not records:
            logger.info(f"未找到性能评分记录 No performance score records found")
            return []
        
        logger.info(f"找到 {len(records)} 条性能评分记录 Found {len(records)} performance score records")
        
        # 转换为字典列表 Convert to list of dicts
        results = []
        for score, serial_number, site_id_val, model_name in records:
            results.append({
                'id': score.id,
                'miner_id': score.miner_id,
                'serial_number': serial_number,
                'site_id': site_id_val,
                'model_name': model_name,
                'performance_score': float(score.performance_score),
                'hashrate_ratio': float(score.hashrate_ratio),
                'power_efficiency_ratio': float(score.power_efficiency_ratio),
                'uptime_ratio': float(score.uptime_ratio),
                'temperature_avg': float(score.temperature_avg) if score.temperature_avg else None,
                'error_rate': float(score.error_rate) if score.error_rate else None,
                'evaluation_period_hours': score.evaluation_period_hours,
                'calculated_at': score.calculated_at.isoformat() if score.calculated_at else None
            })
        
        return results
        
    except SQLAlchemyError as e:
        logger.error(f"数据库错误 Database error in get_latest_performance_scores: {e}")
        return []
    except Exception as e:
        logger.error(f"获取性能评分时发生错误 Error in get_latest_performance_scores: {e}")
        return []


def get_miner_performance_history(miner_id: int, days: int = 7) -> List[Dict]:
    """
    获取矿机性能评分历史
    Get miner performance score history
    
    Args:
        miner_id: 矿机ID Miner ID
        days: 获取最近几天的记录，默认7天 Number of days to look back, default 7
        
    Returns:
        List of performance score dicts ordered by time
    """
    try:
        logger.info(f"获取矿机 {miner_id} 最近 {days} 天的性能历史")
        logger.info(f"Getting performance history for miner {miner_id}, last {days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        records = MinerPerformanceScore.query.filter(
            MinerPerformanceScore.miner_id == miner_id,
            MinerPerformanceScore.calculated_at >= cutoff_date
        ).order_by(MinerPerformanceScore.calculated_at.asc()).all()
        
        if not records:
            logger.info(f"未找到矿机 {miner_id} 的性能历史记录 No performance history found for miner {miner_id}")
            return []
        
        logger.info(f"找到 {len(records)} 条历史记录 Found {len(records)} history records")
        
        results = []
        for score in records:
            results.append({
                'id': score.id,
                'miner_id': score.miner_id,
                'performance_score': float(score.performance_score),
                'hashrate_ratio': float(score.hashrate_ratio),
                'power_efficiency_ratio': float(score.power_efficiency_ratio),
                'uptime_ratio': float(score.uptime_ratio),
                'temperature_avg': float(score.temperature_avg) if score.temperature_avg else None,
                'error_rate': float(score.error_rate) if score.error_rate else None,
                'evaluation_period_hours': score.evaluation_period_hours,
                'calculated_at': score.calculated_at.isoformat() if score.calculated_at else None
            })
        
        return results
        
    except SQLAlchemyError as e:
        logger.error(f"数据库错误 Database error in get_miner_performance_history: {e}")
        return []
    except Exception as e:
        logger.error(f"获取性能历史时发生错误 Error in get_miner_performance_history: {e}")
        return []
