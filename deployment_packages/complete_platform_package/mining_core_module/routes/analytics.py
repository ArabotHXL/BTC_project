"""
分析路由模块
Analytics Routes Module

提供数据分析、技术指标和报告生成功能
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template
from models import (MarketAnalytics, TechnicalIndicators, MiningMetrics, 
                   NetworkSnapshot, SLAMetrics, db)
from modules.analytics.engines.analytics_engine import AnalyticsEngine
from modules.analytics.engines.historical_data_engine import HistoricalDataEngine
from modules.analytics.reports.professional_report_generator import ProfessionalReportGenerator

# 创建蓝图
analytics_bp = Blueprint('analytics', __name__)

logger = logging.getLogger(__name__)

@analytics_bp.route('/')
def index():
    """分析模块主页面"""
    try:
        # 获取最新统计数据
        stats = get_dashboard_stats()
        return render_template('analytics/index.html', stats=stats)
    except Exception as e:
        logger.error(f"加载分析页面失败: {e}")
        return render_template('errors/500.html'), 500

@analytics_bp.route('/api/dashboard-stats')
def dashboard_stats():
    """获取仪表板统计数据API"""
    try:
        stats = get_dashboard_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        # 市场数据统计
        latest_market = MarketAnalytics.query.order_by(
            MarketAnalytics.recorded_at.desc()
        ).first()
        
        # 技术指标统计
        latest_indicators = TechnicalIndicators.query.order_by(
            TechnicalIndicators.recorded_at.desc()
        ).first()
        
        # 挖矿指标统计
        latest_mining = MiningMetrics.query.order_by(
            MiningMetrics.recorded_at.desc()
        ).first()
        
        # 网络快照统计
        latest_network = NetworkSnapshot.query.order_by(
            NetworkSnapshot.recorded_at.desc()
        ).first()
        
        # 统计数据记录数量
        data_counts = {
            'market_records': MarketAnalytics.query.count(),
            'technical_records': TechnicalIndicators.query.count(),
            'mining_records': MiningMetrics.query.count(),
            'network_records': NetworkSnapshot.query.count()
        }
        
        return {
            'latest_market': latest_market.to_dict() if latest_market else None,
            'latest_indicators': latest_indicators.to_dict() if latest_indicators else None,
            'latest_mining': latest_mining.to_dict() if latest_mining else None,
            'latest_network': latest_network.to_dict() if latest_network else None,
            'data_counts': data_counts,
            'last_updated': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return {}

@analytics_bp.route('/api/market-data')
def get_market_data():
    """获取市场数据API"""
    try:
        # 获取查询参数
        days = int(request.args.get('days', 30))
        limit = int(request.args.get('limit', 100))
        
        # 计算时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 查询数据
        market_data = MarketAnalytics.query.filter(
            MarketAnalytics.recorded_at >= start_date,
            MarketAnalytics.recorded_at <= end_date
        ).order_by(MarketAnalytics.recorded_at.desc()).limit(limit).all()
        
        data_list = [record.to_dict() for record in market_data]
        
        return jsonify({
            'success': True,
            'data': data_list,
            'count': len(data_list),
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/technical-indicators')
def get_technical_indicators():
    """获取技术指标数据API"""
    try:
        days = int(request.args.get('days', 7))
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        indicators = TechnicalIndicators.query.filter(
            TechnicalIndicators.recorded_at >= start_date,
            TechnicalIndicators.recorded_at <= end_date
        ).order_by(TechnicalIndicators.recorded_at.desc()).all()
        
        data_list = [record.to_dict() for record in indicators]
        
        return jsonify({
            'success': True,
            'data': data_list,
            'count': len(data_list)
        })
        
    except Exception as e:
        logger.error(f"获取技术指标失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/mining-metrics')
def get_mining_metrics():
    """获取挖矿指标数据API"""
    try:
        days = int(request.args.get('days', 7))
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        metrics = MiningMetrics.query.filter(
            MiningMetrics.recorded_at >= start_date,
            MiningMetrics.recorded_at <= end_date
        ).order_by(MiningMetrics.recorded_at.desc()).all()
        
        data_list = [record.to_dict() for record in metrics]
        
        return jsonify({
            'success': True,
            'data': data_list,
            'count': len(data_list)
        })
        
    except Exception as e:
        logger.error(f"获取挖矿指标失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/collect-data', methods=['POST'])
def collect_data():
    """手动触发数据收集API"""
    try:
        data_type = request.json.get('type', 'all') if request.is_json else 'all'
        
        # 初始化数据收集引擎
        analytics_engine = AnalyticsEngine()
        
        if data_type == 'all' or data_type == 'market':
            # 收集市场数据
            market_result = analytics_engine.collect_market_data()
            logger.info(f"市场数据收集结果: {market_result}")
        
        if data_type == 'all' or data_type == 'historical':
            # 收集历史数据
            historical_engine = HistoricalDataEngine()
            historical_result = historical_engine.backfill_recent_data(days=1)
            logger.info(f"历史数据收集结果: {historical_result}")
        
        return jsonify({
            'success': True,
            'message': '数据收集任务已启动',
            'type': data_type,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"数据收集失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '数据收集失败'
        }), 500

@analytics_bp.route('/api/generate-report', methods=['POST'])
def generate_report():
    """生成分析报告API"""
    try:
        data = request.get_json()
        
        report_type = data.get('type', 'mining_analysis')
        format_type = data.get('format', 'json')
        period_days = int(data.get('days', 30))
        
        # 收集报告数据
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # 获取相关数据
        market_data = MarketAnalytics.query.filter(
            MarketAnalytics.recorded_at >= start_date
        ).order_by(MarketAnalytics.recorded_at.desc()).all()
        
        mining_data = MiningMetrics.query.filter(
            MiningMetrics.recorded_at >= start_date
        ).order_by(MiningMetrics.recorded_at.desc()).all()
        
        technical_data = TechnicalIndicators.query.filter(
            TechnicalIndicators.recorded_at >= start_date
        ).order_by(TechnicalIndicators.recorded_at.desc()).all()
        
        # 准备报告数据
        report_data = {
            'market_data': [record.to_dict() for record in market_data],
            'mining_data': [record.to_dict() for record in mining_data],
            'technical_data': [record.to_dict() for record in technical_data],
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': period_days
            }
        }
        
        # 生成报告
        report_generator = ProfessionalReportGenerator()
        report_result = report_generator.generate_mining_analysis_report(
            report_data, format=format_type
        )
        
        return jsonify({
            'success': True,
            'report': report_result,
            'type': report_type,
            'format': format_type,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '生成报告失败'
        }), 500

@analytics_bp.route('/api/sla-metrics')
def get_sla_metrics():
    """获取SLA指标数据API"""
    try:
        months = int(request.args.get('months', 6))
        
        # 计算月份范围
        end_date = datetime.utcnow()
        start_month = int(end_date.strftime('%Y%m')) - months + 1
        
        sla_metrics = SLAMetrics.query.filter(
            SLAMetrics.month_year >= start_month
        ).order_by(SLAMetrics.month_year.desc()).all()
        
        data_list = []
        for metric in sla_metrics:
            data_list.append({
                'month_year': metric.month_year,
                'uptime_percentage': float(metric.uptime_percentage),
                'availability_percentage': float(metric.availability_percentage),
                'avg_response_time_ms': metric.avg_response_time_ms,
                'data_accuracy_percentage': float(metric.data_accuracy_percentage),
                'api_success_rate': float(metric.api_success_rate),
                'transparency_score': float(metric.transparency_score),
                'composite_sla_score': float(metric.composite_sla_score),
                'sla_status': metric.sla_status.value if metric.sla_status else None,
                'error_count': metric.error_count,
                'recorded_at': metric.recorded_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': data_list,
            'count': len(data_list)
        })
        
    except Exception as e:
        logger.error(f"获取SLA指标失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/price-analysis')
def price_analysis():
    """价格分析API"""
    try:
        days = int(request.args.get('days', 30))
        
        # 获取价格数据
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        price_data = db.session.query(
            NetworkSnapshot.recorded_at,
            NetworkSnapshot.btc_price
        ).filter(
            NetworkSnapshot.recorded_at >= start_date,
            NetworkSnapshot.is_valid == True
        ).order_by(NetworkSnapshot.recorded_at.asc()).all()
        
        if not price_data:
            return jsonify({
                'success': False,
                'error': '没有足够的价格数据进行分析'
            }), 404
        
        # 计算价格统计
        prices = [float(record.btc_price) for record in price_data]
        
        analysis = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'price_stats': {
                'current_price': prices[-1],
                'highest_price': max(prices),
                'lowest_price': min(prices),
                'average_price': sum(prices) / len(prices),
                'price_change': prices[-1] - prices[0],
                'price_change_percent': ((prices[-1] - prices[0]) / prices[0]) * 100,
                'volatility': calculate_volatility(prices)
            },
            'data_points': len(prices),
            'price_history': [
                {
                    'timestamp': record.recorded_at.isoformat(),
                    'price': float(record.btc_price)
                }
                for record in price_data
            ]
        }
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"价格分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def calculate_volatility(prices):
    """计算价格波动率"""
    if len(prices) < 2:
        return 0.0
    
    import statistics
    
    # 计算日收益率
    returns = []
    for i in range(1, len(prices)):
        daily_return = (prices[i] - prices[i-1]) / prices[i-1]
        returns.append(daily_return)
    
    # 计算年化波动率
    if len(returns) > 1:
        volatility = statistics.stdev(returns) * (365 ** 0.5)
        return round(volatility * 100, 2)  # 转换为百分比
    
    return 0.0