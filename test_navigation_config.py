#!/usr/bin/env python3
"""
导航配置测试脚本
用于验证navigation_config.py的功能
"""

from navigation_config import (
    get_user_navigation,
    get_user_menu,
    get_breadcrumb,
    has_permission,
    get_role_permissions,
    ROLE_HIERARCHY
)


def test_role_hierarchy():
    """测试角色层级"""
    print("=" * 60)
    print("测试角色层级")
    print("=" * 60)
    
    for role, level in sorted(ROLE_HIERARCHY.items(), key=lambda x: x[1], reverse=True):
        print(f"{role:15} - 等级: {level}")
    
    print()


def test_permissions():
    """测试权限检查"""
    print("=" * 60)
    print("测试权限检查")
    print("=" * 60)
    
    test_cases = [
        ('owner', 'guest', True),
        ('admin', 'user', True),
        ('mining_site', 'admin', False),
        ('user', 'mining_site', False),
        ('guest', 'user', False),
        ('owner', 'owner', True),
    ]
    
    for user_role, required_role, expected in test_cases:
        result = has_permission(user_role, required_role)
        status = "✓" if result == expected else "✗"
        print(f"{status} {user_role:15} 访问 {required_role:15} 需要的功能: {result} (期望: {expected})")
    
    print()


def test_navigation_menu():
    """测试导航菜单生成"""
    print("=" * 60)
    print("测试导航菜单生成")
    print("=" * 60)
    
    roles = ['guest', 'user', 'mining_site', 'admin', 'owner']
    languages = ['zh', 'en']
    
    for role in roles:
        for lang in languages:
            menu = get_user_navigation(role, lang)
            print(f"\n{role.upper()} - {lang.upper()}:")
            print(f"可见菜单项: {len(menu)}")
            
            for item in menu:
                print(f"  - {item['name']} ({item.get('url', '#')})")
                if 'children' in item:
                    for child in item['children']:
                        print(f"    └─ {child['name']} ({child.get('url', '#')})")
    
    print()


def test_user_menu():
    """测试用户菜单"""
    print("=" * 60)
    print("测试用户菜单（右上角下拉菜单）")
    print("=" * 60)
    
    for role in ['guest', 'user', 'admin', 'owner']:
        menu = get_user_menu(role, 'zh')
        print(f"\n{role.upper()}:")
        for item in menu:
            print(f"  - {item['name']} ({item.get('url', '#')})")
    
    print()


def test_breadcrumb():
    """测试面包屑导航"""
    print("=" * 60)
    print("测试面包屑导航")
    print("=" * 60)
    
    test_urls = [
        '/dashboard',
        '/calculator',
        '/batch-calculator',
        '/analytics',
        '/crm/customers',
        '/system-config'
    ]
    
    for url in test_urls:
        breadcrumb = get_breadcrumb(url, 'owner', 'zh')
        if breadcrumb:
            path = ' > '.join([item['name'] for item in breadcrumb])
            print(f"{url:30} -> {path}")
        else:
            print(f"{url:30} -> (未找到)")
    
    print()


def test_role_permissions_description():
    """测试角色权限描述"""
    print("=" * 60)
    print("测试角色权限描述")
    print("=" * 60)
    
    for role in ['guest', 'user', 'mining_site', 'admin', 'owner']:
        perms = get_role_permissions(role)
        print(f"\n{role.upper()}:")
        print(f"  中文: {perms['zh']}")
        print(f"  英文: {perms['en']}")
        print(f"  功能: {', '.join(perms['features'])}")
    
    print()


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "导航配置系统测试" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    test_role_hierarchy()
    test_permissions()
    test_navigation_menu()
    test_user_menu()
    test_breadcrumb()
    test_role_permissions_description()
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
