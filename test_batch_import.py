"""
测试批量导入功能
Test Batch Import Functionality
"""
import sys
import os

import pytest

pytest.importorskip("flask_sqlalchemy")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from batch.batch_import_manager import BatchImportManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_batch_import():
    """测试批量导入托管矿机"""
    with app.app_context():
        # 使用管理员用户ID (假设ID=1存在)
        # 如果不存在，使用任何存在的用户ID
        from models import UserAccess
        admin_user = UserAccess.query.filter_by(role='admin').first() or UserAccess.query.first()
        
        if not admin_user:
            logger.error("No user found in database. Please create a user first.")
            return False
            
        logger.info(f"Using user ID: {admin_user.id} ({admin_user.email})")
        
        # 创建批量导入管理器
        manager = BatchImportManager(user_id=admin_user.id)
        
        # 读取测试CSV文件
        csv_file_path = 'test_hosting_import.csv'
        if not os.path.exists(csv_file_path):
            logger.error(f"Test CSV file not found: {csv_file_path}")
            return False
            
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        logger.info(f"CSV content loaded ({len(csv_content)} bytes)")
        logger.info("Starting import...")
        
        # 执行导入
        try:
            result = manager.import_csv(csv_content)
            
            logger.info("=" * 60)
            logger.info("IMPORT RESULTS:")
            logger.info("=" * 60)
            logger.info(f"Success: {result.get('success')}")
            logger.info(f"Total rows: {result.get('total_rows')}")
            logger.info(f"Successful: {result.get('success_count')}")
            logger.info(f"Failed: {result.get('error_count')}")
            logger.info(f"Elapsed time: {result.get('elapsed_time')}s")
            
            if result.get('errors'):
                logger.warning(f"\nErrors ({len(result['errors'])}):")
                for error in result['errors']:
                    logger.warning(f"  Row {error['row']}: {error['error_type']} - {error['error']}")
                    if error.get('suggestion'):
                        logger.warning(f"    Suggestion: {error['suggestion']}")
            
            # 验证数据库中的记录
            from models import HostingMiner
            imported_count = HostingMiner.query.count()
            logger.info(f"\nTotal HostingMiner records in database: {imported_count}")
            
            # 显示导入的记录
            if result.get('success_count', 0) > 0:
                logger.info("\nImported records:")
                miners = HostingMiner.query.order_by(HostingMiner.id.desc()).limit(5).all()
                for miner in miners:
                    logger.info(f"  - SN: {miner.serial_number}, Model ID: {miner.miner_model_id}, "
                              f"Hashrate: {miner.actual_hashrate}TH/s, Power: {miner.actual_power}W, "
                              f"Hosting Fee: ${miner.hosting_fee}/mo, Status: {miner.status}")
            
            return result.get('success', False) and result.get('success_count', 0) > 0
            
        except Exception as e:
            logger.error(f"Import failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_batch_import()
    sys.exit(0 if success else 1)
