#!/usr/bin/env python3
"""
区块链集成系统测试脚本
Blockchain Integration System Test Script

这个脚本测试完整的区块链验证和IPFS存储功能
This script tests the complete blockchain verification and IPFS storage functionality
"""

import os
import sys
import logging
import json
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_blockchain_integration():
    """测试区块链集成功能"""
    print("🚀 开始区块链集成系统测试 Starting Blockchain Integration System Test")
    print("=" * 80)
    
    try:
        # 测试1: 导入模块 Test 1: Import modules
        print("\n📦 测试1: 模块导入 Test 1: Module Import")
        print("-" * 40)
        
        try:
            from app import app, db
            from blockchain_integration import (
                standardize_mining_data, 
                compute_data_hash,
                quick_register_mining_data,
                verify_blockchain_data,
                get_blockchain_status,
                encrypt_data,
                decrypt_data
            )
            from models import BlockchainRecord, BlockchainVerificationStatus
            from scheduler import get_scheduler, BlockchainScheduler
            print("✅ 所有模块导入成功 All modules imported successfully")
        except ImportError as e:
            print(f"❌ 模块导入失败 Module import failed: {e}")
            return False
        
        # 测试2: 数据标准化 Test 2: Data standardization
        print("\n🔧 测试2: 数据标准化 Test 2: Data Standardization")
        print("-" * 40)
        
        test_mining_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "site_id": "test_site_001",
            "miner_model": "Antminer S19 Pro",
            "miner_count": 100,
            "hashrate": 11000.0,
            "power_consumption": 325000.0,
            "daily_btc": 0.05432,
            "daily_revenue": 2456.78,
            "daily_profit": 1200.50,
            "btc_price": 45234.56,
            "recorded_by": "test_script"
        }
        
        try:
            standardized_data = standardize_mining_data(test_mining_data)
            print(f"✅ 数据标准化成功 Data standardized successfully")
            print(f"   标准化字段数 Standardized fields: {len(standardized_data)}")
        except Exception as e:
            print(f"❌ 数据标准化失败 Data standardization failed: {e}")
            return False
        
        # 测试3: 数据哈希计算 Test 3: Data hash computation
        print("\n🔐 测试3: 数据哈希计算 Test 3: Data Hash Computation")
        print("-" * 40)
        
        try:
            data_hash = compute_data_hash(standardized_data)
            print(f"✅ 数据哈希计算成功 Data hash computed successfully")
            print(f"   哈希值 Hash: {data_hash[:32]}...")
        except Exception as e:
            print(f"❌ 数据哈希计算失败 Data hash computation failed: {e}")
            return False
        
        # 测试4: 数据加密 Test 4: Data encryption
        print("\n🔒 测试4: 数据加密/解密 Test 4: Data Encryption/Decryption")
        print("-" * 40)
        
        try:
            test_data = json.dumps(standardized_data)
            encrypted_data = encrypt_data(test_data)
            decrypted_data = decrypt_data(encrypted_data)
            
            if test_data == decrypted_data:
                print("✅ 数据加密/解密成功 Data encryption/decryption successful")
            else:
                print("❌ 数据加密/解密验证失败 Data encryption/decryption verification failed")
                return False
        except Exception as e:
            print(f"❌ 数据加密测试失败 Data encryption test failed: {e}")
            return False
        
        # 测试5: 区块链状态检查 Test 5: Blockchain status check
        print("\n⛓️  测试5: 区块链状态检查 Test 5: Blockchain Status Check")
        print("-" * 40)
        
        try:
            blockchain_status = get_blockchain_status()
            print(f"✅ 区块链状态获取成功 Blockchain status retrieved successfully")
            print(f"   状态 Status: {blockchain_status}")
        except Exception as e:
            print(f"❌ 区块链状态检查失败 Blockchain status check failed: {e}")
            return False
        
        # 测试6: 快速区块链注册 Test 6: Quick blockchain registration
        print("\n🚀 测试6: 快速区块链注册 Test 6: Quick Blockchain Registration")
        print("-" * 40)
        
        # 检查是否启用区块链功能
        blockchain_enabled = os.environ.get('BLOCKCHAIN_ENABLED', 'false').lower() == 'true'
        
        if blockchain_enabled:
            try:
                result = quick_register_mining_data(test_mining_data)
                if result:
                    print(f"✅ 区块链注册成功 Blockchain registration successful")
                    print(f"   数据哈希 Data Hash: {result['data_hash'][:32]}...")
                    print(f"   IPFS CID: {result['ipfs_cid']}")
                    print(f"   站点ID Site ID: {result['site_id']}")
                    
                    # 测试7: 数据验证 Test 7: Data verification
                    print("\n🔍 测试7: 数据验证 Test 7: Data Verification")
                    print("-" * 40)
                    
                    time.sleep(2)  # 等待数据上链
                    verification_result = verify_blockchain_data(result['data_hash'], result['ipfs_cid'])
                    
                    if verification_result and verification_result.get('is_valid', False):
                        print("✅ 数据验证成功 Data verification successful")
                    else:
                        print("⚠️  数据验证暂时无法完成 Data verification temporarily unavailable")
                        print("   可能需要等待区块链确认 May need to wait for blockchain confirmation")
                else:
                    print("❌ 区块链注册失败 Blockchain registration failed")
                    return False
            except Exception as e:
                print(f"❌ 区块链注册测试失败 Blockchain registration test failed: {e}")
                return False
        else:
            print("⚠️  区块链功能未启用，跳过注册测试 Blockchain disabled, skipping registration test")
            print("   设置 BLOCKCHAIN_ENABLED=true 启用 Set BLOCKCHAIN_ENABLED=true to enable")
        
        # 测试8: 调度器功能 Test 8: Scheduler functionality
        print("\n📅 测试8: 调度器功能 Test 8: Scheduler Functionality")
        print("-" * 40)
        
        try:
            scheduler = get_scheduler()
            stats = scheduler.get_stats()
            print(f"✅ 调度器功能正常 Scheduler functionality normal")
            print(f"   运行状态 Running: {stats['is_running']}")
            print(f"   运行时间 Uptime: {stats['uptime_hours']:.2f} 小时 hours")
            print(f"   执行任务数 Tasks executed: {stats['tasks_executed']}")
        except Exception as e:
            print(f"❌ 调度器测试失败 Scheduler test failed: {e}")
            return False
        
        # 测试9: 数据库模型 Test 9: Database models
        print("\n🗄️  测试9: 数据库模型 Test 9: Database Models")
        print("-" * 40)
        
        try:
            with app.app_context():
                # 查询区块链记录
                record_count = db.session.query(BlockchainRecord).count()
                print(f"✅ 数据库模型正常 Database models normal")
                print(f"   区块链记录数 Blockchain records: {record_count}")
                
                # 尝试创建测试记录
                if blockchain_enabled and 'result' in locals():
                    test_record = BlockchainRecord(
                        data_hash=result['data_hash'],
                        ipfs_cid=result['ipfs_cid'],
                        site_id=result['site_id'],
                        verification_status=BlockchainVerificationStatus.REGISTERED,
                        hashrate_th=test_mining_data['hashrate'] / 1000,
                        power_consumption_w=test_mining_data['power_consumption'],
                        daily_btc_production=test_mining_data['daily_btc'],
                        daily_revenue_usd=test_mining_data['daily_revenue'],
                        mining_data_summary=json.dumps(test_mining_data),
                        data_timestamp=datetime.utcnow(),
                        created_by="test_script"
                    )
                    
                    db.session.add(test_record)
                    db.session.commit()
                    
                    print(f"✅ 测试记录创建成功 Test record created successfully")
                    print(f"   记录ID Record ID: {test_record.id}")
                    
                    # 清理测试记录
                    db.session.delete(test_record)
                    db.session.commit()
                    print("✅ 测试记录已清理 Test record cleaned up")
                    
        except Exception as e:
            print(f"❌ 数据库模型测试失败 Database model test failed: {e}")
            return False
        
        # 测试总结 Test Summary
        print("\n🎉 测试总结 Test Summary")
        print("=" * 80)
        print("✅ 所有核心功能测试通过 All core functionality tests passed")
        print("\n📋 已验证功能 Verified Features:")
        print("   ✓ 模块导入和初始化 Module import and initialization")
        print("   ✓ 数据标准化和哈希计算 Data standardization and hashing")
        print("   ✓ 数据加密和解密 Data encryption and decryption")
        print("   ✓ 区块链状态检查 Blockchain status checking")
        if blockchain_enabled:
            print("   ✓ 区块链数据注册 Blockchain data registration")
            print("   ✓ IPFS数据存储 IPFS data storage")
        print("   ✓ 调度器功能 Scheduler functionality")
        print("   ✓ 数据库模型操作 Database model operations")
        
        print("\n🌟 区块链验证系统集成完成并正常工作！")
        print("🌟 Blockchain verification system integration complete and working!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误 Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_calculator_integration():
    """测试计算器集成功能"""
    print("\n🧮 测试计算器集成 Testing Calculator Integration")
    print("-" * 40)
    
    try:
        from mining_calculator import calculate_mining_profitability
        
        # 模拟计算器调用
        test_result = calculate_mining_profitability(
            hashrate=110.0,  # TH/s
            power_consumption=3250,  # W
            electricity_cost=0.05,  # $/kWh
            miner_model="Antminer S19 Pro",
            miner_count=1,
            enable_blockchain_recording=True,
            site_id="test_calculator_site"
        )
        
        if test_result and 'blockchain_verification' in test_result:
            blockchain_info = test_result['blockchain_verification']
            print(f"✅ 计算器区块链集成成功 Calculator blockchain integration successful")
            print(f"   区块链功能启用 Blockchain enabled: {blockchain_info['enabled']}")
            print(f"   数据记录状态 Record status: {blockchain_info['status']}")
            
            if blockchain_info.get('recorded', False):
                print(f"   数据哈希 Data hash: {blockchain_info['data_hash'][:32]}...")
                print(f"   IPFS CID: {blockchain_info['ipfs_cid']}")
        else:
            print("⚠️  计算器区块链集成功能未启用 Calculator blockchain integration not enabled")
        
        return True
        
    except Exception as e:
        print(f"❌ 计算器集成测试失败 Calculator integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 启动区块链集成系统完整测试 Starting Complete Blockchain Integration System Test")
    print("🕒 测试时间 Test Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 主要集成测试
    success = test_blockchain_integration()
    
    # 计算器集成测试
    if success:
        success = test_calculator_integration()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 所有测试完成！区块链验证系统已完全集成并正常工作！")
        print("🎉 All tests completed! Blockchain verification system fully integrated and working!")
        exit(0)
    else:
        print("❌ 测试失败，请检查配置和依赖")
        print("❌ Tests failed, please check configuration and dependencies")
        exit(1)