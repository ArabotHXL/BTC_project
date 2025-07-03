#!/usr/bin/env python3
"""
快速修复curtailment_calculator.html中的translate函数调用
"""

def fix_template():
    # 读取文件
    with open('templates/curtailment_calculator.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换映射
    replacements = {
        "{{ translate('curtailment_parameters') }}": "削减参数配置",
        "{{ translate('miner_configuration') }}": "矿机配置",
        "{{ translate('miner_model') }}": "矿机型号",
        "{{ translate('select_miner') }}": "选择矿机型号",
        "{{ translate('miner_count') }}": "矿机数量",
        "{{ translate('electricity_cost') }}": "电费成本",
        "{{ translate('curtailment_percentage') }}": "削减百分比",
        "{{ translate('shutdown_strategy') }}": "关机策略",
        "{{ translate('efficiency_based') }}": "基于效率",
        "{{ translate('random') }}": "随机",
        "{{ translate('proportional') }}": "按比例",
        "{{ translate('shutdown_strategy_description') }}": "选择关机策略",
        "{{ translate('btc_price') }}": "BTC价格",
        "{{ translate('use_real_time_data') }}": "使用实时数据",
        "{{ translate('calculate_curtailment') }}": "计算削减影响",
        "{{ translate('calculate_curtailment_impact') }}": "计算削减影响",
        "{{ translate('curtailment_results') }}": "削减影响结果",
        "{{ translate('normal_operation') }}": "正常运行",
        "{{ translate('daily_revenue') }}": "日收入",
        "{{ translate('daily_profit') }}": "日利润",
        "{{ translate('monthly_profit') }}": "月利润",
        "{{ translate('annual_profit') }}": "年利润",
        "{{ translate('curtailment_operation') }}": "削减运行",
        "{{ translate('active_miners') }}": "活跃矿机",
        "{{ translate('shutdown_miners') }}": "关机矿机",
        "{{ translate('impact_analysis') }}": "影响分析",
        "{{ translate('profit_loss') }}": "利润损失",
        "{{ translate('percentage_loss') }}": "损失百分比",
        "{{ translate('operating_miners') }}": "运行矿机",
        "{{ translate('total_miners') }}": "总矿机数",
        "{{ translate('efficiency_shutdown') }}": "效率关机",
        "{{ translate('revenue_loss') }}": "收入损失",
        "{{ translate('profit_impact') }}": "利润影响",
        "{{ translate('curtailment_analysis_results') }}": "削减分析结果",
        '{{ translate("calculating") }}': "计算中",
        '{{ translate("calculation_failed") }}': "计算失败",
        '{{ translate("request_failed") }}': "请求失败",
        "{{ translate('operation_summary') }}": "运行概况",
        "{{ translate('running_miners') }}": "运行矿机",
        "{{ translate('power_reduction') }}": "功率削减",
        "{{ translate('financial_impact') }}": "财务影响",
        "{{ translate('monthly_revenue_loss') }}": "月收入损失",
        "{{ translate('monthly_cost_savings') }}": "月成本节省",
        "{{ translate('net_monthly_impact') }}": "月净影响",
        "{{ translate('efficiency_improvement') }}": "效率提升",
    }
    
    # 执行所有替换
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # 写回文件
    with open('templates/curtailment_calculator.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("模板修复完成")

if __name__ == "__main__":
    fix_template()