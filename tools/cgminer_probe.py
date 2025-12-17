#!/usr/bin/env python3
"""
CGMiner Probe CLI Tool
CGMiner 探测命令行工具

Safe connectivity test for Antminer CGMiner API.
Outputs structured status without logging credentials.

Usage:
    python tools/cgminer_probe.py --host 192.168.1.100
    python tools/cgminer_probe.py --host 192.168.1.100 --port 4028 --cmd summary
    python tools/cgminer_probe.py --host 192.168.1.100 --json
"""

import argparse
import sys
import json
from datetime import datetime

sys.path.insert(0, '.')

from services.cgminer_client import (
    CGMinerClient, CGMinerError, 
    get_normalized_telemetry, quick_probe
)


def main():
    parser = argparse.ArgumentParser(
        description='CGMiner API Probe Tool - Safe connectivity testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python tools/cgminer_probe.py --host 192.168.1.100
  python tools/cgminer_probe.py --host 192.168.1.100 --cmd stats
  python tools/cgminer_probe.py --host 192.168.1.100 --json --timeout 3
        '''
    )
    
    parser.add_argument('--host', '-H', required=True, help='Miner IP address or hostname')
    parser.add_argument('--port', '-p', type=int, default=4028, help='CGMiner API port (default: 4028)')
    parser.add_argument('--cmd', '-c', default='summary', 
                       choices=['summary', 'stats', 'pools', 'devs', 'version', 'all'],
                       help='Command to execute (default: summary)')
    parser.add_argument('--timeout', '-t', type=float, default=5.0, help='Timeout in seconds (default: 5)')
    parser.add_argument('--json', '-j', action='store_true', help='Output JSON format')
    parser.add_argument('--normalized', '-n', action='store_true', help='Output normalized telemetry')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode - only output result line')
    
    args = parser.parse_args()
    
    if args.quiet or args.json:
        result = quick_probe(args.host, args.port, args.timeout)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"{result['result']} | {result['latency_ms']:.1f}ms | "
                  f"{result['hashrate_ghs']:.2f} GH/s | {result['temp_max']:.1f}C | {result['as_of']}")
        
        sys.exit(0 if result['result'] == 'OK' else 1)
    
    print(f"\n{'='*60}")
    print(f"CGMiner Probe: {args.host}:{args.port}")
    print(f"{'='*60}")
    
    try:
        client = CGMinerClient(args.host, args.port, args.timeout)
        
        if args.normalized:
            print("\n[Normalized Telemetry]")
            telemetry = get_normalized_telemetry(client)
            for key, value in telemetry.items():
                print(f"  {key}: {value}")
            print(f"\nResult: {'OK' if telemetry['status'] == 'online' else 'FAIL'}")
            sys.exit(0 if telemetry['status'] == 'online' else 1)
        
        if args.cmd == 'all':
            commands = ['summary', 'stats', 'pools', 'devs', 'version']
        else:
            commands = [args.cmd]
        
        for cmd in commands:
            print(f"\n[{cmd.upper()}]")
            try:
                result = client.send_command(cmd)
                print(json.dumps(result, indent=2, default=str))
                print(f"  Latency: {client.last_latency_ms:.1f}ms")
            except CGMinerError as e:
                print(f"  Error: {e.message}")
        
        print(f"\n{'='*60}")
        print(f"Result: OK | Latency: {client.last_latency_ms:.1f}ms | As of: {datetime.utcnow().isoformat()}Z")
        print(f"{'='*60}\n")
        
    except CGMinerError as e:
        print(f"\n[ERROR] {e.error_type}: {e.message}")
        print(f"\nResult: FAIL | As of: {datetime.utcnow().isoformat()}Z\n")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[VALIDATION ERROR] {e}\n")
        sys.exit(2)
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {type(e).__name__}: {e}\n")
        sys.exit(3)


if __name__ == '__main__':
    main()
