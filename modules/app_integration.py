"""
将模块化架构集成到主应用
这个文件展示如何将新的模块架构与现有的app.py集成
"""
from flask import Flask, render_template, jsonify
from modules.config import register_modules, get_enabled_modules
import logging

logger = logging.getLogger(__name__)

def integrate_modules(app: Flask):
    """
    将模块系统集成到现有Flask应用
    
    Args:
        app: 现有的Flask应用实例
    """
    
    # 1. 注册所有模块
    logger.info("="*50)
    logger.info("开始集成模块化架构...")
    registered = register_modules(app)
    
    # 2. 创建模块导航页面
    @app.route('/modules')
    def modules_dashboard():
        """模块化系统仪表板"""
        modules = get_enabled_modules()
        return render_template('modules_dashboard.html', modules=modules)
    
    # 3. 提供模块状态API
    @app.route('/api/modules/status')
    def modules_status():
        """获取所有模块状态"""
        modules = get_enabled_modules()
        status = []
        
        for key, config in modules:
            status.append({
                'key': key,
                'name': config['name'],
                'url': config['url_prefix'],
                'requires_auth': config['requires_auth'],
                'enabled': config['enabled']
            })
        
        return jsonify({
            'success': True,
            'modules': status,
            'total': len(status)
        })
    
    # 4. 添加模块切换API（管理员功能）
    @app.route('/api/modules/toggle/<module_key>', methods=['POST'])
    def toggle_module(module_key):
        """启用或禁用模块（需要管理员权限）"""
        from flask_login import current_user, login_required
        
        # 这里应该添加管理员权限检查
        # if not current_user.is_authenticated or current_user.role != 'admin':
        #     return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        from modules.config import toggle_module as do_toggle
        from flask import request
        
        enabled = request.json.get('enabled', False)
        success = do_toggle(module_key, enabled)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'模块 {module_key} 已{"启用" if enabled else "禁用"}'
            })
        else:
            return jsonify({
                'success': False,
                'error': '模块不存在'
            }), 404
    
    logger.info(f"模块化架构集成完成，共注册 {len(registered)} 个模块")
    logger.info("="*50)
    
    return registered

def add_module_context_processor(app: Flask):
    """
    添加模块上下文处理器
    使所有模板都可以访问模块信息
    """
    @app.context_processor
    def inject_modules():
        from modules.config import get_enabled_modules, is_module_enabled
        
        return {
            'enabled_modules': get_enabled_modules(),
            'is_module_enabled': is_module_enabled
        }

def migrate_existing_routes(app: Flask):
    """
    迁移现有路由到模块化架构的示例
    展示如何逐步将现有功能迁移到模块中
    """
    
    # 示例：将现有的计算器路由迁移到模块
    # 1. 保留原有路由作为重定向
    @app.route('/mining-calculator')
    def redirect_to_calculator():
        from flask import redirect, url_for
        return redirect(url_for('calculator.index'))
    
    @app.route('/batch-calculator')
    def redirect_to_batch():
        from flask import redirect, url_for
        return redirect(url_for('batch.index'))
    
    logger.info("现有路由迁移配置完成")

# 使用示例：在主app.py中调用
# from modules.app_integration import integrate_modules, add_module_context_processor
# integrate_modules(app)
# add_module_context_processor(app)