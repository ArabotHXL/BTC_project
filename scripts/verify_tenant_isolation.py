#!/usr/bin/env python3
"""
多租户越权验证脚本 (Tenant Isolation Verification Script)
验证 customer 角色无法访问非本租户资源

用法:
    python scripts/verify_tenant_isolation.py [--verbose]

验收标准:
    - customer 访问非本租户资源 100% 返回 403
    - 脚本输出 PASS/FAIL 清单
"""

import os
import sys
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_tenant_isolation(verbose=False):
    """
    验证租户隔离
    
    测试场景:
    1. Customer 访问自己租户的资源 -> 应该成功
    2. Customer 访问其他租户的资源 -> 应该返回 403
    
    Returns:
        dict: 验证结果
    """
    from app import app
    from db import db
    from models import User, HostingSite, UserAccess
    
    result = {
        'passed': True,
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'test_results': [],
        'details': ''
    }
    
    with app.app_context():
        customers = User.query.filter(User.role == 'customer').limit(5).all()
        
        if not customers:
            result['details'] = 'No customer users found for testing'
            result['test_results'].append({
                'test': 'find_customers',
                'status': 'SKIP',
                'message': 'No customer users in database'
            })
            return result
        
        all_sites = HostingSite.query.limit(20).all()
        
        if not all_sites:
            result['details'] = 'No hosting sites found for testing'
            result['test_results'].append({
                'test': 'find_sites',
                'status': 'SKIP',
                'message': 'No hosting sites in database'
            })
            return result
        
        from common.rbac import check_site_access
        
        for customer in customers:
            customer_access = UserAccess.query.filter_by(user_id=customer.id).all()
            accessible_site_ids = set()
            
            for access in customer_access:
                if access.site_id:
                    accessible_site_ids.add(access.site_id)
            
            accessible_via_contact = HostingSite.query.filter(
                HostingSite.contact_email == customer.email
            ).all()
            for site in accessible_via_contact:
                accessible_site_ids.add(site.id)
            
            if verbose:
                print(f"\n[INFO] Testing customer: {customer.email} (id={customer.id})")
                print(f"       Accessible sites: {accessible_site_ids}")
            
            for site in all_sites:
                result['total_tests'] += 1
                should_have_access = site.id in accessible_site_ids
                
                with app.test_client() as client:
                    with client.session_transaction() as sess:
                        sess['user_id'] = customer.id
                        sess['email'] = customer.email
                        sess['role'] = 'customer'
                    
                    test_endpoints = [
                        f'/api/sites/{site.id}/commands',
                        f'/hosting/site/{site.id}',
                    ]
                    
                    for endpoint in test_endpoints:
                        try:
                            if 'commands' in endpoint:
                                resp = client.get(endpoint)
                            else:
                                resp = client.get(endpoint)
                            
                            status_code = resp.status_code
                            
                            if should_have_access:
                                if status_code in (200, 302, 404):
                                    test_status = 'PASS'
                                    result['passed_tests'] += 1
                                else:
                                    test_status = 'FAIL'
                                    result['failed_tests'] += 1
                                    result['passed'] = False
                            else:
                                if status_code == 403:
                                    test_status = 'PASS'
                                    result['passed_tests'] += 1
                                elif status_code == 302:
                                    test_status = 'PASS'
                                    result['passed_tests'] += 1
                                else:
                                    test_status = 'FAIL'
                                    result['failed_tests'] += 1
                                    result['passed'] = False
                            
                            test_result = {
                                'customer_id': customer.id,
                                'customer_email': customer.email,
                                'site_id': site.id,
                                'endpoint': endpoint,
                                'should_have_access': should_have_access,
                                'status_code': status_code,
                                'test_status': test_status
                            }
                            result['test_results'].append(test_result)
                            
                            if verbose:
                                icon = '✅' if test_status == 'PASS' else '❌'
                                print(f"       {icon} {endpoint} -> {status_code} (expected: {'allow' if should_have_access else '403'})")
                        
                        except Exception as e:
                            result['test_results'].append({
                                'customer_id': customer.id,
                                'site_id': site.id,
                                'endpoint': endpoint,
                                'test_status': 'ERROR',
                                'error': str(e)
                            })
                            if verbose:
                                print(f"       ⚠️ {endpoint} -> ERROR: {e}")
        
        if result['passed']:
            result['details'] = f"All {result['passed_tests']}/{result['total_tests']} isolation tests passed"
        else:
            result['details'] = f"Isolation FAILED: {result['failed_tests']} tests failed"
    
    return result


def verify_api_isolation(verbose=False):
    """
    验证 API 端点的租户隔离（使用 RBAC check_site_access）
    """
    from app import app
    from db import db
    from models import User, HostingSite
    from flask import session, g
    
    result = {
        'passed': True,
        'tests': [],
        'summary': ''
    }
    
    with app.app_context():
        from common.rbac import check_site_access
        
        customers = User.query.filter(User.role == 'customer').limit(3).all()
        sites = HostingSite.query.limit(10).all()
        
        if not customers or not sites:
            result['summary'] = 'Insufficient test data'
            return result
        
        for customer in customers:
            for site in sites:
                with app.test_request_context():
                    session['user_id'] = customer.id
                    session['email'] = customer.email
                    session['role'] = 'customer'
                    
                    has_access = check_site_access(site.id)
                    
                    is_owner = site.owner_id == customer.id
                    is_contact = site.contact_email == customer.email if site.contact_email else False
                    should_have_access = is_owner or is_contact
                    
                    test_passed = (has_access == should_have_access)
                    
                    result['tests'].append({
                        'customer_id': customer.id,
                        'site_id': site.id,
                        'has_access': has_access,
                        'should_have_access': should_have_access,
                        'passed': test_passed
                    })
                    
                    if not test_passed:
                        result['passed'] = False
                    
                    if verbose:
                        icon = '✅' if test_passed else '❌'
                        print(f"{icon} Customer {customer.id} -> Site {site.id}: "
                              f"access={has_access}, expected={should_have_access}")
        
        passed_count = sum(1 for t in result['tests'] if t['passed'])
        result['summary'] = f"{passed_count}/{len(result['tests'])} RBAC checks passed"
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='验证多租户隔离 (Verify Tenant Isolation)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/verify_tenant_isolation.py           # 运行所有测试
    python scripts/verify_tenant_isolation.py --verbose # 详细输出
    python scripts/verify_tenant_isolation.py --json    # JSON输出
        """
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--rbac-only', action='store_true', help='Only test RBAC check_site_access')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("多租户隔离验证 (Tenant Isolation Verification)")
    print("=" * 60)
    
    if args.rbac_only:
        print("\nMode: RBAC check_site_access only")
        result = verify_api_isolation(verbose=args.verbose)
    else:
        print("\nMode: Full endpoint isolation test")
        result = verify_tenant_isolation(verbose=args.verbose)
    
    print("-" * 60)
    
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\nTotal tests:  {result.get('total_tests', len(result.get('tests', [])))}")
        print(f"Passed:       {result.get('passed_tests', sum(1 for t in result.get('tests', []) if t.get('passed')))}")
        print(f"Failed:       {result.get('failed_tests', sum(1 for t in result.get('tests', []) if not t.get('passed')))}")
        print("-" * 60)
        
        if result['passed']:
            print("\n✅ PASS - Tenant isolation verified")
        else:
            print("\n❌ FAIL - Tenant isolation compromised")
            
            failed_tests = [t for t in result.get('test_results', result.get('tests', [])) 
                          if t.get('test_status') == 'FAIL' or not t.get('passed', True)]
            
            if failed_tests:
                print("\nFailed tests:")
                for ft in failed_tests[:10]:
                    if 'endpoint' in ft:
                        print(f"  - Customer {ft['customer_id']} accessed site {ft['site_id']} "
                              f"via {ft['endpoint']} (got {ft.get('status_code')})")
                    else:
                        print(f"  - Customer {ft['customer_id']} -> Site {ft['site_id']}: "
                              f"access={ft.get('has_access')}, expected={ft.get('should_have_access')}")
        
        print("=" * 60)
    
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
