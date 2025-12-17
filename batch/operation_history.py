"""
HashInsight Enterprise - Operation History
操作历史记录与审计追踪
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from db import db
from models import UserMiner

logger = logging.getLogger(__name__)


class OperationHistory:
    """操作历史管理器"""
    
    # 历史记录存储（实际应该存储在数据库中）
    _history = []
    _max_history = 100
    
    @classmethod
    def record_operation(cls, user_id: int, operation_type: str, 
                        miner_ids: List[int], details: Dict,
                        previous_state: Dict = None) -> int:
        """
        记录操作
        
        Args:
            user_id: 用户ID
            operation_type: 操作类型（update_notes, update_status, delete等）
            miner_ids: 受影响的矿机ID列表
            details: 操作详情
            previous_state: 操作前状态（用于撤销）
        
        Returns:
            操作记录ID
        """
        try:
            record = {
                'id': len(cls._history) + 1,
                'user_id': user_id,
                'operation_type': operation_type,
                'miner_ids': miner_ids,
                'details': details,
                'previous_state': previous_state,
                'timestamp': datetime.utcnow().isoformat(),
                'can_undo': previous_state is not None
            }
            
            cls._history.append(record)
            
            # 限制历史记录数量
            if len(cls._history) > cls._max_history:
                cls._history.pop(0)
            
            logger.info(f"Recorded operation {record['id']}: {operation_type}")
            return record['id']
            
        except Exception as e:
            logger.error(f"Failed to record operation: {e}")
            return -1
    
    @classmethod
    def get_history(cls, user_id: int, limit: int = 50) -> List[Dict]:
        """
        获取用户操作历史
        
        Args:
            user_id: 用户ID
            limit: 返回记录数量
        
        Returns:
            操作历史列表
        """
        user_history = [
            h for h in cls._history 
            if h['user_id'] == user_id
        ]
        return user_history[-limit:]
    
    @classmethod
    def undo_operation(cls, user_id: int, operation_id: int) -> bool:
        """
        撤销操作
        
        Args:
            user_id: 用户ID
            operation_id: 操作ID
        
        Returns:
            是否成功
        """
        try:
            # 查找操作记录
            record = next(
                (h for h in cls._history if h['id'] == operation_id and h['user_id'] == user_id),
                None
            )
            
            if not record:
                logger.warning(f"Operation {operation_id} not found")
                return False
            
            if not record['can_undo']:
                logger.warning(f"Operation {operation_id} cannot be undone")
                return False
            
            # 执行撤销
            previous_state = record['previous_state']
            operation_type = record['operation_type']
            
            if operation_type == 'update_notes':
                for miner_id, old_notes in previous_state.items():
                    miner = UserMiner.query.get(int(miner_id))
                    if miner:
                        miner.notes = old_notes
            
            elif operation_type == 'update_status':
                for miner_id, old_status in previous_state.items():
                    miner = UserMiner.query.get(int(miner_id))
                    if miner:
                        miner.status = old_status
            
            elif operation_type == 'delete':
                # 删除操作无法撤销（需要有软删除机制）
                logger.warning("Delete operations cannot be undone")
                return False
            
            db.session.commit()
            
            # 记录撤销操作
            cls.record_operation(
                user_id,
                f'undo_{operation_type}',
                record['miner_ids'],
                {'undone_operation_id': operation_id},
                None
            )
            
            logger.info(f"Undone operation {operation_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Undo operation failed: {e}")
            return False
    
    @classmethod
    def get_audit_trail(cls, user_id: int, miner_id: int = None,
                       start_date: datetime = None,
                       end_date: datetime = None) -> List[Dict]:
        """
        获取审计追踪
        
        Args:
            user_id: 用户ID
            miner_id: 矿机ID（可选）
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            审计记录列表
        """
        audit_trail = []
        
        for record in cls._history:
            # 过滤用户
            if record['user_id'] != user_id:
                continue
            
            # 过滤矿机ID
            if miner_id and miner_id not in record['miner_ids']:
                continue
            
            # 过滤日期范围
            record_time = datetime.fromisoformat(record['timestamp'])
            if start_date and record_time < start_date:
                continue
            if end_date and record_time > end_date:
                continue
            
            audit_trail.append(record)
        
        return audit_trail
