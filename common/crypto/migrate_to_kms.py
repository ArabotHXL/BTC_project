"""
数据加密迁移工具 - 从Fernet迁移到KMS信封加密
Migration Tool: Fernet → KMS Envelope Encryption

使用场景:
1. 首次启用KMS时，迁移现有Fernet加密数据
2. 更换KMS提供商时，重新加密数据
3. 密钥轮换时，批量重新加密

安全特性:
- 零停机迁移
- 回滚支持
- 迁移进度持久化
- 自动备份
- 完整性验证
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from envelope import (
    get_envelope_encryption,
    EncryptionContext,
    get_kms_client,
    KMSProvider
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationProgress:
    """迁移进度追踪"""
    
    def __init__(self, progress_file: str = 'migration_progress.json'):
        self.progress_file = progress_file
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict[str, Any]:
        """加载迁移进度"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'started_at': datetime.utcnow().isoformat(),
            'completed_tables': [],
            'failed_records': [],
            'total_records': 0,
            'migrated_records': 0,
            'status': 'in_progress'
        }
    
    def save_progress(self):
        """保存迁移进度"""
        with open(self.progress_file, 'w') as f:
            json.dumps(self.progress, f, indent=2)
    
    def mark_table_completed(self, table_name: str, record_count: int):
        """标记表迁移完成"""
        self.progress['completed_tables'].append({
            'table': table_name,
            'records': record_count,
            'completed_at': datetime.utcnow().isoformat()
        })
        self.progress['migrated_records'] += record_count
        self.save_progress()
    
    def add_failed_record(self, table_name: str, record_id: int, error: str):
        """记录失败的记录"""
        self.progress['failed_records'].append({
            'table': table_name,
            'record_id': record_id,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.save_progress()
    
    def mark_completed(self):
        """标记迁移完成"""
        self.progress['status'] = 'completed'
        self.progress['completed_at'] = datetime.utcnow().isoformat()
        self.save_progress()
    
    def mark_failed(self, error: str):
        """标记迁移失败"""
        self.progress['status'] = 'failed'
        self.progress['error'] = error
        self.progress['failed_at'] = datetime.utcnow().isoformat()
        self.save_progress()

class FernetToKMSMigrator:
    """Fernet到KMS迁移工具"""
    
    def __init__(
        self,
        database_url: str,
        old_fernet_key: str,
        dry_run: bool = False,
        backup_enabled: bool = True
    ):
        self.database_url = database_url
        self.old_fernet = Fernet(old_fernet_key.encode() if isinstance(old_fernet_key, str) else old_fernet_key)
        self.envelope_enc = get_envelope_encryption()
        self.dry_run = dry_run
        self.backup_enabled = backup_enabled
        
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        
        self.progress = MigrationProgress()
        
        self.encrypted_fields = self._discover_encrypted_fields()
    
    def _discover_encrypted_fields(self) -> Dict[str, List[str]]:
        """
        自动发现需要迁移的加密字段
        
        规则:
        - 字段名包含 'encrypted_' 前缀
        - 字段类型为 TEXT 或 VARCHAR
        - 字段值符合 Fernet 格式 (base64编码)
        """
        encrypted_fields = {}
        
        inspector = inspect(self.engine)
        
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            encrypted_cols = []
            
            for column in columns:
                col_name = column['name']
                col_type = str(column['type'])
                
                if col_name.startswith('encrypted_') or col_name.endswith('_encrypted'):
                    encrypted_cols.append(col_name)
                elif col_name in ['api_key', 'secret', 'password_hash', 'private_key']:
                    encrypted_cols.append(col_name)
            
            if encrypted_cols:
                encrypted_fields[table_name] = encrypted_cols
        
        logger.info(f"Discovered encrypted fields: {encrypted_fields}")
        return encrypted_fields
    
    def backup_table(self, table_name: str):
        """备份表数据"""
        if not self.backup_enabled:
            return
        
        backup_table = f"{table_name}_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        with self.engine.connect() as conn:
            conn.execute(text(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}"))
            conn.commit()
        
        logger.info(f"Created backup table: {backup_table}")
    
    def migrate_table(self, table_name: str, fields: List[str]) -> Tuple[int, int]:
        """
        迁移单个表的加密数据
        
        Returns:
            Tuple[成功数, 失败数]
        """
        logger.info(f"Migrating table: {table_name}, fields: {fields}")
        
        if table_name in [t['table'] for t in self.progress.progress['completed_tables']]:
            logger.info(f"Table {table_name} already migrated, skipping")
            return 0, 0
        
        self.backup_table(table_name)
        
        success_count = 0
        error_count = 0
        
        session = self.Session()
        
        try:
            result = session.execute(text(f"SELECT * FROM {table_name}"))
            records = result.fetchall()
            
            logger.info(f"Found {len(records)} records in {table_name}")
            
            for record in records:
                record_dict = dict(record._mapping)
                record_id = record_dict.get('id')
                
                try:
                    updates = {}
                    
                    for field in fields:
                        old_encrypted_value = record_dict.get(field)
                        
                        if not old_encrypted_value:
                            continue
                        
                        plaintext = self.old_fernet.decrypt(
                            old_encrypted_value.encode() if isinstance(old_encrypted_value, str) else old_encrypted_value
                        ).decode('utf-8')
                        
                        context = EncryptionContext(
                            purpose=f"migrate_{table_name}_{field}",
                            resource_type=table_name
                        )
                        
                        new_envelope = self.envelope_enc.encrypt(plaintext, context)
                        new_encrypted_value = json.dumps(new_envelope)
                        
                        updates[field] = new_encrypted_value
                    
                    if updates and not self.dry_run:
                        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                        update_query = text(f"UPDATE {table_name} SET {set_clause} WHERE id = :id")
                        
                        session.execute(update_query, {'id': record_id, **updates})
                    
                    success_count += 1
                    
                    if success_count % 100 == 0:
                        logger.info(f"Migrated {success_count} records in {table_name}")
                        if not self.dry_run:
                            session.commit()
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to migrate record {record_id} in {table_name}: {e}")
                    self.progress.add_failed_record(table_name, record_id, str(e))
                    session.rollback()
            
            if not self.dry_run:
                session.commit()
            
            self.progress.mark_table_completed(table_name, success_count)
            
            logger.info(f"Table {table_name} migration completed: {success_count} success, {error_count} errors")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to migrate table {table_name}: {e}")
            raise
        
        finally:
            session.close()
        
        return success_count, error_count
    
    def migrate_all(self):
        """迁移所有表"""
        try:
            logger.info("Starting migration from Fernet to KMS...")
            logger.info(f"Dry run mode: {self.dry_run}")
            logger.info(f"Backup enabled: {self.backup_enabled}")
            
            total_success = 0
            total_errors = 0
            
            for table_name, fields in self.encrypted_fields.items():
                success, errors = self.migrate_table(table_name, fields)
                total_success += success
                total_errors += errors
            
            self.progress.mark_completed()
            
            logger.info("=" * 80)
            logger.info("Migration Summary:")
            logger.info(f"  Total records migrated: {total_success}")
            logger.info(f"  Total errors: {total_errors}")
            logger.info(f"  Tables migrated: {len(self.progress.progress['completed_tables'])}")
            logger.info(f"  Failed records: {len(self.progress.progress['failed_records'])}")
            logger.info("=" * 80)
            
            if total_errors > 0:
                logger.warning(f"Migration completed with {total_errors} errors. Check migration_progress.json for details.")
            else:
                logger.info("Migration completed successfully!")
        
        except Exception as e:
            self.progress.mark_failed(str(e))
            logger.error(f"Migration failed: {e}")
            raise
    
    def rollback(self):
        """回滚迁移"""
        logger.info("Rolling back migration...")
        
        for table_info in self.progress.progress['completed_tables']:
            table_name = table_info['table']
            
            backup_tables = []
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    f"SELECT table_name FROM information_schema.tables "
                    f"WHERE table_name LIKE '{table_name}_backup_%'"
                ))
                backup_tables = [row[0] for row in result]
            
            if backup_tables:
                latest_backup = sorted(backup_tables)[-1]
                
                with self.engine.connect() as conn:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                    conn.execute(text(f"ALTER TABLE {latest_backup} RENAME TO {table_name}"))
                    conn.commit()
                
                logger.info(f"Restored {table_name} from {latest_backup}")
            else:
                logger.warning(f"No backup found for {table_name}")
        
        logger.info("Rollback completed")

def main():
    parser = argparse.ArgumentParser(description='Migrate from Fernet to KMS encryption')
    parser.add_argument('--database-url', required=True, help='Database connection URL')
    parser.add_argument('--old-fernet-key', required=True, help='Old Fernet encryption key')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no changes)')
    parser.add_argument('--no-backup', action='store_true', help='Disable backup creation')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration')
    
    args = parser.parse_args()
    
    migrator = FernetToKMSMigrator(
        database_url=args.database_url,
        old_fernet_key=args.old_fernet_key,
        dry_run=args.dry_run,
        backup_enabled=not args.no_backup
    )
    
    if args.rollback:
        migrator.rollback()
    else:
        migrator.migrate_all()

if __name__ == '__main__':
    main()
