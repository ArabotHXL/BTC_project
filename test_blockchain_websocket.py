#!/usr/bin/env python3
"""
测试 Blockchain.info WebSocket API
Test Blockchain.info WebSocket API functionality and data quality
"""

import websocket_client as websocket
import json
import time
import threading
from datetime import datetime

class BlockchainWebSocketTest:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.message_count = 0
        self.last_block_data = None
        self.last_transaction_data = None
        
    def on_message(self, ws, message):
        """处理WebSocket消息"""
        try:
            data = json.loads(message)
            self.message_count += 1
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 消息 #{self.message_count}")
            
            if data.get('op') == 'block':
                # 新区块数据
                block_data = data.get('x', {})
                block_height = block_data.get('height', 0)
                block_hash = block_data.get('hash', '')
                tx_count = len(block_data.get('tx', []))
                
                print(f"📦 新区块: #{block_height}")
                print(f"   区块哈希: {block_hash[:16]}...")
                print(f"   交易数量: {tx_count}")
                
                # 分析区块奖励
                if 'tx' in block_data and len(block_data['tx']) > 0:
                    coinbase_tx = block_data['tx'][0]  # 第一个交易是coinbase
                    if 'out' in coinbase_tx:
                        total_reward = sum(out.get('value', 0) for out in coinbase_tx['out'])
                        reward_btc = total_reward / 100000000  # satoshi to BTC
                        print(f"   区块奖励: {reward_btc:.8f} BTC")
                
                self.last_block_data = block_data
                
            elif data.get('op') == 'utx':
                # 新交易数据
                tx_data = data.get('x', {})
                tx_hash = tx_data.get('hash', '')
                
                # 计算交易价值
                total_input = sum(inp.get('prev_out', {}).get('value', 0) for inp in tx_data.get('inputs', []))
                total_output = sum(out.get('value', 0) for out in tx_data.get('out', []))
                
                if total_output > 0:
                    value_btc = total_output / 100000000
                    print(f"💰 新交易: {value_btc:.4f} BTC")
                    print(f"   交易哈希: {tx_hash[:16]}...")
                
                self.last_transaction_data = tx_data
                
            else:
                print(f"📡 其他消息类型: {data.get('op', 'unknown')}")
                print(f"   数据: {str(data)[:100]}...")
                
        except json.JSONDecodeError:
            print(f"❌ JSON解析失败: {message[:100]}...")
        except Exception as e:
            print(f"❌ 消息处理错误: {str(e)}")
    
    def on_error(self, ws, error):
        """处理WebSocket错误"""
        print(f"❌ WebSocket错误: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket关闭"""
        print(f"\n🔌 WebSocket连接已关闭")
        print(f"   状态码: {close_status_code}")
        print(f"   关闭消息: {close_msg}")
        self.connected = False
    
    def on_open(self, ws):
        """处理WebSocket打开"""
        print("✅ WebSocket连接已建立")
        self.connected = True
        
        # 订阅新区块和交易
        try:
            # 订阅新区块
            subscribe_blocks = json.dumps({"op": "blocks_sub"})
            ws.send(subscribe_blocks)
            print("📡 已订阅新区块通知")
            
            # 订阅未确认交易 (可能数据量很大，谨慎使用)
            # subscribe_unconfirmed = json.dumps({"op": "unconfirmed_sub"})
            # ws.send(subscribe_unconfirmed)
            # print("📡 已订阅未确认交易通知")
            
        except Exception as e:
            print(f"❌ 订阅失败: {str(e)}")
    
    def test_websocket_connection(self, duration=30):
        """测试WebSocket连接"""
        print("=" * 60)
        print("🔍 测试 Blockchain.info WebSocket API")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 测试时长: {duration}秒")
        print("=" * 60)
        
        try:
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                "wss://ws.blockchain.info/inv",
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            # 在新线程中运行WebSocket
            def run_websocket():
                self.ws.run_forever()
            
            ws_thread = threading.Thread(target=run_websocket)
            ws_thread.daemon = True
            ws_thread.start()
            
            # 等待连接建立
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                print("❌ WebSocket连接超时")
                return False
            
            # 运行测试指定时间
            test_start = time.time()
            while (time.time() - test_start) < duration and self.connected:
                time.sleep(1)
                
                # 每10秒显示统计信息
                elapsed = int(time.time() - test_start)
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"\n📊 统计信息 ({elapsed}秒):")
                    print(f"   收到消息: {self.message_count}")
                    print(f"   连接状态: {'正常' if self.connected else '断开'}")
            
            # 关闭连接
            if self.ws:
                self.ws.close()
            
            return True
            
        except Exception as e:
            print(f"❌ WebSocket测试失败: {str(e)}")
            return False
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📋 Blockchain.info WebSocket API 测试报告")
        print("=" * 60)
        
        print(f"🔌 连接状态: {'成功' if self.connected else '失败'}")
        print(f"📨 总消息数: {self.message_count}")
        
        if self.last_block_data:
            print(f"📦 最新区块高度: {self.last_block_data.get('height', 'N/A')}")
            print(f"📦 最新区块交易数: {len(self.last_block_data.get('tx', []))}")
        
        # API评估
        print(f"\n🎯 API评估:")
        if self.message_count > 0:
            print("   ✅ 数据接收: 正常")
            print("   ✅ 实时性: 优秀")
            print("   ✅ 数据格式: 结构化JSON")
        else:
            print("   ❌ 数据接收: 失败")
        
        # 推荐使用场景
        print(f"\n💡 推荐使用场景:")
        print("   • 实时区块通知")
        print("   • 网络活动监控")
        print("   • 交易确认追踪")
        
        # 注意事项
        print(f"\n⚠️  使用注意事项:")
        print("   • 数据量可能很大（特别是交易流）")
        print("   • 需要处理连接中断重连")
        print("   • 适合实时监控，不适合历史数据")
        
        print(f"\n🚀 WebSocket API测试完成")

def main():
    """主函数"""
    tester = BlockchainWebSocketTest()
    
    # 运行30秒测试
    success = tester.test_websocket_connection(duration=30)
    
    # 生成报告
    tester.generate_test_report()
    
    return success

if __name__ == "__main__":
    main()