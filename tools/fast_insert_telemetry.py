#!/usr/bin/env python3
"""
[DEPRECATED] Use generate_telemetry_24h.py instead

This script is a compatibility wrapper that delegates to the new unified generator.
"""

import sys
from generate_telemetry_24h import generate_telemetry_24h

def main():
    print("=" * 80)
    print("[DEPRECATED] This tool is superseded by generate_telemetry_24h.py")
    print("=" * 80)
    print()
    
    # Delegate to the new generator
    generate_telemetry_24h()

if __name__ == '__main__':
    main()
