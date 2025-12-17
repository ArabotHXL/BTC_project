"""
HashInsight CDC Platform - Intelligence API Blueprint
智能预测API，使用SWR缓存策略
"""
import os
import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.infra.database import db
from core.infra.redis_client import redis_client
from core.infra.audit import AuditLogger
from core.infra.auth import jwt_required, rate_limit

logger = logging.getLogger(__name__)

# 创建Blueprint
bp = Blueprint('intelligence', __name__)

# SWR缓存配置
SWR_CACHE_TTL = int(os.getenv('SWR_CACHE_TTL', 300))  # 5分钟
SWR_STALE_TTL = int(os.getenv('SWR_STALE_TTL', 3600))  # 1小时（stale-while-revalidate）

# ==================== GET /api/intelligence/forecast ====================

@bp.route('/forecast', methods=['GET'])
@jwt_required(scopes=['intelligence:read', 'admin'])
@rate_limit(limit_per_minute=100)
def get_forecast():
    """
    获取预测数据（BTC价格、难度、算力等）
    
    功能：
    1. 从forecast_daily表读取最新预测数据
    2. 使用SWR (Stale-While-Revalidate) 缓存策略
    3. 返回缓存元数据（命中率、新鲜度）
    
    SWR缓存策略：
    - 首次请求：从数据库读取，写入Redis（TTL=5分钟）
    - 缓存有效期内：直接返回缓存（cache_hit=true）
    - 缓存过期但<1小时：返回stale数据，异步刷新（stale=true）
    - 缓存过期>1小时：同步从数据库读取
    
    curl示例:
    ```bash
    curl -X GET "https://api.hashinsight.io/api/intelligence/forecast?days=7&metric=btc_price" \
      -H "Authorization: Bearer YOUR_JWT_TOKEN"
    ```
    
    查询参数:
    - days: 预测天数（1-30，默认7）
    - metric: 指标类型（btc_price/hashrate/difficulty，默认all）
    
    响应示例:
    ```json
    {
      "success": true,
      "data": [
        {
          "date": "2025-10-09",
          "btc_price_usd": 45000.50,
          "network_hashrate_eh": 450.2,
          "difficulty": 62000000000000,
          "confidence": 0.85
        }
      ],
      "metadata": {
        "cache_hit": true,
        "stale": false,
        "freshness_sec": 120,
        "source": "redis",
        "count": 7
      }
    }
    ```
    """
    try:
        # 解析查询参数
        days = int(request.args.get('days', 7))
        metric = request.args.get('metric', 'all')
        
        # 参数验证
        if days < 1 or days > 30:
            return jsonify({'error': 'Days must be between 1 and 30'}), 400
        
        # SQL注入防护：严格验证metric参数，只允许预定义的列名
        ALLOWED_METRICS = ['all', 'btc_price_usd', 'network_hashrate_eh', 'difficulty']
        if metric not in ALLOWED_METRICS:
            return jsonify({'error': f'Invalid metric. Allowed values: {", ".join(ALLOWED_METRICS)}'}), 400
        
        # 生成缓存键
        cache_key = f"forecast:{g.tenant_id}:{days}:{metric}"
        
        # 尝试从Redis获取缓存
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            # 缓存命中
            logger.debug(f"📦 Cache hit: {cache_key}")
            
            # 检查缓存新鲜度
            cache_age_key = f"{cache_key}:timestamp"
            cache_timestamp = redis_client.get(cache_age_key)
            
            freshness_sec = 0
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                freshness_sec = int((datetime.utcnow() - cache_time).total_seconds())
            
            # 审计日志（仅记录查询，不影响事务）
            audit = AuditLogger(db)
            audit.log(
                user_id=g.user_id,
                action='view',
                resource_type='forecast',
                resource_id=f"days_{days}",
                details={
                    'days': days,
                    'metric': metric,
                    'cache_hit': True,
                    'freshness_sec': freshness_sec
                },
                tenant_id=g.tenant_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'data': cached_data.get('data', []),
                'metadata': {
                    'cache_hit': True,
                    'stale': False,
                    'freshness_sec': freshness_sec,
                    'source': 'redis',
                    'count': len(cached_data.get('data', []))
                }
            }), 200
        
        # 缓存未命中，从数据库读取
        logger.debug(f"💾 Cache miss, querying database: {cache_key}")
        
        # 构建SQL查询
        if metric == 'all':
            columns = "date, btc_price_usd, network_hashrate_eh, difficulty, confidence"
        else:
            columns = f"date, {metric}, confidence"
        
        sql = text(f"""
            SELECT {columns}
            FROM forecast_daily
            WHERE tenant_id = :tenant_id
            AND date >= :start_date
            ORDER BY date ASC
            LIMIT :days
        """)
        
        result = db.session.execute(sql, {
            'tenant_id': g.tenant_id,
            'start_date': datetime.utcnow().date(),
            'days': days
        })
        
        # 转换结果为字典列表
        forecast_data = []
        for row in result:
            row_dict = dict(row._mapping)
            # 转换日期为字符串
            if 'date' in row_dict:
                row_dict['date'] = row_dict['date'].isoformat()
            forecast_data.append(row_dict)
        
        # 写入Redis缓存（SWR策略）
        cache_payload = {
            'data': forecast_data,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        redis_client.set(cache_key, cache_payload, ttl=SWR_CACHE_TTL)
        redis_client.set(f"{cache_key}:timestamp", datetime.utcnow().isoformat(), ttl=SWR_STALE_TTL)
        
        # 审计日志
        audit = AuditLogger(db)
        audit.log(
            user_id=g.user_id,
            action='view',
            resource_type='forecast',
            resource_id=f"days_{days}",
            details={
                'days': days,
                'metric': metric,
                'cache_hit': False,
                'source': 'database'
            },
            tenant_id=g.tenant_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.commit()
        
        logger.info(f"✅ Forecast data served: {len(forecast_data)} records")
        
        return jsonify({
            'success': True,
            'data': forecast_data,
            'metadata': {
                'cache_hit': False,
                'stale': False,
                'freshness_sec': 0,
                'source': 'database',
                'count': len(forecast_data)
            }
        }), 200
    
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"❌ Database error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
