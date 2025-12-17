"""
HashInsight CDC Platform - Miners API Blueprint
矿机管理API，实现Transactional Outbox模式
"""
import os
import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.infra.database import db
from core.infra.outbox import OutboxPublisher
from core.infra.audit import AuditLogger
from core.infra.auth import jwt_required, rate_limit

logger = logging.getLogger(__name__)

# 创建Blueprint
bp = Blueprint('miners', __name__)

# 初始化Outbox服务（不需要应用上下文）
outbox = OutboxPublisher(db)

# ==================== POST /api/miners ====================

@bp.route('/miners', methods=['POST'])
@jwt_required(scopes=['miners:write', 'admin'])
@rate_limit(limit_per_minute=30)
def create_miner():
    """
    新增矿机
    
    功能：
    1. 在事务内创建矿机记录
    2. 写入event_outbox表（miner.added事件）
    3. 写入audit_logs审计日志
    4. 事务提交后，Debezium CDC自动捕获并发布到Kafka
    
    curl示例:
    ```bash
    curl -X POST https://api.hashinsight.io/api/miners \
      -H "Authorization: Bearer YOUR_JWT_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "model": "Antminer S19 Pro",
        "hashrate": 110.0,
        "power_consumption": 3250,
        "location": "datacenter-1",
        "owner_id": "user123",
        "purchase_price": 5000.00,
        "status": "online"
      }'
    ```
    
    响应示例:
    ```json
    {
      "success": true,
      "miner_id": "miner_abc123",
      "event_id": "evt_xyz456",
      "message": "Miner created successfully"
    }
    ```
    """
    try:
        # 解析请求数据
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # 验证必填字段
        required_fields = ['model', 'hashrate', 'power_consumption', 'owner_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # 生成矿机ID
        miner_id = f"miner_{datetime.utcnow().timestamp()}"
        
        # 开始事务
        # 1. 插入矿机记录（假设miners表存在）
        insert_sql = text("""
            INSERT INTO miners (
                id, model, hashrate, power_consumption, location, 
                owner_id, purchase_price, status, tenant_id, created_at
            )
            VALUES (
                :id, :model, :hashrate, :power_consumption, :location,
                :owner_id, :purchase_price, :status, :tenant_id, :created_at
            )
        """)
        
        db.session.execute(insert_sql, {
            'id': miner_id,
            'model': data['model'],
            'hashrate': data['hashrate'],
            'power_consumption': data['power_consumption'],
            'location': data.get('location', 'unknown'),
            'owner_id': data['owner_id'],
            'purchase_price': data.get('purchase_price', 0.0),
            'status': data.get('status', 'pending'),
            'tenant_id': g.tenant_id,
            'created_at': datetime.utcnow()
        })
        
        # 2. 写入Outbox事件（在同一事务内）
        event_id = outbox.publish(
            kind='miner.added',
            user_id=g.user_id,
            payload={
                'miner_id': miner_id,
                'model': data['model'],
                'hashrate': data['hashrate'],
                'owner_id': data['owner_id'],
                'created_by': g.user_id
            },
            entity_id=miner_id,
            tenant_id=g.tenant_id,
            idempotency_key=f"add_miner_{g.user_id}_{miner_id}"
        )
        
        # 3. 写入审计日志（在同一事务内）
        audit = AuditLogger(db)
        audit.log(
            user_id=g.user_id,
            action='create',
            resource_type='miner',
            resource_id=miner_id,
            details={
                'model': data['model'],
                'hashrate': data['hashrate'],
                'event_id': event_id
            },
            tenant_id=g.tenant_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # 提交事务
        db.session.commit()
        
        logger.info(f"✅ Miner created: {miner_id}, event: {event_id}")
        
        return jsonify({
            'success': True,
            'miner_id': miner_id,
            'event_id': event_id,
            'message': 'Miner created successfully'
        }), 201
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"❌ Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== PATCH /api/miners/:id/status ====================

@bp.route('/miners/<miner_id>/status', methods=['PATCH'])
@jwt_required(scopes=['miners:write', 'admin'])
@rate_limit(limit_per_minute=60)
def update_miner_status(miner_id):
    """
    更新矿机状态
    
    功能：
    1. 更新矿机状态（online/offline/maintenance）
    2. 写入event_outbox（miner.status_changed事件）
    3. 记录审计日志
    
    curl示例:
    ```bash
    curl -X PATCH https://api.hashinsight.io/api/miners/miner_123/status \
      -H "Authorization: Bearer YOUR_JWT_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "status": "maintenance",
        "reason": "Scheduled maintenance"
      }'
    ```
    
    响应示例:
    ```json
    {
      "success": true,
      "miner_id": "miner_123",
      "old_status": "online",
      "new_status": "maintenance",
      "event_id": "evt_xyz789"
    }
    ```
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Status field is required'}), 400
        
        new_status = data['status']
        reason = data.get('reason', 'Status update')
        
        # 验证状态值
        valid_statuses = ['online', 'offline', 'maintenance', 'pending', 'decommissioned']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
        
        # 获取当前状态
        select_sql = text("""
            SELECT status FROM miners 
            WHERE id = :miner_id AND tenant_id = :tenant_id
        """)
        result = db.session.execute(select_sql, {
            'miner_id': miner_id,
            'tenant_id': g.tenant_id
        }).first()
        
        if not result:
            return jsonify({'error': 'Miner not found'}), 404
        
        old_status = result[0]
        
        # 更新状态
        update_sql = text("""
            UPDATE miners 
            SET status = :status, updated_at = :updated_at
            WHERE id = :miner_id AND tenant_id = :tenant_id
        """)
        db.session.execute(update_sql, {
            'status': new_status,
            'updated_at': datetime.utcnow(),
            'miner_id': miner_id,
            'tenant_id': g.tenant_id
        })
        
        # 写入Outbox事件
        event_id = outbox.publish(
            kind='miner.status_changed',
            user_id=g.user_id,
            payload={
                'miner_id': miner_id,
                'old_status': old_status,
                'new_status': new_status,
                'reason': reason,
                'changed_by': g.user_id
            },
            entity_id=miner_id,
            tenant_id=g.tenant_id,
            idempotency_key=f"status_{miner_id}_{new_status}_{datetime.utcnow().timestamp()}"
        )
        
        # 审计日志
        audit = AuditLogger(db)
        audit.log(
            user_id=g.user_id,
            action='update',
            resource_type='miner',
            resource_id=miner_id,
            details={
                'old_status': old_status,
                'new_status': new_status,
                'reason': reason,
                'event_id': event_id
            },
            tenant_id=g.tenant_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        logger.info(f"✅ Miner status updated: {miner_id} {old_status}->{new_status}")
        
        return jsonify({
            'success': True,
            'miner_id': miner_id,
            'old_status': old_status,
            'new_status': new_status,
            'event_id': event_id
        }), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"❌ Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== POST /api/miners/bulk ====================

@bp.route('/miners/bulk', methods=['POST'])
@jwt_required(scopes=['miners:write', 'admin'])
@rate_limit(limit_per_minute=10)
def bulk_import_miners():
    """
    批量导入矿机
    
    功能：
    1. 批量插入矿机记录
    2. 写入单个聚合事件（miner.bulk_imported）
    3. 记录批量操作审计日志
    
    curl示例:
    ```bash
    curl -X POST https://api.hashinsight.io/api/miners/bulk \
      -H "Authorization: Bearer YOUR_JWT_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "miners": [
          {
            "model": "Antminer S19 Pro",
            "hashrate": 110.0,
            "power_consumption": 3250,
            "owner_id": "user123"
          },
          {
            "model": "Whatsminer M30S++",
            "hashrate": 112.0,
            "power_consumption": 3400,
            "owner_id": "user123"
          }
        ],
        "batch_id": "batch_20250108_001"
      }'
    ```
    
    响应示例:
    ```json
    {
      "success": true,
      "batch_id": "batch_20250108_001",
      "imported_count": 2,
      "failed_count": 0,
      "event_id": "evt_bulk_123",
      "miner_ids": ["miner_1", "miner_2"]
    }
    ```
    """
    try:
        data = request.get_json()
        
        if not data or 'miners' not in data:
            return jsonify({'error': 'Miners array is required'}), 400
        
        miners = data['miners']
        batch_id = data.get('batch_id', f"batch_{datetime.utcnow().timestamp()}")
        
        if not isinstance(miners, list) or len(miners) == 0:
            return jsonify({'error': 'Miners must be a non-empty array'}), 400
        
        # 批量导入限制
        if len(miners) > 1000:
            return jsonify({'error': 'Maximum 1000 miners per batch'}), 400
        
        imported_ids = []
        failed_count = 0
        
        # 批量插入
        for idx, miner_data in enumerate(miners):
            try:
                miner_id = f"miner_{batch_id}_{idx}"
                
                insert_sql = text("""
                    INSERT INTO miners (
                        id, model, hashrate, power_consumption, location,
                        owner_id, purchase_price, status, tenant_id, created_at
                    )
                    VALUES (
                        :id, :model, :hashrate, :power_consumption, :location,
                        :owner_id, :purchase_price, :status, :tenant_id, :created_at
                    )
                """)
                
                db.session.execute(insert_sql, {
                    'id': miner_id,
                    'model': miner_data.get('model', 'Unknown'),
                    'hashrate': miner_data.get('hashrate', 0),
                    'power_consumption': miner_data.get('power_consumption', 0),
                    'location': miner_data.get('location', 'unknown'),
                    'owner_id': miner_data.get('owner_id', g.user_id),
                    'purchase_price': miner_data.get('purchase_price', 0.0),
                    'status': miner_data.get('status', 'pending'),
                    'tenant_id': g.tenant_id,
                    'created_at': datetime.utcnow()
                })
                
                imported_ids.append(miner_id)
            
            except Exception as e:
                logger.warning(f"⚠️ Failed to import miner {idx}: {e}")
                failed_count += 1
        
        # 写入单个聚合事件（而不是为每个矿机写一个事件）
        event_id = outbox.publish(
            kind='miner.bulk_imported',
            user_id=g.user_id,
            payload={
                'batch_id': batch_id,
                'total_count': len(miners),
                'imported_count': len(imported_ids),
                'failed_count': failed_count,
                'miner_ids': imported_ids,
                'imported_by': g.user_id
            },
            entity_id=batch_id,
            tenant_id=g.tenant_id,
            idempotency_key=f"bulk_import_{batch_id}"
        )
        
        # 审计日志
        audit = AuditLogger(db)
        audit.log(
            user_id=g.user_id,
            action='bulk_create',
            resource_type='miner',
            resource_id=batch_id,
            details={
                'total_count': len(miners),
                'imported_count': len(imported_ids),
                'failed_count': failed_count,
                'event_id': event_id
            },
            tenant_id=g.tenant_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        logger.info(f"✅ Bulk import completed: {len(imported_ids)}/{len(miners)} miners")
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'imported_count': len(imported_ids),
            'failed_count': failed_count,
            'event_id': event_id,
            'miner_ids': imported_ids
        }), 201
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"❌ Bulk import database error: {e}")
        return jsonify({'error': 'Database error during bulk import'}), 500
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Bulk import error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
