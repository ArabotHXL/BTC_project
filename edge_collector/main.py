#!/usr/bin/env python3
"""
HashInsight Edge Collector - CLI测试工具
Board Health Test Tool

Usage:
    python -m edge_collector.main --host 192.168.1.100 --port 4028
    python -m edge_collector.main -H 192.168.1.100 -p 4028 --json
    
Options:
    --host, -H: 矿机IP地址
    --port, -p: CGMiner API端口 (默认4028)
    --timeout, -t: 连接超时秒数 (默认5)
    --json: 输出JSON格式
    --verbose, -v: 详细输出
"""

import argparse
import json
import sys
import logging
from typing import Optional

from .cgminer_client import CGMinerClient, CGMinerError
from .parsers import parse_board_health, parse_pool_info, parse_summary_info, create_miner_snapshot
from .models import HealthStatus


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def format_health_status(status: HealthStatus) -> str:
    """格式化健康状态为带颜色的字符串"""
    colors = {
        HealthStatus.HEALTHY: '\033[92m',   # 绿色
        HealthStatus.WARNING: '\033[93m',   # 黄色
        HealthStatus.CRITICAL: '\033[91m',  # 红色
        HealthStatus.OFFLINE: '\033[90m'    # 灰色
    }
    reset = '\033[0m'
    color = colors.get(status, reset)
    return f"{color}{status.value.upper()}{reset}"


def print_board_table(boards: list):
    """打印板卡健康表格"""
    if not boards:
        print("  No board data available")
        return
    
    print("\n  ┌────────┬───────────┬──────────┬─────────────────┬──────────┐")
    print("  │ Board  │ Hashrate  │   Temp   │     Chips       │  Status  │")
    print("  ├────────┼───────────┼──────────┼─────────────────┼──────────┤")
    
    for board in boards:
        chips_str = f"{board.chips_ok}/{board.chips_total}"
        status_str = format_health_status(board.health)
        
        print(f"  │   {board.board_index}    │ {board.hashrate_ths:7.2f}   │  {board.temperature_c:5.1f}°C │ "
              f"{chips_str:^15} │ {status_str:^8} │")
    
    print("  └────────┴───────────┴──────────┴─────────────────┴──────────┘")


def probe_miner(host: str, port: int = 4028, timeout: float = 5.0,
               json_output: bool = False, verbose: bool = False) -> int:
    """
    探测矿机并输出板级健康数据
    
    Returns:
        0: 成功
        1: 连接失败
        2: 解析错误
    """
    setup_logging(verbose)
    
    print(f"\n🔍 Connecting to {host}:{port}...")
    
    try:
        client = CGMinerClient(host, port, timeout)
        
        summary = client.get_summary()
        stats = client.get_stats()
        pools = client.get_pools()
        latency = client.last_latency_ms
        
        print(f"✅ Connected (latency: {latency:.1f}ms)")
        
    except CGMinerError as e:
        print(f"❌ Connection failed: {e.message}")
        return 1
    
    snapshot = create_miner_snapshot(
        miner_id=host.replace('.', '_'),
        ip_address=host,
        summary_data=summary,
        stats_data=stats,
        pools_data=pools
    )
    
    if json_output:
        print(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False))
        return 0
    
    print(f"\n📊 Miner Summary")
    print(f"  Model: {snapshot.model or 'Unknown'}")
    print(f"  Firmware: {snapshot.firmware or 'Unknown'}")
    print(f"  Uptime: {snapshot.uptime_seconds // 3600}h {(snapshot.uptime_seconds % 3600) // 60}m")
    
    print(f"\n⚡ Performance")
    print(f"  Hashrate (avg): {snapshot.hashrate_total_ths:.2f} TH/s")
    print(f"  Hashrate (5s):  {snapshot.hashrate_5s_ths:.2f} TH/s")
    print(f"  Temperature:    {snapshot.temp_min_c:.1f}°C - {snapshot.temp_max_c:.1f}°C")
    
    if snapshot.fan_speeds_rpm:
        fan_str = ', '.join(f"{rpm} RPM" for rpm in snapshot.fan_speeds_rpm)
        print(f"  Fans: {fan_str}")
    
    print(f"\n⛏️  Pool")
    print(f"  URL: {snapshot.pool_url}")
    print(f"  Worker: {snapshot.pool_user}")
    print(f"  Shares: ✓{snapshot.shares_accepted} / ✗{snapshot.shares_rejected} "
          f"({snapshot.shares_rejected_rate:.2f}% rejected)")
    
    print(f"\n🔧 Board Health ({snapshot.boards_healthy}/{snapshot.boards_total} healthy)")
    print_board_table(snapshot.boards)
    
    overall = snapshot.get_overall_health()
    print(f"\n  Overall Status: {format_health_status(overall)}")
    
    if overall == HealthStatus.CRITICAL:
        print("\n  ⚠️  Warning: Critical issues detected!")
        for board in snapshot.boards:
            if board.health == HealthStatus.CRITICAL:
                if board.temperature_c > 90:
                    print(f"     Board {board.board_index}: Overheating ({board.temperature_c}°C)")
                elif board.chips_failed > 0:
                    print(f"     Board {board.board_index}: {board.chips_failed} failed chips")
    
    return 0


def main():
    """CLI入口"""
    parser = argparse.ArgumentParser(
        description='HashInsight Edge Collector - Board Health Test Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --host 192.168.1.100
  %(prog)s -H 192.168.1.100 -p 4028 --json
  %(prog)s -H 192.168.1.100 --verbose
        """
    )
    
    parser.add_argument('--host', '-H', required=True,
                       help='Miner IP address')
    parser.add_argument('--port', '-p', type=int, default=4028,
                       help='CGMiner API port (default: 4028)')
    parser.add_argument('--timeout', '-t', type=float, default=5.0,
                       help='Connection timeout in seconds (default: 5)')
    parser.add_argument('--json', action='store_true',
                       help='Output in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    exit_code = probe_miner(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        json_output=args.json,
        verbose=args.verbose
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
