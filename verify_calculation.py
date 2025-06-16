#!/usr/bin/env python3
"""验证挖矿收益计算的准确性"""

# 验证单台矿机收益计算
btc_per_day = 0.00004951
btc_price = 108617
daily_revenue = btc_per_day * btc_price
power_consumption = 3645  # W
electricity_cost = 0.06  # $/kWh
daily_electricity = (power_consumption * 24) / 1000 * electricity_cost
daily_profit = daily_revenue - daily_electricity

print(f'单台S21 XP矿机每日计算:')
print(f'BTC产出: {btc_per_day:.8f} BTC')
print(f'BTC价格: ${btc_price:,.2f}')
print(f'每日收入: ${daily_revenue:.2f}')
print(f'功耗: {power_consumption}W')
print(f'每日电费: ${daily_electricity:.2f}')
print(f'每日净收益: ${daily_profit:.2f}')
print(f'每月收益: ${daily_profit * 30:.2f}')
print(f'年收益: ${daily_profit * 365:.2f}')

print('\n' + '='*50)

# 验证大规模运营计算 (1097台矿机)
miner_count = 1097
total_daily_revenue = btc_per_day * miner_count * btc_price
total_daily_electricity = daily_electricity * miner_count
total_daily_profit = total_daily_revenue - total_daily_electricity

print(f'\n{miner_count}台S21 XP矿机大规模运营:')
print(f'总算力: {270 * miner_count:,} TH/s')
print(f'总功耗: {power_consumption * miner_count / 1000:,.1f} kW')
print(f'每日总收入: ${total_daily_revenue:,.2f}')
print(f'每日总电费: ${total_daily_electricity:,.2f}')
print(f'每日净收益: ${total_daily_profit:,.2f}')
print(f'每月收益: ${total_daily_profit * 30:,.2f}')
print(f'年收益: ${total_daily_profit * 365:,.2f}')

print('\n' + '='*50)
print('结论分析:')
print('1. 单台矿机收益确实很少，这是正常现象')
print('2. 挖矿需要规模化运营才能获得可观收益')
print('3. 当前BTC价格和网络难度下，小规模挖矿利润微薄')
print('4. 电费成本是影响收益的关键因素')