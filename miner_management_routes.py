"""
矿机管理路由模块
提供矿机信息的增删改查功能的API接口
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from auth import login_required
from models import MinerModel
from db import db
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

# 创建蓝图
miner_bp = Blueprint('miner_management', __name__, url_prefix='/admin/miners')

@miner_bp.route('/')
@login_required
def miner_list():
    """矿机列表页面"""
    miners = MinerModel.query.order_by(MinerModel.manufacturer, MinerModel.model_name).all()
    return render_template('admin/miner_list.html', miners=miners)

@miner_bp.route('/api/list')
def api_miner_list():
    """获取矿机列表 API"""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        if active_only:
            miners = MinerModel.get_active_miners()
        else:
            miners = MinerModel.query.order_by(MinerModel.manufacturer, MinerModel.model_name).all()
        
        return jsonify({
            'success': True,
            'miners': [miner.to_dict() for miner in miners],
            'count': len(miners)
        })
    except Exception as e:
        logger.error(f"获取矿机列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@miner_bp.route('/api/get/<int:miner_id>')
def api_get_miner(miner_id):
    """获取单个矿机信息 API"""
    try:
        miner = MinerModel.query.get_or_404(miner_id)
        return jsonify({
            'success': True,
            'miner': miner.to_dict()
        })
    except Exception as e:
        logger.error(f"获取矿机信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@miner_bp.route('/api/search')
def api_search_miners():
    """搜索矿机 API"""
    try:
        query = request.args.get('q', '').strip()
        manufacturer = request.args.get('manufacturer', '').strip()
        
        miners_query = MinerModel.query
        
        if query:
            miners_query = miners_query.filter(
                MinerModel.model_name.ilike(f'%{query}%')
            )
        
        if manufacturer:
            miners_query = miners_query.filter(
                MinerModel.manufacturer.ilike(f'%{manufacturer}%')
            )
        
        miners = miners_query.filter_by(is_active=True).order_by(
            MinerModel.manufacturer, MinerModel.model_name
        ).all()
        
        return jsonify({
            'success': True,
            'miners': [miner.to_dict() for miner in miners],
            'count': len(miners)
        })
    except Exception as e:
        logger.error(f"搜索矿机失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@miner_bp.route('/api/create', methods=['POST'])
@login_required
def api_create_miner():
    """创建新矿机 API"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['model_name', 'manufacturer', 'hashrate', 'power_consumption']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'缺少必填字段: {field}'}), 400
        
        # 检查是否已存在相同型号
        existing = MinerModel.query.filter_by(model_name=data['model_name']).first()
        if existing:
            return jsonify({'success': False, 'error': f'矿机型号 {data["model_name"]} 已存在'}), 400
        
        # 处理日期字段
        if 'release_date' in data and data['release_date']:
            try:
                data['release_date'] = datetime.strptime(data['release_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': '发布日期格式不正确，应为 YYYY-MM-DD'}), 400
        
        # 创建矿机
        miner = MinerModel(
            model_name=data['model_name'],
            manufacturer=data['manufacturer'],
            hashrate=float(data['hashrate']),
            power_consumption=int(data['power_consumption']),
            price_usd=float(data.get('price_usd', 0)) if data.get('price_usd') else None,
            is_liquid_cooled=data.get('is_liquid_cooled', False),
            chip_type=data.get('chip_type'),
            fan_count=int(data.get('fan_count', 0)) if data.get('fan_count') else None,
            operating_temp_min=int(data.get('operating_temp_min', 0)) if data.get('operating_temp_min') else None,
            operating_temp_max=int(data.get('operating_temp_max', 0)) if data.get('operating_temp_max') else None,
            noise_level=int(data.get('noise_level', 0)) if data.get('noise_level') else None,
            length_mm=float(data.get('length_mm', 0)) if data.get('length_mm') else None,
            width_mm=float(data.get('width_mm', 0)) if data.get('width_mm') else None,
            height_mm=float(data.get('height_mm', 0)) if data.get('height_mm') else None,
            weight_kg=float(data.get('weight_kg', 0)) if data.get('weight_kg') else None,
            release_date=data.get('release_date')
        )
        
        db.session.add(miner)
        db.session.commit()
        
        logger.info(f"成功创建矿机: {data['model_name']}")
        return jsonify({
            'success': True,
            'message': f'成功创建矿机 {data["model_name"]}',
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        logger.error(f"创建矿机失败: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@miner_bp.route('/api/update/<int:miner_id>', methods=['PUT'])
@login_required
def api_update_miner(miner_id):
    """更新矿机信息 API"""
    try:
        miner = MinerModel.query.get_or_404(miner_id)
        data = request.get_json()
        
        # 更新字段
        updatable_fields = [
            'model_name', 'manufacturer', 'hashrate', 'power_consumption',
            'price_usd', 'is_liquid_cooled', 'is_active', 'chip_type', 'fan_count',
            'operating_temp_min', 'operating_temp_max', 'noise_level',
            'length_mm', 'width_mm', 'height_mm', 'weight_kg'
        ]
        
        for field in updatable_fields:
            if field in data:
                if field in ['hashrate', 'price_usd', 'length_mm', 'width_mm', 'height_mm', 'weight_kg']:
                    setattr(miner, field, float(data[field]) if data[field] else None)
                elif field in ['power_consumption', 'fan_count', 'operating_temp_min', 'operating_temp_max', 'noise_level']:
                    setattr(miner, field, int(data[field]) if data[field] else None)
                elif field in ['is_liquid_cooled', 'is_active']:
                    setattr(miner, field, bool(data[field]))
                else:
                    setattr(miner, field, data[field])
        
        # 处理发布日期
        if 'release_date' in data and data['release_date']:
            try:
                miner.release_date = datetime.strptime(data['release_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': '发布日期格式不正确，应为 YYYY-MM-DD'}), 400
        
        # 重新计算能效比
        if miner.hashrate > 0:
            miner.efficiency = round(miner.power_consumption / miner.hashrate, 2)
        
        miner.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"成功更新矿机: {miner.model_name}")
        return jsonify({
            'success': True,
            'message': f'成功更新矿机 {miner.model_name}',
            'miner': miner.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新矿机失败: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@miner_bp.route('/api/delete/<int:miner_id>', methods=['DELETE'])
@login_required
def api_delete_miner(miner_id):
    """删除矿机 API（软删除）"""
    try:
        miner = MinerModel.query.get_or_404(miner_id)
        
        # 软删除 - 只是标记为不活跃
        miner.is_active = False
        miner.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"成功删除矿机: {miner.model_name}")
        return jsonify({
            'success': True,
            'message': f'成功删除矿机 {miner.model_name}'
        })
        
    except Exception as e:
        logger.error(f"删除矿机失败: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@miner_bp.route('/api/manufacturers')
def api_get_manufacturers():
    """获取制造商列表 API"""
    try:
        manufacturers = db.session.query(MinerModel.manufacturer).filter_by(is_active=True).distinct().all()
        manufacturer_list = [m[0] for m in manufacturers]
        
        return jsonify({
            'success': True,
            'manufacturers': manufacturer_list
        })
    except Exception as e:
        logger.error(f"获取制造商列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@miner_bp.route('/api/stats')
def api_get_stats():
    """获取矿机统计信息 API"""
    try:
        total_miners = MinerModel.query.count()
        active_miners = MinerModel.query.filter_by(is_active=True).count()
        manufacturers = db.session.query(MinerModel.manufacturer).filter_by(is_active=True).distinct().count()
        
        # 按制造商分组统计
        manufacturer_stats = db.session.query(
            MinerModel.manufacturer,
            db.func.count(MinerModel.id).label('count')
        ).filter_by(is_active=True).group_by(MinerModel.manufacturer).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_miners': total_miners,
                'active_miners': active_miners,
                'manufacturers': manufacturers,
                'manufacturer_stats': [{'manufacturer': m[0], 'count': m[1]} for m in manufacturer_stats]
            }
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500