#!/usr/bin/env python3
"""
代码优化分析工具
检查重复代码、冗余文件、性能问题和优化机会
"""

import os
import re
import ast
import json
from collections import defaultdict, Counter
from pathlib import Path

class CodeOptimizationAnalyzer:
    def __init__(self):
        self.issues = {
            'duplicate_files': [],
            'redundant_code': [],
            'performance_issues': [],
            'unused_imports': [],
            'large_functions': [],
            'duplicate_logic': [],
            'optimization_opportunities': []
        }
        
    def analyze_project(self):
        """分析整个项目"""
        print("=" * 80)
        print("代码优化分析报告")
        print("=" * 80)
        
        self.find_duplicate_files()
        self.find_redundant_code()
        self.analyze_python_files()
        self.find_performance_issues()
        self.analyze_templates()
        self.analyze_static_files()
        self.generate_recommendations()
        
    def find_duplicate_files(self):
        """查找重复或相似的文件"""
        print("\n🔍 查找重复文件...")
        
        # 检查明显的重复文件
        duplicate_patterns = [
            ('app.py', 'app_original_backup.py'),
            ('app.py', 'app_simplified.py'),
            ('mining_calculator.py', 'mining_calculator_original_backup.py'),
            ('mining_calculator.py', 'mining_calculator_simplified.py'),
        ]
        
        for file1, file2 in duplicate_patterns:
            if os.path.exists(file1) and os.path.exists(file2):
                try:
                    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
                        content1 = f1.read()
                        content2 = f2.read()
                        
                        # 计算相似度
                        similarity = self.calculate_similarity(content1, content2)
                        
                        self.issues['duplicate_files'].append({
                            'files': [file1, file2],
                            'similarity': similarity,
                            'recommendation': f'考虑删除备份文件 {file2}' if similarity > 0.8 else '内容差异较大，需要确认是否需要保留'
                        })
                except Exception as e:
                    print(f"无法比较文件 {file1} 和 {file2}: {e}")
    
    def find_redundant_code(self):
        """查找冗余代码"""
        print("\n🔍 查找冗余代码...")
        
        # 检查可能的冗余文件
        redundant_candidates = [
            'test_*.py',
            '*_test.py', 
            '*_backup.py',
            '*_original*.py',
            '*_simplified.py',
            'debug_*.py',
            'check_*.py'
        ]
        
        for pattern in redundant_candidates:
            files = list(Path('.').glob(pattern))
            if files:
                for file in files:
                    size = file.stat().st_size
                    self.issues['redundant_code'].append({
                        'file': str(file),
                        'size': size,
                        'type': 'test/debug file',
                        'recommendation': '确认是否仍需要此文件'
                    })
    
    def analyze_python_files(self):
        """分析Python文件"""
        print("\n🔍 分析Python文件...")
        
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 分析文件大小
                lines = content.split('\n')
                if len(lines) > 500:
                    self.issues['large_functions'].append({
                        'file': str(file_path),
                        'lines': len(lines),
                        'recommendation': '考虑拆分为多个模块'
                    })
                
                # 查找重复的import语句
                imports = re.findall(r'^(import .+|from .+ import .+)', content, re.MULTILINE)
                import_counter = Counter(imports)
                duplicates = {imp: count for imp, count in import_counter.items() if count > 1}
                
                if duplicates:
                    self.issues['unused_imports'].append({
                        'file': str(file_path),
                        'duplicates': duplicates,
                        'recommendation': '合并重复的import语句'
                    })
                
                # 查找重复的函数定义
                functions = re.findall(r'^def (\w+)\(', content, re.MULTILINE)
                func_counter = Counter(functions)
                duplicate_funcs = {func: count for func, count in func_counter.items() if count > 1}
                
                if duplicate_funcs:
                    self.issues['duplicate_logic'].append({
                        'file': str(file_path),
                        'functions': duplicate_funcs,
                        'recommendation': '检查是否有重复的函数定义'
                    })
                    
            except Exception as e:
                print(f"分析文件 {file_path} 时出错: {e}")
    
    def find_performance_issues(self):
        """查找性能问题"""
        print("\n🔍 查找性能问题...")
        
        performance_patterns = [
            (r'\.query\.all\(\)', '使用分页查询替代查询所有记录'),
            (r'for .+ in .+\.query\.all\(\)', '避免在循环中查询所有记录'),
            (r'time\.sleep\(', '检查是否有不必要的sleep调用'),
            (r'requests\.get\(.+\)', '考虑添加超时和重试机制'),
            (r'json\.loads\(.*requests', '考虑流式处理大JSON响应'),
        ]
        
        python_files = list(Path('.').glob('*.py'))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern, suggestion in performance_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        self.issues['performance_issues'].append({
                            'file': str(file_path),
                            'pattern': pattern,
                            'matches': len(matches),
                            'suggestion': suggestion
                        })
                        
            except Exception as e:
                print(f"分析性能问题时出错 {file_path}: {e}")
    
    def analyze_templates(self):
        """分析模板文件"""
        print("\n🔍 分析模板文件...")
        
        if not os.path.exists('templates'):
            return
            
        template_files = list(Path('templates').glob('*.html'))
        
        # 查找重复的CSS/JS引用
        css_js_usage = defaultdict(list)
        
        for template in template_files:
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 查找CSS和JS引用
                css_refs = re.findall(r'<link.*?href="([^"]+)"', content)
                js_refs = re.findall(r'<script.*?src="([^"]+)"', content)
                
                for ref in css_refs + js_refs:
                    css_js_usage[ref].append(str(template))
                    
            except Exception as e:
                print(f"分析模板 {template} 时出错: {e}")
        
        # 找出可能重复的资源引用
        common_resources = {ref: files for ref, files in css_js_usage.items() if len(files) > 3}
        
        if common_resources:
            self.issues['optimization_opportunities'].append({
                'type': 'template_resources',
                'common_resources': common_resources,
                'recommendation': '考虑将公共资源提取到base模板'
            })
    
    def analyze_static_files(self):
        """分析静态文件"""
        print("\n🔍 分析静态文件...")
        
        if not os.path.exists('static'):
            return
            
        # 检查大文件
        for root, dirs, files in os.walk('static'):
            for file in files:
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                
                if size > 100 * 1024:  # 大于100KB
                    self.issues['performance_issues'].append({
                        'file': file_path,
                        'size': f"{size/1024:.1f} KB",
                        'type': 'large_static_file',
                        'suggestion': '考虑压缩或优化此文件'
                    })
    
    def calculate_similarity(self, text1, text2):
        """计算两个文本的相似度"""
        lines1 = set(text1.split('\n'))
        lines2 = set(text2.split('\n'))
        
        intersection = len(lines1.intersection(lines2))
        union = len(lines1.union(lines2))
        
        return intersection / union if union > 0 else 0
    
    def generate_recommendations(self):
        """生成优化建议"""
        print("\n" + "=" * 80)
        print("优化建议报告")
        print("=" * 80)
        
        # 重复文件建议
        if self.issues['duplicate_files']:
            print("\n📂 重复文件问题:")
            for issue in self.issues['duplicate_files']:
                print(f"  文件: {issue['files'][0]} <-> {issue['files'][1]}")
                print(f"  相似度: {issue['similarity']:.2%}")
                print(f"  建议: {issue['recommendation']}")
                print()
        
        # 冗余代码建议
        if self.issues['redundant_code']:
            print("\n🗑️ 冗余文件:")
            for issue in self.issues['redundant_code']:
                print(f"  文件: {issue['file']} ({issue['size']} bytes)")
                print(f"  类型: {issue['type']}")
                print(f"  建议: {issue['recommendation']}")
                print()
        
        # 大文件建议
        if self.issues['large_functions']:
            print("\n📏 大文件:")
            for issue in self.issues['large_functions']:
                print(f"  文件: {issue['file']} ({issue['lines']} 行)")
                print(f"  建议: {issue['recommendation']}")
                print()
        
        # 性能问题
        if self.issues['performance_issues']:
            print("\n⚡ 性能优化机会:")
            for issue in self.issues['performance_issues']:
                if 'pattern' in issue:
                    print(f"  文件: {issue['file']}")
                    print(f"  问题: {issue['matches']} 个匹配")
                    print(f"  建议: {issue['suggestion']}")
                else:
                    print(f"  文件: {issue['file']} ({issue.get('size', 'N/A')})")
                    print(f"  建议: {issue['suggestion']}")
                print()
        
        # 重复逻辑
        if self.issues['duplicate_logic']:
            print("\n🔄 重复逻辑:")
            for issue in self.issues['duplicate_logic']:
                print(f"  文件: {issue['file']}")
                print(f"  重复函数: {issue['functions']}")
                print(f"  建议: {issue['recommendation']}")
                print()
        
        # 优化机会
        if self.issues['optimization_opportunities']:
            print("\n🎯 优化机会:")
            for issue in self.issues['optimization_opportunities']:
                print(f"  类型: {issue['type']}")
                print(f"  建议: {issue['recommendation']}")
                if 'common_resources' in issue:
                    print("  公共资源:")
                    for resource, files in list(issue['common_resources'].items())[:3]:
                        print(f"    {resource}: 被 {len(files)} 个文件使用")
                print()
        
        # 总结
        total_issues = sum(len(issues) for issues in self.issues.values())
        print(f"\n📊 优化总结:")
        print(f"  发现问题总数: {total_issues}")
        print(f"  重复文件: {len(self.issues['duplicate_files'])}")
        print(f"  冗余代码: {len(self.issues['redundant_code'])}")
        print(f"  性能问题: {len(self.issues['performance_issues'])}")
        print(f"  大文件: {len(self.issues['large_functions'])}")
        print()
        
        # 优先级建议
        print("🎯 优化优先级建议:")
        print("1. 高优先级: 删除明显的备份文件")
        print("2. 中优先级: 优化大文件和性能问题")
        print("3. 低优先级: 重构重复逻辑")

def main():
    analyzer = CodeOptimizationAnalyzer()
    analyzer.analyze_project()

if __name__ == "__main__":
    main()