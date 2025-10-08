#!/usr/bin/env python3
"""
HashInsight CDC Platform - DLQ Replay Script
死信队列事件回放脚本

功能：
1. 从event_dlq表读取失败事件
2. 重新发布到Kafka主题
3. 支持按事件类型、时间范围过滤
4. 支持批量回放和单条回放
5. 记录回放结果

Author: HashInsight Team
Version: 1.0.0
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# 添加CDC核心模块到路径
CDC_CORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, CDC_CORE_PATH)

from flask import Flask
from infra.database import db, init_db  # type: ignore
from infra.kafka_producer import kafka_producer  # type: ignore

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DLQReplayManager:
    """DLQ回放管理器"""
    
    def __init__(self, app: Flask):
        """初始化回放管理器"""
        self.app = app
        self.kafka_producer = kafka_producer
        logger.info("✅ DLQReplayManager initialized")
    
    def get_dlq_events(
        self,
        consumer_name: Optional[str] = None,
        event_kind: Optional[str] = None,
        hours_ago: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取DLQ中的失败事件
        
        参数:
            consumer_name: 消费者名称（可选）
            event_kind: 事件类型（可选）
            hours_ago: 时间范围（小时）
            limit: 返回数量限制
        
        返回:
            失败事件列表
        """
        with self.app.app_context():
            try:
                # 构建查询条件
                conditions = ["created_at > NOW() - INTERVAL ':hours hours'"]
                params = {'hours': hours_ago, 'limit': limit}
                
                if consumer_name:
                    conditions.append("consumer_name = :consumer_name")
                    params['consumer_name'] = consumer_name
                
                if event_kind:
                    conditions.append("event_kind = :event_kind")
                    params['event_kind'] = event_kind
                
                where_clause = " AND ".join(conditions)
                
                sql = text(f"""
                    SELECT 
                        id,
                        consumer_name,
                        event_id,
                        event_kind,
                        payload,
                        error_message,
                        retry_count,
                        created_at
                    FROM event_dlq
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                
                result = db.session.execute(sql, params)
                events = []
                
                for row in result:
                    events.append({
                        'dlq_id': row.id,
                        'consumer_name': row.consumer_name,
                        'event_id': row.event_id,
                        'event_kind': row.event_kind,
                        'payload': row.payload,
                        'error_message': row.error_message,
                        'retry_count': row.retry_count,
                        'created_at': row.created_at.isoformat()
                    })
                
                logger.info(f"📊 Found {len(events)} DLQ events")
                return events
            
            except SQLAlchemyError as e:
                logger.error(f"❌ Failed to get DLQ events: {e}")
                return []
    
    def replay_event(self, dlq_event: Dict) -> bool:
        """
        回放单个DLQ事件
        
        参数:
            dlq_event: DLQ事件字典
        
        返回:
            是否成功
        """
        try:
            event_kind = dlq_event['event_kind']
            payload = dlq_event['payload']
            
            # 确定目标Kafka主题
            # 根据event_kind路由到对应主题（events.miner, events.treasury等）
            if event_kind.startswith('miner.'):
                topic = 'events.miner'
            elif event_kind.startswith('treasury.'):
                topic = 'events.treasury'
            elif event_kind.startswith('ops.'):
                topic = 'events.ops'
            elif event_kind.startswith('crm.'):
                topic = 'events.crm'
            else:
                logger.warning(f"⚠️ Unknown event type: {event_kind}, using default topic")
                topic = 'events.default'
            
            # 重新发布到Kafka
            message = {
                'id': dlq_event['event_id'],
                'kind': event_kind,
                'user_id': payload.get('user_id'),
                'tenant_id': payload.get('tenant_id', 'default'),
                'payload': payload,
                'replayed_from_dlq': True,
                'original_dlq_id': dlq_event['dlq_id'],
                'replay_timestamp': datetime.utcnow().isoformat()
            }
            
            # 发送到Kafka
            user_id = payload.get('user_id', 'unknown')
            self.kafka_producer.send(
                topic=topic,
                key=str(user_id),
                value=json.dumps(message)
            )
            
            logger.info(
                f"✅ Replayed event to Kafka: "
                f"dlq_id={dlq_event['dlq_id']}, "
                f"event_id={dlq_event['event_id']}, "
                f"topic={topic}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to replay event {dlq_event['dlq_id']}: {e}")
            return False
    
    def replay_batch(
        self,
        consumer_name: Optional[str] = None,
        event_kind: Optional[str] = None,
        hours_ago: int = 24,
        limit: int = 100,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        批量回放DLQ事件
        
        参数:
            consumer_name: 消费者名称过滤
            event_kind: 事件类型过滤
            hours_ago: 时间范围（小时）
            limit: 回放数量限制
            dry_run: 是否模拟运行（不实际发送）
        
        返回:
            回放统计 {total, success, failed}
        """
        logger.info("🔄 Starting DLQ batch replay...")
        logger.info(f"   consumer_name={consumer_name}")
        logger.info(f"   event_kind={event_kind}")
        logger.info(f"   hours_ago={hours_ago}")
        logger.info(f"   limit={limit}")
        logger.info(f"   dry_run={dry_run}")
        
        # 获取DLQ事件
        events = self.get_dlq_events(
            consumer_name=consumer_name,
            event_kind=event_kind,
            hours_ago=hours_ago,
            limit=limit
        )
        
        if not events:
            logger.info("ℹ️ No DLQ events to replay")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        # 回放事件
        success_count = 0
        failed_count = 0
        
        for event in events:
            if dry_run:
                logger.info(f"[DRY RUN] Would replay: {event['dlq_id']} - {event['event_kind']}")
                success_count += 1
            else:
                if self.replay_event(event):
                    success_count += 1
                    # 标记为已回放（可选）
                    self._mark_replayed(event['dlq_id'])
                else:
                    failed_count += 1
        
        result = {
            'total': len(events),
            'success': success_count,
            'failed': failed_count
        }
        
        logger.info(f"✅ Replay completed: {result}")
        return result
    
    def _mark_replayed(self, dlq_id: str):
        """标记DLQ事件为已回放"""
        with self.app.app_context():
            try:
                sql = text("""
                    UPDATE event_dlq
                    SET 
                        replayed = true,
                        replayed_at = NOW()
                    WHERE id = :dlq_id
                """)
                
                db.session.execute(sql, {'dlq_id': dlq_id})
                db.session.commit()
                logger.debug(f"📝 Marked as replayed: {dlq_id}")
            
            except SQLAlchemyError as e:
                logger.error(f"❌ Failed to mark as replayed: {e}")
                db.session.rollback()
    
    def get_dlq_stats(self) -> Dict:
        """获取DLQ统计信息"""
        with self.app.app_context():
            try:
                sql = text("""
                    SELECT 
                        consumer_name,
                        event_kind,
                        COUNT(*) as count,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM event_dlq
                    WHERE replayed = false OR replayed IS NULL
                    GROUP BY consumer_name, event_kind
                    ORDER BY count DESC
                """)
                
                result = db.session.execute(sql)
                stats = []
                
                for row in result:
                    stats.append({
                        'consumer_name': row.consumer_name,
                        'event_kind': row.event_kind,
                        'count': row.count,
                        'oldest': row.oldest.isoformat() if row.oldest else None,
                        'newest': row.newest.isoformat() if row.newest else None
                    })
                
                return {'dlq_breakdown': stats}
            
            except SQLAlchemyError as e:
                logger.error(f"❌ Failed to get DLQ stats: {e}")
                return {'error': str(e)}

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='HashInsight DLQ Replay Tool - 回放死信队列中的失败事件'
    )
    
    # 操作模式
    subparsers = parser.add_subparsers(dest='command', help='操作命令')
    
    # stats命令
    stats_parser = subparsers.add_parser('stats', help='显示DLQ统计信息')
    
    # replay命令
    replay_parser = subparsers.add_parser('replay', help='回放DLQ事件')
    replay_parser.add_argument(
        '--consumer',
        type=str,
        help='消费者名称过滤'
    )
    replay_parser.add_argument(
        '--event-kind',
        type=str,
        help='事件类型过滤'
    )
    replay_parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='时间范围（小时，默认24）'
    )
    replay_parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='回放数量限制（默认100）'
    )
    replay_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模拟运行，不实际发送'
    )
    
    args = parser.parse_args()
    
    # 检查环境变量
    if not os.getenv('DATABASE_URL'):
        logger.error("❌ DATABASE_URL environment variable is required")
        sys.exit(1)
    
    # 初始化Flask应用
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    init_db(app)
    
    # 创建回放管理器
    manager = DLQReplayManager(app)
    
    # 执行命令
    if args.command == 'stats':
        stats = manager.get_dlq_stats()
        print("\n📊 DLQ Statistics:")
        print(json.dumps(stats, indent=2))
    
    elif args.command == 'replay':
        result = manager.replay_batch(
            consumer_name=args.consumer,
            event_kind=args.event_kind,
            hours_ago=args.hours,
            limit=args.limit,
            dry_run=args.dry_run
        )
        
        print(f"\n✅ Replay Result:")
        print(f"   Total: {result['total']}")
        print(f"   Success: {result['success']}")
        print(f"   Failed: {result['failed']}")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
