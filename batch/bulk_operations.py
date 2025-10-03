"""
HashInsight Enterprise - Bulk Operations
批量操作管理器
"""

import logging
from typing import List, Dict, Optional
from sqlalchemy import text, or_, and_
from db import db
from models import UserMiner

logger = logging.getLogger(__name__)


class BulkOperationsManager:
    """批量操作管理器"""
    
    # 规则条件
    RULE_OPERATORS = {
        'gt': '>',  # Greater than
        'lt': '<',  # Less than
        'eq': '=',  # Equal
        'gte': '>=',
        'lte': '<=',
        'contains': 'LIKE'
    }
    
    def __init__(self, user_id: int):
        """初始化批量操作管理器"""
        self.user_id = user_id
    
    def select_by_rules(self, rules: List[Dict]) -> List[int]:
        """
        按规则批量选择矿机
        
        Args:
            rules: 规则列表，例如:
                [
                    {'field': 'actual_hashrate', 'operator': 'lt', 'value': 100},
                    {'field': 'status', 'operator': 'eq', 'value': 'active'}
                ]
        
        Returns:
            符合条件的矿机ID列表
        """
        try:
            query = UserMiner.query.filter_by(user_id=self.user_id)
            
            for rule in rules:
                field = rule['field']
                operator = rule['operator']
                value = rule['value']
                
                # 构建查询条件
                if operator == 'gt':
                    query = query.filter(getattr(UserMiner, field) > value)
                elif operator == 'lt':
                    query = query.filter(getattr(UserMiner, field) < value)
                elif operator == 'eq':
                    query = query.filter(getattr(UserMiner, field) == value)
                elif operator == 'gte':
                    query = query.filter(getattr(UserMiner, field) >= value)
                elif operator == 'lte':
                    query = query.filter(getattr(UserMiner, field) <= value)
                elif operator == 'contains':
                    query = query.filter(getattr(UserMiner, field).like(f'%{value}%'))
            
            miners = query.all()
            miner_ids = [m.id for m in miners]
            
            logger.info(f"Selected {len(miner_ids)} miners by rules")
            return miner_ids
            
        except Exception as e:
            logger.error(f"Rule-based selection failed: {e}")
            return []
    
    def bulk_update_notes(self, miner_ids: List[int], note: str, append: bool = True) -> int:
        """
        批量添加备注
        
        Args:
            miner_ids: 矿机ID列表
            note: 备注内容
            append: 是否追加（True）还是替换（False）
        
        Returns:
            更新的矿机数量
        """
        try:
            updated_count = 0
            
            for miner_id in miner_ids:
                miner = UserMiner.query.get(miner_id)
                if miner and miner.user_id == self.user_id:
                    if append and miner.notes:
                        miner.notes = f"{miner.notes}\n{note}"
                    else:
                        miner.notes = note
                    updated_count += 1
            
            db.session.commit()
            logger.info(f"Updated notes for {updated_count} miners")
            return updated_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk notes update failed: {e}")
            return 0
    
    def bulk_update_status(self, miner_ids: List[int], status: str) -> int:
        """
        批量更新状态
        
        Args:
            miner_ids: 矿机ID列表
            status: 新状态（active/maintenance/offline/sold）
        
        Returns:
            更新的矿机数量
        """
        try:
            valid_statuses = ['active', 'maintenance', 'offline', 'sold']
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}")
            
            updated = UserMiner.query.filter(
                UserMiner.id.in_(miner_ids),
                UserMiner.user_id == self.user_id
            ).update({
                'status': status
            }, synchronize_session=False)
            
            db.session.commit()
            logger.info(f"Updated status for {updated} miners to {status}")
            return updated
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk status update failed: {e}")
            return 0
    
    def bulk_archive(self, miner_ids: List[int]) -> int:
        """
        批量归档矿机
        
        Returns:
            归档的矿机数量
        """
        return self.bulk_update_status(miner_ids, 'offline')
    
    def bulk_delete(self, miner_ids: List[int]) -> int:
        """
        批量删除矿机
        
        Returns:
            删除的矿机数量
        """
        try:
            deleted = UserMiner.query.filter(
                UserMiner.id.in_(miner_ids),
                UserMiner.user_id == self.user_id
            ).delete(synchronize_session=False)
            
            db.session.commit()
            logger.info(f"Deleted {deleted} miners")
            return deleted
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk delete failed: {e}")
            return 0
    
    def bulk_export(self, miner_ids: List[int]) -> List[Dict]:
        """
        批量导出选中矿机数据
        
        Returns:
            矿机数据列表
        """
        try:
            miners = UserMiner.query.filter(
                UserMiner.id.in_(miner_ids),
                UserMiner.user_id == self.user_id
            ).all()
            
            export_data = [m.to_dict() for m in miners]
            logger.info(f"Exported {len(export_data)} miners")
            return export_data
            
        except Exception as e:
            logger.error(f"Bulk export failed: {e}")
            return []
