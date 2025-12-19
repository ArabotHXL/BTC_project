"""
Monitor Routes - Site Telemetry Monitoring UI
监控路由 - 站点遥测监控界面
"""

from flask import Blueprint, render_template
from models import db

monitor_bp = Blueprint('monitor', __name__, url_prefix='/monitor')


@monitor_bp.route('/<int:site_id>')
def site_monitor(site_id):
    """
    Site monitor page with Bootstrap table and Chart.js
    站点监控页面，包含矿机列表和历史图表
    """
    from models import HostingSite
    
    site = HostingSite.query.get(site_id)
    
    return render_template(
        'monitor/site_monitor.html',
        site_id=site_id,
        site=site
    )
