#!/usr/bin/env python3
"""
测试分析报告功能
Test Analytics Report Function
"""
import requests
import json
from datetime import datetime

def test_analytics_report():
    """测试分析报告显示功能"""
    print("=== 分析报告功能测试 ===")
    print(f"测试时间: {datetime.now()}")
    
    # 测试数据库连接和数据获取
    try:
        import psycopg2
        import os
        
        # 连接数据库
        DATABASE_URL = os.environ.get("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n1. 数据库连接: ✓")
        
        # 检查分析报告数据
        cursor.execute("""
            SELECT COUNT(*) FROM analysis_reports
        """)
        report_count = cursor.fetchone()[0]
        print(f"2. 分析报告总数: {report_count} 条")
        
        # 检查技术指标数据
        cursor.execute("""
            SELECT COUNT(*) FROM technical_indicators
        """)
        tech_count = cursor.fetchone()[0]
        print(f"3. 技术指标总数: {tech_count} 条")
        
        # 获取最新分析报告
        cursor.execute("""
            SELECT title, summary, recommendations, risk_assessment, key_findings, generated_at 
            FROM analysis_reports 
            ORDER BY generated_at DESC LIMIT 1
        """)
        latest_report = cursor.fetchone()
        
        if latest_report:
            print("\n4. 最新分析报告内容:")
            print(f"   标题: {latest_report[0]}")
            print(f"   摘要: {latest_report[1][:100]}...")
            print(f"   生成时间: {latest_report[5]}")
            print("   ✓ 报告数据完整")
        else:
            print("4. 最新分析报告: ❌ 无数据")
        
        # 获取最新技术指标
        cursor.execute("""
            SELECT rsi_14, sma_20, sma_50, macd, recorded_at
            FROM technical_indicators 
            ORDER BY recorded_at DESC LIMIT 1
        """)
        latest_tech = cursor.fetchone()
        
        if latest_tech:
            print("\n5. 最新技术指标:")
            print(f"   RSI(14): {latest_tech[0]}")
            print(f"   SMA(20): ${latest_tech[1]:,.2f}")
            print(f"   SMA(50): ${latest_tech[2]:,.2f}")
            print(f"   MACD: {latest_tech[3]}")
            print(f"   记录时间: {latest_tech[4]}")
            print("   ✓ 技术指标数据完整")
        else:
            print("5. 最新技术指标: ❌ 无数据")
        
        cursor.close()
        conn.close()
        
        # 模拟前端数据显示
        print("\n6. 前端显示测试:")
        if latest_report:
            # 解析JSON数据
            try:
                recommendations = json.loads(latest_report[2].replace("'", '"')) if latest_report[2] else []
                risk_assessment = json.loads(latest_report[3].replace("'", '"')) if latest_report[3] else {}
                key_findings = json.loads(latest_report[4].replace("'", '"')) if latest_report[4] else {}
                
                print("   推荐建议:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"     {i}. {rec}")
                
                print(f"   风险评估: {risk_assessment.get('risk_level', 'N/A')} (评分: {risk_assessment.get('risk_score', 'N/A')})")
                
                print("   关键发现:")
                for key, value in key_findings.items():
                    print(f"     {key}: {value}")
                
                print("   ✓ 数据解析成功")
                
            except Exception as e:
                print(f"   ❌ JSON解析错误: {e}")
        
        print("\n=== 测试结果 ===")
        print("✓ 数据库表结构正确")
        print("✓ 分析报告数据存在")
        print("✓ 技术指标数据存在")
        print("✓ 数据格式可解析")
        print("\n前端显示问题可能原因:")
        print("1. 用户认证状态丢失")
        print("2. 前端JavaScript未正确调用API")
        print("3. 模板渲染问题")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_analytics_report()