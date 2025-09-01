
"""
托管功能路由
包含托管商和客户视角的所有功能
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash
from . import hosting_bp
from auth import login_required
from decorators import requires_role
import logging

logger = logging.getLogger(__name__)

@hosting_bp.route('/')
@login_required
def dashboard():
    """托管功能主仪表板"""
    user_role = session.get('role', 'guest')
    
    if user_role in ['owner', 'admin', 'mining_site']:
        # 托管商视角
        return render_template('hosting/host_dashboard.html')
    else:
        # 客户视角
        return render_template('hosting/client_dashboard.html')

@hosting_bp.route('/host')
@hosting_bp.route('/host/<path:subpath>')
@requires_role(['owner', 'admin', 'mining_site'])
def host_view(subpath='dashboard'):
    """托管商视角路由"""
    try:
        if subpath == 'dashboard':
            return render_template('hosting/host_dashboard.html')
        elif subpath == 'sites':
            return render_template('hosting/site_management.html')
        elif subpath == 'devices':
            return render_template('hosting/device_management.html')
        elif subpath == 'monitoring':
            return render_template('hosting/event_monitoring.html')
        elif subpath == 'sla':
            return render_template('hosting/sla_management.html')
        else:
            return render_template('hosting/host_dashboard.html')
    except Exception as e:
        logger.error(f"托管商视图错误: {e}")
        flash('页面加载失败', 'error')
        return redirect(url_for('hosting.dashboard'))

@hosting_bp.route('/client')
@hosting_bp.route('/client/<path:subpath>')
@login_required
def client_view(subpath='dashboard'):
    """客户视角路由"""
    try:
        if subpath == 'dashboard':
            return render_template('hosting/client_dashboard.html')
        elif subpath == 'assets':
            return render_template('hosting/asset_overview.html')
        elif subpath == 'billing':
            return render_template('hosting/billing_view.html')
        elif subpath == 'reports':
            return render_template('hosting/client_reports.html')
        else:
            return render_template('hosting/client_dashboard.html')
    except Exception as e:
        logger.error(f"客户视图错误: {e}")
        flash('页面加载失败', 'error')
        return redirect(url_for('hosting.dashboard'))

@hosting_bp.route('/api/sites', methods=['GET'])
@requires_role(['owner', 'admin', 'mining_site'])
def get_sites():
    """获取托管站点列表"""
    try:
        # 这里可以从数据库获取站点数据
        # 暂时返回示例数据
        sites = [
            {
                'id': 1,
                'name': '北京数据中心',
                'location': '北京市朝阳区',
                'capacity_mw': 50.0,
                'used_capacity_mw': 35.2,
                'status': 'online',
                'devices_count': 1200
            },
            {
                'id': 2,
                'name': '四川矿场',
                'location': '四川省阿坝州',
                'capacity_mw': 100.0,
                'used_capacity_mw': 78.5,
                'status': 'online',
                'devices_count': 2800
            }
        ]
        return jsonify({'success': True, 'sites': sites})
    except Exception as e:
        logger.error(f"获取站点列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@hosting_bp.route('/api/client/assets', methods=['GET'])
@login_required
def get_client_assets():
    """获取客户资产概览"""
    try:
        user_id = session.get('user_id')
        # 这里应该从数据库获取客户的实际资产数据
        assets = {
            'total_devices': 45,
            'active_devices': 42,
            'total_hashrate': '10.5 PH/s',
            'monthly_revenue': 15420.50,
            'monthly_cost': 8900.00,
            'net_profit': 6520.50
        }
        return jsonify({'success': True, 'assets': assets})
    except Exception as e:
        logger.error(f"获取客户资产失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
