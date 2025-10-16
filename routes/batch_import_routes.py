"""
HashInsight Enterprise - Batch Import Routes
批量导入路由
"""

import logging
from flask import Blueprint, request, jsonify, render_template, session, send_file
from werkzeug.utils import secure_filename
import io
from datetime import datetime

from auth import login_required
from batch.batch_import_manager import BatchImportManager
from batch.csv_template_generator import CSVTemplateGenerator

logger = logging.getLogger(__name__)

# 创建蓝图
batch_import_bp = Blueprint('batch_import', __name__, url_prefix='/batch')


@batch_import_bp.route('/import')
@login_required
def import_page():
    """批量导入页面"""
    return render_template('batch/import.html')


@batch_import_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_csv():
    """
    上传CSV文件进行批量导入
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if not file or not file.filename or file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({
                'success': False,
                'error': 'Only CSV files are allowed'
            }), 400
        
        # 读取文件内容
        csv_content = file.read().decode('utf-8')
        filename = secure_filename(file.filename)
        
        # 创建导入管理器
        import_manager = BatchImportManager(user_id=int(user_id))
        
        # 执行导入
        result = import_manager.import_csv(csv_content, filename)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@batch_import_bp.route('/api/template/download')
@login_required
def download_template():
    """
    下载CSV模板
    """
    try:
        language = request.args.get('lang', 'en')
        include_examples = request.args.get('examples', 'true').lower() == 'true'
        
        # 生成模板
        template_content = CSVTemplateGenerator.generate_template(
            language=language,
            include_examples=include_examples
        )
        
        # 创建响应
        output = io.BytesIO(template_content.encode('utf-8-sig'))  # BOM for Excel compatibility
        output.seek(0)
        
        filename = f'miner_import_template_{language}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Template download failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@batch_import_bp.route('/api/template/bulk')
@login_required
def download_bulk_template():
    """
    下载大批量测试模板（用于性能测试）
    """
    try:
        count = int(request.args.get('count', 5000))
        language = request.args.get('lang', 'en')
        
        # 限制最大数量
        count = min(count, 10000)
        
        # 生成模板
        template_content = CSVTemplateGenerator.generate_bulk_template(
            count=count,
            language=language
        )
        
        output = io.BytesIO(template_content.encode('utf-8-sig'))
        output.seek(0)
        
        filename = f'miner_bulk_template_{count}_rows.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Bulk template download failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@batch_import_bp.route('/api/validation-rules')
@login_required
def get_validation_rules():
    """
    获取数据验证规则
    """
    try:
        language = request.args.get('lang', 'en')
        rules = CSVTemplateGenerator.generate_validation_rules(language)
        
        return jsonify({
            'success': True,
            'rules': rules
        })
        
    except Exception as e:
        logger.error(f"Failed to get validation rules: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
