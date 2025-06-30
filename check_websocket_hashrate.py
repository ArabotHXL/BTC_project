#!/usr/bin/env python3
"""
检查Blockchain.info WebSocket API的hashrate数据
"""

import socket
import ssl
import base64
import hashlib
import struct
import json
import time
from datetime import datetime

def create_websocket_key():
    """生成WebSocket握手密钥"""
    key = base64.b64encode(hashlib.sha1().digest()[:16]).decode()
    return key

def decode_websocket_frame(data):
    """解码WebSocket帧"""
    if len(data) < 2:
        return None
    
    opcode = data[0] & 0x0F
    masked = bool(data[1] & 0x80)
    payload_len = data[1] & 0x7F
    
    if opcode != 1:  # 只处理文本帧
        return None
    
    if payload_len < 126:
        payload_start = 2
    elif payload_len == 126:
        payload_len = struct.unpack('>H', data[2:4])[0]
        payload_start = 4
    else:
        payload_len = struct.unpack('>Q', data[2:10])[0]
        payload_start = 10
    
    try:
        payload_end = payload_start + payload_len
        if payload_end > len(data):
            return None
            
        payload = data[payload_start:payload_end]
        text = payload.decode('utf-8', errors='ignore')
        return json.loads(text)
    except:
        return None

def check_websocket_hashrate():
    """检查WebSocket API的hashrate数据"""
    print("检查 Blockchain.info WebSocket API - hashrate数据")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 创建SSL连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        
        context = ssl.create_default_context()
        ssl_sock = context.wrap_socket(sock, server_hostname='ws.blockchain.info')
        ssl_sock.connect(('ws.blockchain.info', 443))
        
        # WebSocket握手
        key = create_websocket_key()
        handshake = (
            "GET /inv HTTP/1.1\r\n"
            "Host: ws.blockchain.info\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        
        ssl_sock.send(handshake.encode())
        response = ssl_sock.recv(2048).decode()
        
        if "101 Switching Protocols" not in response:
            print("❌ WebSocket握手失败")
            return
        
        print("✅ WebSocket连接建立成功")
        
        # 创建WebSocket帧
        def create_frame(data):
            payload = data.encode('utf-8')
            frame = bytearray()
            frame.append(0x81)  # FIN=1, opcode=1 (text)
            
            if len(payload) < 126:
                frame.append(len(payload) | 0x80)  # mask=1
            else:
                frame.append(126 | 0x80)
                frame.extend(struct.pack('>H', len(payload)))
            
            # 掩码
            mask = struct.pack('>I', 0x12345678)
            frame.extend(mask)
            
            # 掩码化的数据
            for i, byte in enumerate(payload):
                frame.append(byte ^ mask[i % 4])
            
            return bytes(frame)
        
        # 订阅不同类型的数据
        subscriptions = [
            {"op": "blocks_sub"},           # 新区块
            {"op": "unconfirmed_sub"},      # 未确认交易
        ]
        
        for sub in subscriptions:
            frame = create_frame(json.dumps(sub))
            ssl_sock.send(frame)
            print(f"📡 已订阅: {sub['op']}")
            time.sleep(0.5)
        
        # 监听数据并分析hashrate相关信息
        print("\n🔍 监听数据中... (寻找hashrate相关信息)")
        start_time = time.time()
        message_count = 0
        block_count = 0
        hashrate_found = False
        
        while time.time() - start_time < 30:  # 监听30秒
            try:
                ssl_sock.settimeout(2)
                raw_data = ssl_sock.recv(4096)
                
                if not raw_data:
                    continue
                
                # 解码WebSocket帧
                json_data = decode_websocket_frame(raw_data)
                if not json_data:
                    continue
                
                message_count += 1
                
                if json_data.get('op') == 'block':
                    block_count += 1
                    block_data = json_data.get('x', {})
                    
                    print(f"\n📦 新区块 #{block_count}:")
                    print(f"   高度: {block_data.get('height', 'N/A')}")
                    print(f"   时间戳: {block_data.get('time', 'N/A')}")
                    print(f"   交易数: {len(block_data.get('tx', []))}")
                    
                    # 检查是否包含hashrate信息
                    for key in block_data:
                        if 'hash' in key.lower() and key != 'hash':
                            print(f"   {key}: {block_data[key]}")
                            if 'rate' in key.lower():
                                hashrate_found = True
                    
                    # 检查区块头信息
                    if 'bits' in block_data:
                        print(f"   难度位: {block_data['bits']}")
                    if 'nonce' in block_data:
                        print(f"   随机数: {block_data['nonce']}")
                    
                    # 计算区块间隔时间
                    if block_count > 1:
                        current_time = block_data.get('time', 0)
                        if hasattr(check_websocket_hashrate, 'last_block_time'):
                            interval = current_time - check_websocket_hashrate.last_block_time
                            print(f"   区块间隔: {interval}秒")
                        check_websocket_hashrate.last_block_time = current_time
                
                elif json_data.get('op') == 'utx':
                    # 交易数据，通常不包含hashrate信息
                    pass
                
                # 打印完整的JSON结构以寻找hashrate字段
                if message_count <= 3:  # 只打印前3条消息的完整结构
                    print(f"\n📄 消息结构 #{message_count}:")
                    for key in json_data:
                        if key == 'x' and isinstance(json_data[key], dict):
                            print(f"   {key}: {{...}} (区块/交易数据)")
                            # 检查嵌套的字段
                            for subkey in json_data[key]:
                                if 'hash' in subkey.lower() or 'rate' in subkey.lower():
                                    print(f"     -> {subkey}: {json_data[key][subkey]}")
                        else:
                            print(f"   {key}: {json_data[key]}")
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"❌ 数据处理错误: {e}")
                continue
        
        ssl_sock.close()
        
        # 生成分析报告
        print(f"\n" + "=" * 60)
        print("📊 WebSocket API hashrate数据分析报告")
        print("=" * 60)
        print(f"监听时长: 30秒")
        print(f"收到消息: {message_count}")
        print(f"新区块数: {block_count}")
        print(f"Hashrate字段: {'发现' if hashrate_found else '未发现'}")
        
        print(f"\n💡 结论:")
        if hashrate_found:
            print("   ✅ WebSocket API包含hashrate相关数据")
        else:
            print("   ❌ WebSocket API不直接提供hashrate数据")
            print("   📝 该API主要提供:")
            print("      • 实时区块通知")
            print("      • 交易流数据")
            print("      • 区块头信息")
            print("      • 需要通过难度计算hashrate")
        
        print(f"\n🔧 对挖矿计算器的价值:")
        print("   • 实时区块通知: 高价值")
        print("   • 直接hashrate数据: 无")
        print("   • 难度数据: 可用于计算hashrate")
        print("   • 建议: 作为通知机制，配合其他API获取hashrate")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    check_websocket_hashrate()