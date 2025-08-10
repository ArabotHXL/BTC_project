#!/usr/bin/env python3
"""
BTC Mining Algorithm Verification Script
用于验证批量计算器算法的准确性
"""

def verify_mining_calculation():
    """验证Antminer S21的挖矿计算准确性"""
    
    # 输入参数（来自实际计算）
    btc_price = 118500  # USD
    hashrate_th = 200  # TH/s (Antminer S21)
    network_hashrate_eh = 952  # EH/s
    power_kw = 3.55  # kW
    electricity_cost = 0.045  # USD/kWh
    block_reward = 3.125  # BTC
    blocks_per_day = 144
    
    print("=== Antminer S21 算法验证 ===")
    print(f"BTC价格: ${btc_price:,}")
    print(f"矿机算力: {hashrate_th} TH/s")
    print(f"网络算力: {network_hashrate_eh} EH/s")
    print(f"功耗: {power_kw} kW")
    print(f"电价: ${electricity_cost}/kWh")
    print()
    
    # 算法1：基于网络算力比例（正确版本）
    # 按照系统实际算法：全网TH = 全网EH * 1,000,000（不是1000）
    network_hashrate_th = network_hashrate_eh * 1000000  # EH/s转换为TH/s (1 EH = 1,000,000 TH)
    # 全网日产出 = 区块奖励 * 每日区块数
    network_daily_btc = block_reward * blocks_per_day
    # 每TH每日产出 = 全网日产出 / 全网TH
    btc_per_th = network_daily_btc / network_hashrate_th
    # 矿机每日产出 = 矿机TH * 每TH产出
    daily_btc_mined = hashrate_th * btc_per_th
    
    print("--- 算法1：基于网络算力比例（正确版本）---")
    print(f"个人算力: {hashrate_th} TH/s")
    print(f"网络算力: {network_hashrate_th:,.0f} TH/s")
    print(f"每TH每日产出: {btc_per_th:.12f} BTC")
    print(f"全网每日BTC: {network_daily_btc} BTC")
    print(f"每日BTC挖矿: {daily_btc_mined:.8f} BTC")
    print()
    
    # 算法2：基于难度计算
    # 使用标准难度公式: target = difficulty_1_target / current_difficulty
    # 其中 difficulty_1_target = 0x00000000ffff0000000000000000000000000000000000000000000000000000
    difficulty_raw = 129435235580345.0  # 当前难度
    hashrate_hs = hashrate_th * 1e12  # 转换为H/s
    difficulty_factor = 2 ** 32
    daily_btc_difficulty = (hashrate_hs * block_reward * 86400) / (difficulty_raw * difficulty_factor)
    
    print("--- 算法2：基于难度计算 ---")
    print(f"当前难度: {difficulty_raw:,.0f}")
    print(f"矿机算力: {hashrate_hs:.0f} H/s")
    print(f"每日BTC挖矿: {daily_btc_difficulty:.8f} BTC")
    print()
    
    # 收益和成本计算
    daily_revenue_algo1 = daily_btc_mined * btc_price
    daily_revenue_algo2 = daily_btc_difficulty * btc_price
    daily_cost = power_kw * 24 * electricity_cost
    
    daily_profit_algo1 = daily_revenue_algo1 - daily_cost
    daily_profit_algo2 = daily_revenue_algo2 - daily_cost
    
    print("--- 收益对比 ---")
    print(f"算法1 每日收益: ${daily_revenue_algo1:.2f}")
    print(f"算法2 每日收益: ${daily_revenue_algo2:.2f}")
    print(f"每日电费成本: ${daily_cost:.2f}")
    print(f"算法1 每日利润: ${daily_profit_algo1:.2f}")
    print(f"算法2 每日利润: ${daily_profit_algo2:.2f}")
    print()
    
    # 月度数据
    monthly_profit_algo1 = daily_profit_algo1 * 30
    monthly_profit_algo2 = daily_profit_algo2 * 30
    
    print("--- 月度收益 ---")
    print(f"算法1 月利润: ${monthly_profit_algo1:.2f}")
    print(f"算法2 月利润: ${monthly_profit_algo2:.2f}")
    print()
    
    # 与系统计算结果对比
    system_daily_profit = 7.52  # 来自系统计算
    system_daily_revenue = 11.36
    system_monthly_profit = 225.66
    
    print("--- 与系统结果对比 ---")
    print(f"系统计算 每日收益: ${system_daily_revenue:.2f}")
    print(f"系统计算 每日利润: ${system_daily_profit:.2f}")
    print(f"系统计算 月利润: ${system_monthly_profit:.2f}")
    print()
    
    # 准确性分析
    algo1_accuracy = abs(daily_profit_algo1 - system_daily_profit) / system_daily_profit * 100
    algo2_accuracy = abs(daily_profit_algo2 - system_daily_profit) / system_daily_profit * 100
    
    print("--- 准确性分析 ---")
    print(f"算法1 与系统差异: {algo1_accuracy:.2f}%")
    print(f"算法2 与系统差异: {algo2_accuracy:.2f}%")
    
    if algo1_accuracy < 5 and algo2_accuracy < 5:
        print("✅ 算法准确性验证通过：差异<5%")
    elif algo1_accuracy < 10 and algo2_accuracy < 10:
        print("⚠️ 算法基本准确：差异<10%，可接受范围")
    else:
        print("❌ 算法存在较大偏差：需要检查计算逻辑")
    
    return {
        'algo1_accuracy': algo1_accuracy,
        'algo2_accuracy': algo2_accuracy,
        'system_result': system_daily_profit,
        'manual_algo1': daily_profit_algo1,
        'manual_algo2': daily_profit_algo2
    }

if __name__ == "__main__":
    result = verify_mining_calculation()
    print(f"\n验证完成！算法准确性: {min(result['algo1_accuracy'], result['algo2_accuracy']):.2f}%差异")