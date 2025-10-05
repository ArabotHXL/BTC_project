"""
矿机批量导入路由模块
Miner Batch Import Routes Module

提供矿机批量导入、查询和管理的API接口
"""

import logging
import os
import re
import uuid
import pandas as pd
import io
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, session, send_file
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_

from auth import login_required
from db import db
from models import Miner, MinerImportJob, User
from translations import get_translation

logger = logging.getLogger(__name__)

# 创建蓝图
miner_import_bp = Blueprint('miner_import', __name__, url_prefix='/api/miners')


# IP地址验证正则表达式（IPv4）
IPV4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)


def validate_ip_address(ip):
    """验证IP地址格式"""
    if not ip:
        return False
    return IPV4_PATTERN.match(str(ip).strip()) is not None


def get_current_user_id():
    """获取当前登录用户ID"""
    user_id = session.get('user_id')
    if not user_id:
        email = session.get('email')
        if email:
            user = User.query.filter_by(email=email).first()
            if user:
                user_id = user.id
                session['user_id'] = user_id
    return user_id


def get_translation_safe(key, lang='en'):
    """安全地获取翻译，如果失败则返回key"""
    try:
        return get_translation(key, lang)
    except:
        return key


@miner_import_bp.route('/page')
@login_required
def import_page():
    """矿机导入页面"""
    return render_template('miner_import.html')


@miner_import_bp.route('/template.csv')
@login_required
def download_template():
    """
    下载CSV模板
    GET /api/miners/template.csv?mode=with_example 或 header_only
    """
    try:
        mode = request.args.get('mode', 'with_example')
        lang = session.get('lang', 'en')
        
        # CSV header
        headers = ['miner_id', 'model', 'ip', 'port', 'api', 'username', 'password', 'note']
        
        # 创建CSV内容
        csv_lines = [','.join(headers)]
        
        # 如果需要示例数据
        if mode == 'with_example':
            examples = [
                ['S21-192.168.1.45', 'Antminer S21', '192.168.1.45', '4028', 'bmminer', '', '', 'rack A-03'],
                ['M50-192.168.1.55', 'Whatsminer M50', '192.168.1.55', '22333', 'http', '', '', 'rack B-02'],
            ]
            for example in examples:
                csv_lines.append(','.join(example))
        
        csv_content = '\n'.join(csv_lines)
        
        # 创建响应
        output = io.BytesIO(csv_content.encode('utf-8-sig'))  # BOM for Excel compatibility
        output.seek(0)
        
        filename = f'miner_import_template_{mode}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Template download failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to download template',
            'message_zh': '模板下载失败',
            'error': str(e)
        }), 500


@miner_import_bp.route('/import', methods=['POST'])
@login_required
def import_miners():
    """
    批量导入矿机
    POST /api/miners/import
    
    表单参数：
    - file: CSV/Excel文件
    - siteId: 站点ID（必填）
    - dedupStrategy: 去重策略（prefer_import/prefer_existing/reject_conflict）
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message_en': 'User not authenticated',
                'message_zh': '用户未认证'
            }), 401
        
        # 获取站点ID
        site_id = request.form.get('siteId')
        if not site_id:
            return jsonify({
                'success': False,
                'message_en': 'Site ID is required',
                'message_zh': '站点ID必填'
            }), 400
        
        # 获取去重策略
        dedup_strategy = request.form.get('dedupStrategy', 'prefer_import')
        valid_strategies = ['prefer_import', 'prefer_existing', 'reject_conflict']
        if dedup_strategy not in valid_strategies:
            dedup_strategy = 'prefer_import'
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message_en': 'No file uploaded',
                'message_zh': '未上传文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message_en': 'No file selected',
                'message_zh': '未选择文件'
            }), 400
        
        # 获取文件扩展名
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        # 解析文件
        try:
            if file_ext == '.csv':
                df = pd.read_csv(file, encoding='utf-8-sig')
                file_type = 'csv'
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file)
                file_type = 'excel'
            else:
                return jsonify({
                    'success': False,
                    'message_en': 'Only CSV and Excel files are supported',
                    'message_zh': '仅支持CSV和Excel文件'
                }), 400
        except Exception as e:
            logger.error(f"Failed to parse file: {e}")
            return jsonify({
                'success': False,
                'message_en': f'Failed to parse file: {str(e)}',
                'message_zh': f'文件解析失败: {str(e)}'
            }), 400
        
        # 创建导入任务记录
        job_id = f"import_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        import_job = MinerImportJob(
            job_id=job_id,
            site_id=site_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            dedup_strategy=dedup_strategy,
            total_rows=len(df),
            status='processing'
        )
        db.session.add(import_job)
        db.session.commit()
        
        # 处理数据
        valid_rows = []
        invalid_rows = []
        
        required_columns = ['miner_id', 'ip']
        
        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel行号（从2开始，因为有header）
            errors = []
            
            # 检查必填字段
            if pd.isna(row.get('miner_id')) or str(row.get('miner_id')).strip() == '':
                errors.append('miner_id is required')
            if pd.isna(row.get('ip')) or str(row.get('ip')).strip() == '':
                errors.append('ip is required')
            
            # IP地址格式验证
            if not pd.isna(row.get('ip')):
                ip = str(row.get('ip')).strip()
                if not validate_ip_address(ip):
                    errors.append(f'Invalid IP address format: {ip}')
            
            if errors:
                invalid_rows.append({
                    'row_number': row_num,
                    'data': row.to_dict(),
                    'errors': '; '.join(errors)
                })
            else:
                valid_rows.append(row)
        
        # 去重和插入/更新逻辑
        inserted_count = 0
        updated_count = 0
        dedup_count = 0
        
        for row in valid_rows:
            miner_id = str(row.get('miner_id')).strip()
            ip = str(row.get('ip')).strip()
            
            # 查找现有记录（基于 site_id + ip + miner_id 去重）
            existing_miner = Miner.query.filter_by(
                site_id=site_id,
                ip=ip,
                miner_id=miner_id
            ).first()
            
            # 准备数据
            miner_data = {
                'miner_id': miner_id,
                'site_id': site_id,
                'ip': ip,
                'model': str(row.get('model', '')).strip() if not pd.isna(row.get('model')) else None,
                'port': str(row.get('port', '')).strip() if not pd.isna(row.get('port')) else None,
                'api': str(row.get('api', '')).strip() if not pd.isna(row.get('api')) else None,
                'username': str(row.get('username', '')).strip() if not pd.isna(row.get('username')) else None,
                'password': str(row.get('password', '')).strip() if not pd.isna(row.get('password')) else None,
                'note': str(row.get('note', '')).strip() if not pd.isna(row.get('note')) else None,
                'source': 'import',
                'status': 'active'
            }
            
            if existing_miner:
                # 根据去重策略处理
                if dedup_strategy == 'prefer_import':
                    # 更新现有记录
                    for key, value in miner_data.items():
                        if key not in ['miner_id', 'site_id', 'ip']:  # 不更新主键
                            setattr(existing_miner, key, value)
                    existing_miner.updated_at = datetime.utcnow()
                    updated_count += 1
                elif dedup_strategy == 'prefer_existing':
                    # 保留现有数据，跳过
                    dedup_count += 1
                    continue
                elif dedup_strategy == 'reject_conflict':
                    # 拒绝冲突，记录到错误
                    invalid_rows.append({
                        'row_number': valid_rows.index(row) + 2,
                        'data': row.to_dict(),
                        'errors': f'Duplicate miner: {miner_id} at {ip}'
                    })
                    dedup_count += 1
                    continue
            else:
                # 新建记录
                new_miner = Miner(**miner_data, user_id=user_id)
                db.session.add(new_miner)
                inserted_count += 1
        
        # 生成错误CSV（如果有错误）
        error_csv_path = None
        if invalid_rows:
            error_csv_filename = f'import_errors_{job_id}.csv'
            error_csv_path = os.path.join('/tmp', error_csv_filename)
            
            # 创建错误DataFrame
            error_data = []
            for err_row in invalid_rows:
                row_data = err_row['data'].copy()
                row_data['_row_number'] = err_row['row_number']
                row_data['_errors'] = err_row['errors']
                error_data.append(row_data)
            
            error_df = pd.DataFrame(error_data)
            error_df.to_csv(error_csv_path, index=False, encoding='utf-8-sig')
        
        # 更新导入任务记录
        import_job.parsed_rows = len(valid_rows)
        import_job.invalid_rows = len(invalid_rows)
        import_job.inserted = inserted_count
        import_job.updated = updated_count
        import_job.deduped = dedup_count
        import_job.error_csv_path = error_csv_path
        import_job.status = 'completed'
        import_job.completed_at = datetime.utcnow()
        
        # 提交数据库更改
        db.session.commit()
        
        # 获取预览数据（最多5条）
        preview_miners = Miner.query.filter_by(site_id=site_id).order_by(
            Miner.created_at.desc()
        ).limit(5).all()
        
        preview_data = [m.to_dict() for m in preview_miners]
        
        # 返回结果
        return jsonify({
            'success': True,
            'message_en': f'Import completed: {inserted_count} inserted, {updated_count} updated, {len(invalid_rows)} errors',
            'message_zh': f'导入完成：{inserted_count}条新增，{updated_count}条更新，{len(invalid_rows)}条错误',
            'job_id': job_id,
            'statistics': {
                'total_rows': len(df),
                'valid_rows': len(valid_rows),
                'invalid_rows': len(invalid_rows),
                'inserted': inserted_count,
                'updated': updated_count,
                'deduped': dedup_count
            },
            'preview': preview_data,
            'error_csv_url': f'/api/miners/import/errors.csv?jobId={job_id}' if invalid_rows else None
        })
        
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        db.session.rollback()
        
        # 更新任务状态为失败
        if 'import_job' in locals():
            import_job.status = 'failed'
            db.session.commit()
        
        return jsonify({
            'success': False,
            'message_en': f'Import failed: {str(e)}',
            'message_zh': f'导入失败: {str(e)}',
            'error': str(e)
        }), 500


@miner_import_bp.route('/import/errors.csv')
@login_required
def download_error_csv():
    """
    下载错误报告CSV
    GET /api/miners/import/errors.csv?jobId=xxx
    """
    try:
        job_id = request.args.get('jobId')
        if not job_id:
            return jsonify({
                'success': False,
                'message_en': 'Job ID is required',
                'message_zh': '任务ID必填'
            }), 400
        
        # 查找导入任务
        import_job = MinerImportJob.query.filter_by(job_id=job_id).first()
        if not import_job:
            return jsonify({
                'success': False,
                'message_en': 'Import job not found',
                'message_zh': '导入任务未找到'
            }), 404
        
        # 检查错误CSV文件
        if not import_job.error_csv_path or not os.path.exists(import_job.error_csv_path):
            return jsonify({
                'success': False,
                'message_en': 'Error CSV file not found',
                'message_zh': '错误CSV文件未找到'
            }), 404
        
        # 返回文件
        return send_file(
            import_job.error_csv_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'import_errors_{job_id}.csv'
        )
        
    except Exception as e:
        logger.error(f"Error CSV download failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to download error CSV',
            'message_zh': '错误CSV下载失败',
            'error': str(e)
        }), 500


@miner_import_bp.route('')
@login_required
def query_miners():
    """
    查询矿机列表（分页）
    GET /api/miners?siteId=xxx&page=1&pageSize=50
    """
    try:
        site_id = request.args.get('siteId')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 50))
        
        # 限制每页最大数量
        page_size = min(page_size, 200)
        
        # 构建查询
        query = Miner.query
        
        if site_id:
            query = query.filter_by(site_id=site_id)
        
        # 分页
        pagination = query.order_by(Miner.created_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )
        
        miners = [m.to_dict() for m in pagination.items]
        
        return jsonify({
            'success': True,
            'data': miners,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Query miners failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message_en': 'Failed to query miners',
            'message_zh': '查询矿机失败',
            'error': str(e)
        }), 500


@miner_import_bp.route('/link', methods=['POST'])
@login_required
def link_miner_to_site():
    """
    关联矿机到站点
    POST /api/miners/link
    
    JSON参数：
    {
        "minerId": "xxx",
        "siteId": "xxx"
    }
    """
    try:
        data = request.get_json()
        miner_id = data.get('minerId')
        site_id = data.get('siteId')
        
        if not miner_id or not site_id:
            return jsonify({
                'success': False,
                'message_en': 'Miner ID and Site ID are required',
                'message_zh': '矿机ID和站点ID必填'
            }), 400
        
        # 查找矿机
        miner = Miner.query.filter_by(miner_id=miner_id).first()
        if not miner:
            return jsonify({
                'success': False,
                'message_en': 'Miner not found',
                'message_zh': '矿机未找到'
            }), 404
        
        # 更新站点ID
        miner.site_id = site_id
        miner.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_en': 'Miner linked to site successfully',
            'message_zh': '矿机关联站点成功',
            'data': miner.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Link miner to site failed: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message_en': 'Failed to link miner to site',
            'message_zh': '关联矿机到站点失败',
            'error': str(e)
        }), 500
