#!/usr/bin/env python3
"""
CGMiner API 连接测试工具
用于验证能否连接到Antminer矿机的CGMiner API并获取实时数据

使用方法:
    python tools/test_cgminer.py --ip 192.168.1.100
    python tools/test_cgminer.py --ip 192.168.1.100 --port 4028 --verbose
    python tools/test_cgminer.py --batch ips.txt
"""

import socket
import json
import argparse
import sys
import time
from typing import Optional, Dict, List
from datetime import datetime


class CGMinerTester:
    """CGMiner API 测试客户端"""
    
    def __init__(self, ip_address: str, port: int = 4028, timeout: int = 5):
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
    
    def send_command(self, command: str) -> Optional[Dict]:
        """
        发送CGMiner API命令
        
        Args:
            command: 命令名称（如 'summary', 'stats', 'pools'）
        
        Returns:
            API响应的JSON数据，失败返回None
        """
        sock = None
        try:
            # 创建TCP socket连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            # 连接到CGMiner API
            sock.connect((self.ip_address, self.port))
            
            # 发送命令
            request = json.dumps({"command": command})
            sock.sendall(request.encode('utf-8'))
            
            # 接收响应
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            
            # 解析JSON响应（移除末尾的null字符）
            if response:
                response_str = response.decode('utf-8').rstrip('\x00')
                return json.loads(response_str)
            
            return None
            
        except socket.timeout:
            print(f"❌ 连接超时: {self.ip_address}:{self.port}")
            return None
        except socket.error as e:
            print(f"❌ Socket错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            return None
        finally:
            # 确保socket总是被关闭，防止资源泄漏
            if sock:
                try:
                    sock.close()
                except:
                    pass
    
    def test_connection(self, verbose: bool = False) -> bool:
        """
        测试连接并获取矿机信息
        
        Args:
            verbose: 是否显示详细信息
        
        Returns:
            连接成功返回True，否则返回False
        """
        print(f"\n{'='*70}")
        print(f"🔍 测试矿机: {self.ip_address}:{self.port}")
        print(f"{'='*70}")
        
        # 测试summary命令
        print("\n📊 获取矿机摘要信息...")
        summary_data = self.send_command('summary')
        
        if not summary_data:
            print(f"❌ 无法连接到 {self.ip_address}:{self.port}")
            print("\n可能的原因:")
            print("  1. 矿机未开机或网络不可达")
            print("  2. CGMiner API未启用")
            print("  3. 防火墙阻止端口4028")
            print("  4. IP地址错误")
            return False
        
        # 解析摘要数据
        summary = summary_data.get('SUMMARY', [{}])[0]
        status = summary_data.get('STATUS', [{}])[0]
        
        print(f"✅ 连接成功!")
        print(f"\n📋 基本信息:")
        print(f"  软件版本: {status.get('Description', 'Unknown')}")
        print(f"  运行时间: {self._format_uptime(summary.get('Elapsed', 0))}")
        print(f"  当前时间: {datetime.fromtimestamp(status.get('When', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n⚡ 算力数据:")
        ghs_5s = summary.get('GHS 5s', 0)
        ghs_avg = summary.get('GHS av', 0)
        print(f"  实时算力: {ghs_5s / 1000:.2f} TH/s")
        print(f"  平均算力: {ghs_avg / 1000:.2f} TH/s")
        
        print(f"\n📈 工作份额:")
        accepted = summary.get('Accepted', 0)
        rejected = summary.get('Rejected', 0)
        total = accepted + rejected
        reject_rate = (rejected / total * 100) if total > 0 else 0
        print(f"  接受份额: {accepted}")
        print(f"  拒绝份额: {rejected}")
        print(f"  拒绝率: {reject_rate:.2f}%")
        print(f"  硬件错误: {summary.get('Hardware Errors', 0)}")
        
        # 获取详细统计
        if verbose:
            print(f"\n🔧 获取详细统计信息...")
            stats_data = self.send_command('stats')
            
            if stats_data:
                stats = stats_data.get('STATS', [{}])
                if len(stats) > 0:
                    stat = stats[0]
                    
                    print(f"\n🌡️ 温度数据:")
                    temps = []
                    for i in range(1, 10):
                        temp_key = f'temp{i}'
                        if temp_key in stat:
                            temp_val = stat[temp_key]
                            if temp_val and temp_val > 0:
                                temps.append(temp_val)
                                print(f"  温度{i}: {temp_val}°C")
                    
                    if temps:
                        print(f"  平均温度: {sum(temps) / len(temps):.1f}°C")
                        print(f"  最高温度: {max(temps)}°C")
                    
                    print(f"\n💨 风扇速度:")
                    fans = []
                    for i in range(1, 10):
                        fan_key = f'fan{i}'
                        if fan_key in stat:
                            fan_val = stat[fan_key]
                            if fan_val and fan_val > 0:
                                fans.append(fan_val)
                                print(f"  风扇{i}: {fan_val} RPM")
                    
                    if fans:
                        print(f"  平均转速: {sum(fans) / len(fans):.0f} RPM")
            
            # 获取矿池信息
            print(f"\n🏊 矿池信息...")
            pools_data = self.send_command('pools')
            
            if pools_data:
                pools = pools_data.get('POOLS', [])
                for pool in pools:
                    pool_id = pool.get('POOL', 'Unknown')
                    url = pool.get('URL', 'Unknown')
                    user = pool.get('User', 'Unknown')
                    status = pool.get('Status', 'Unknown')
                    priority = pool.get('Priority', 0)
                    
                    print(f"\n  矿池 #{pool_id}:")
                    print(f"    地址: {url}")
                    print(f"    用户: {user}")
                    print(f"    状态: {status}")
                    print(f"    优先级: {priority}")
                    print(f"    接受份额: {pool.get('Accepted', 0)}")
                    print(f"    拒绝份额: {pool.get('Rejected', 0)}")
        
        print(f"\n{'='*70}\n")
        return True
    
    def _format_uptime(self, seconds: int) -> str:
        """格式化运行时间"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if days > 0:
            return f"{days}天 {hours}小时 {minutes}分钟"
        elif hours > 0:
            return f"{hours}小时 {minutes}分钟"
        elif minutes > 0:
            return f"{minutes}分钟 {secs}秒"
        else:
            return f"{secs}秒"
    
    def get_telemetry_data(self) -> Optional[Dict]:
        """
        获取标准化的遥测数据（用于后端API）
        
        Returns:
            标准化的遥测数据字典
        """
        summary_data = self.send_command('summary')
        stats_data = self.send_command('stats')
        pools_data = self.send_command('pools')
        
        if not summary_data:
            return None
        
        try:
            summary = summary_data.get('SUMMARY', [{}])[0]
            stats = stats_data.get('STATS', [{}])[0] if stats_data else {}
            pools = pools_data.get('POOLS', [{}])[0] if pools_data else {}
            
            # 提取温度数据
            temperatures = []
            for i in range(1, 10):
                temp = stats.get(f'temp{i}')
                if temp and temp > 0:
                    temperatures.append(float(temp))
            
            # 提取风扇数据
            fan_speeds = []
            for i in range(1, 10):
                fan = stats.get(f'fan{i}')
                if fan and fan > 0:
                    fan_speeds.append(int(fan))
            
            # 构造标准化数据
            telemetry = {
                "timestamp": int(time.time()),
                "online": True,
                "hashrate_5s": round(summary.get('GHS 5s', 0) / 1000, 2),
                "hashrate_avg": round(summary.get('GHS av', 0) / 1000, 2),
                "temperature_avg": round(sum(temperatures) / len(temperatures), 2) if temperatures else None,
                "temperature_max": max(temperatures) if temperatures else None,
                "fan_speeds": fan_speeds,
                "fan_avg": int(sum(fan_speeds) / len(fan_speeds)) if fan_speeds else None,
                "accepted_shares": summary.get('Accepted', 0),
                "rejected_shares": summary.get('Rejected', 0),
                "hardware_errors": summary.get('Hardware Errors', 0),
                "reject_rate": round((summary.get('Rejected', 0) / max(summary.get('Accepted', 1), 1)) * 100, 2),
                "uptime_seconds": summary.get('Elapsed', 0),
                "pool_url": pools.get('URL', ''),
                "pool_worker": pools.get('User', ''),
                "pool_status": pools.get('Status', 'Unknown')
            }
            
            return telemetry
            
        except Exception as e:
            print(f"❌ 解析遥测数据错误: {e}")
            return None


def batch_test(ip_file: str, verbose: bool = False):
    """
    批量测试多台矿机
    
    Args:
        ip_file: IP地址文件路径（每行一个IP）
        verbose: 是否显示详细信息
    """
    try:
        with open(ip_file, 'r') as f:
            ips = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"❌ 文件未找到: {ip_file}")
        return
    
    print(f"\n📋 批量测试 {len(ips)} 台矿机")
    print(f"{'='*70}\n")
    
    results = {
        'success': [],
        'failed': []
    }
    
    for ip in ips:
        tester = CGMinerTester(ip)
        if tester.test_connection(verbose=verbose):
            results['success'].append(ip)
        else:
            results['failed'].append(ip)
        
        time.sleep(1)  # 避免过快请求
    
    # 汇总结果
    print(f"\n{'='*70}")
    print(f"📊 测试结果汇总")
    print(f"{'='*70}")
    print(f"✅ 成功: {len(results['success'])} 台")
    print(f"❌ 失败: {len(results['failed'])} 台")
    
    if results['failed']:
        print(f"\n失败的矿机:")
        for ip in results['failed']:
            print(f"  - {ip}")


def main():
    parser = argparse.ArgumentParser(
        description='CGMiner API 连接测试工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  测试单台矿机:
    python test_cgminer.py --ip 192.168.1.100
    
  测试单台矿机（详细信息）:
    python test_cgminer.py --ip 192.168.1.100 --verbose
    
  批量测试多台矿机:
    python test_cgminer.py --batch ips.txt
    
  获取JSON格式的遥测数据:
    python test_cgminer.py --ip 192.168.1.100 --json
        """
    )
    
    parser.add_argument('--ip', type=str, help='矿机IP地址')
    parser.add_argument('--port', type=int, default=4028, help='CGMiner API端口（默认4028）')
    parser.add_argument('--timeout', type=int, default=5, help='连接超时时间（秒，默认5）')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息（温度、风扇、矿池等）')
    parser.add_argument('--batch', type=str, help='批量测试：IP地址文件路径')
    parser.add_argument('--json', action='store_true', help='输出JSON格式的遥测数据')
    
    args = parser.parse_args()
    
    # 批量测试模式
    if args.batch:
        batch_test(args.batch, args.verbose)
        return
    
    # 单机测试模式
    if not args.ip:
        parser.print_help()
        sys.exit(1)
    
    tester = CGMinerTester(args.ip, args.port, args.timeout)
    
    if args.json:
        # JSON输出模式
        telemetry = tester.get_telemetry_data()
        if telemetry:
            print(json.dumps(telemetry, indent=2, ensure_ascii=False))
        else:
            sys.exit(1)
    else:
        # 人类可读模式
        success = tester.test_connection(verbose=args.verbose)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
