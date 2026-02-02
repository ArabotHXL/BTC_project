#!/usr/bin/env python3
"""
审计链验证脚本 (Audit Chain Verification Script)
验证 AuditEvent 表的 hash chain 完整性

用法:
    python scripts/verify_audit_chain.py [--site-id SITE_ID] [--start-id START] [--end-id END] [--verbose]

验收标准:
    - 对指定范围输出 PASS (所有事件 hash chain 连续)
    - 任意断链输出 FAIL 并标出 event_id 与断点
"""

import os
import sys
import json
import hashlib
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def compute_event_hash(event_data: dict) -> str:
    """
    根据 canonical JSON 规则计算事件 hash
    规则: SHA256(prev_hash + canonical_json(event_data))
    """
    data = {
        'event_id': event_data.get('event_id'),
        'site_id': event_data.get('site_id'),
        'actor_type': event_data.get('actor_type'),
        'actor_id': event_data.get('actor_id'),
        'event_type': event_data.get('event_type'),
        'ref_type': event_data.get('ref_type'),
        'ref_id': event_data.get('ref_id'),
        'payload': event_data.get('payload_json'),
        'created_at': event_data.get('created_at').isoformat() if event_data.get('created_at') else None,
        'prev_hash': event_data.get('prev_hash'),
    }
    canonical_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


def verify_audit_chain(site_id=None, start_id=None, end_id=None, verbose=False):
    """
    验证审计链完整性
    
    Returns:
        dict: {
            'passed': bool,
            'total_events': int,
            'verified_events': int,
            'broken_links': list,  # [(event_id, expected_prev_hash, actual_prev_hash)]
            'hash_mismatches': list,  # [(event_id, expected_hash, actual_hash)]
            'details': str
        }
    """
    from app import app
    from db import db
    from models_control_plane import AuditEvent
    
    result = {
        'passed': True,
        'total_events': 0,
        'verified_events': 0,
        'broken_links': [],
        'hash_mismatches': [],
        'first_event_id': None,
        'last_event_id': None,
        'details': ''
    }
    
    with app.app_context():
        query = AuditEvent.query.order_by(AuditEvent.id.asc())
        
        if site_id is not None:
            query = query.filter(AuditEvent.site_id == site_id)
        if start_id is not None:
            query = query.filter(AuditEvent.id >= start_id)
        if end_id is not None:
            query = query.filter(AuditEvent.id <= end_id)
        
        events = query.all()
        result['total_events'] = len(events)
        
        if len(events) == 0:
            result['details'] = 'No audit events found in specified range'
            return result
        
        result['first_event_id'] = events[0].event_id
        result['last_event_id'] = events[-1].event_id
        
        prev_hash = None
        
        for i, event in enumerate(events):
            event_data = {
                'event_id': event.event_id,
                'site_id': event.site_id,
                'actor_type': event.actor_type,
                'actor_id': event.actor_id,
                'event_type': event.event_type,
                'ref_type': event.ref_type,
                'ref_id': event.ref_id,
                'payload_json': event.payload_json,
                'created_at': event.created_at,
                'prev_hash': event.prev_hash,
            }
            
            if i == 0:
                if event.prev_hash is not None and event.prev_hash != '':
                    if verbose:
                        print(f"[INFO] First event has prev_hash (likely not genesis): {event.prev_hash[:16]}...")
            else:
                if prev_hash != event.prev_hash:
                    result['passed'] = False
                    result['broken_links'].append({
                        'event_id': event.event_id,
                        'db_id': event.id,
                        'expected_prev_hash': prev_hash,
                        'actual_prev_hash': event.prev_hash,
                        'position': i
                    })
                    if verbose:
                        print(f"[FAIL] Broken link at event {event.event_id} (id={event.id})")
                        print(f"       Expected prev_hash: {prev_hash}")
                        print(f"       Actual prev_hash:   {event.prev_hash}")
            
            computed_hash = compute_event_hash(event_data)
            if event.event_hash and computed_hash != event.event_hash:
                result['passed'] = False
                result['hash_mismatches'].append({
                    'event_id': event.event_id,
                    'db_id': event.id,
                    'expected_hash': computed_hash,
                    'actual_hash': event.event_hash,
                    'position': i
                })
                if verbose:
                    print(f"[FAIL] Hash mismatch at event {event.event_id} (id={event.id})")
                    print(f"       Computed hash: {computed_hash}")
                    print(f"       Stored hash:   {event.event_hash}")
            
            prev_hash = event.event_hash or computed_hash
            result['verified_events'] += 1
            
            if verbose and i > 0 and i % 100 == 0:
                print(f"[INFO] Verified {i}/{len(events)} events...")
        
        if result['passed']:
            result['details'] = f"All {result['verified_events']} events verified successfully"
        else:
            result['details'] = (
                f"Chain integrity FAILED: "
                f"{len(result['broken_links'])} broken links, "
                f"{len(result['hash_mismatches'])} hash mismatches"
            )
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='验证审计链完整性 (Verify Audit Chain Integrity)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/verify_audit_chain.py                    # 验证所有事件
    python scripts/verify_audit_chain.py --site-id 5       # 验证特定站点
    python scripts/verify_audit_chain.py --start-id 100 --end-id 200  # 验证ID范围
    python scripts/verify_audit_chain.py --verbose          # 详细输出
        """
    )
    parser.add_argument('--site-id', type=int, help='Filter by site ID')
    parser.add_argument('--start-id', type=int, help='Start from this event ID')
    parser.add_argument('--end-id', type=int, help='End at this event ID')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("审计链验证 (Audit Chain Verification)")
    print("=" * 60)
    
    filters = []
    if args.site_id:
        filters.append(f"site_id={args.site_id}")
    if args.start_id:
        filters.append(f"start_id={args.start_id}")
    if args.end_id:
        filters.append(f"end_id={args.end_id}")
    
    if filters:
        print(f"Filters: {', '.join(filters)}")
    else:
        print("Scope: All audit events")
    print("-" * 60)
    
    result = verify_audit_chain(
        site_id=args.site_id,
        start_id=args.start_id,
        end_id=args.end_id,
        verbose=args.verbose
    )
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\nTotal events:    {result['total_events']}")
        print(f"Verified events: {result['verified_events']}")
        if result['first_event_id']:
            print(f"First event:     {result['first_event_id']}")
            print(f"Last event:      {result['last_event_id']}")
        print(f"Broken links:    {len(result['broken_links'])}")
        print(f"Hash mismatches: {len(result['hash_mismatches'])}")
        print("-" * 60)
        
        if result['passed']:
            print("\n✅ PASS - Audit chain integrity verified")
        else:
            print("\n❌ FAIL - Audit chain integrity compromised")
            
            if result['broken_links']:
                print("\nBroken links:")
                for bl in result['broken_links'][:10]:
                    print(f"  - Event {bl['event_id']} (id={bl['db_id']}, position={bl['position']})")
                if len(result['broken_links']) > 10:
                    print(f"  ... and {len(result['broken_links']) - 10} more")
            
            if result['hash_mismatches']:
                print("\nHash mismatches:")
                for hm in result['hash_mismatches'][:10]:
                    print(f"  - Event {hm['event_id']} (id={hm['db_id']}, position={hm['position']})")
                if len(result['hash_mismatches']) > 10:
                    print(f"  ... and {len(result['hash_mismatches']) - 10} more")
        
        print("=" * 60)
    
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
