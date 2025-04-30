import pandas as pd
import numpy as np
import ipywidgets as widgets
from IPython.display import display
from IPython.display import FileLink


# 固定矿机数据 (包括每种矿机的算力和功耗)
MINER_DATA = {
    "Antminer S21 XP Hyd": {"hashrate": 473, "power_watt": 5676},
    "Antminer S21 XP": {"hashrate": 270, "power_watt": 3645},
    "Antminer S21": {"hashrate": 200, "power_watt": 3500},
    "Antminer S21 Hyd": {"hashrate": 335, "power_watt": 5360},
    "Antminer S19": {"hashrate": 95, "power_watt": 3250},
    "Antminer S19 Pro": {"hashrate": 110, "power_watt": 3250},
    "Antminer S19j Pro": {"hashrate": 100, "power_watt": 3050},
    "Antminer S19 XP": {"hashrate": 140, "power_watt": 3010},
    "Antminer S19 Hydro": {"hashrate": 158, "power_watt": 5451},
    "Antminer S19 Pro+ Hyd": {"hashrate": 198, "power_watt": 5445}
}

# 获取用户输入数据
def get_user_input():
    site_power_mw_input = widgets.FloatText(description='矿场电力 (MW):')
    electricity_rate_input = widgets.BoundedFloatText(description='电价 ($/kWh):', min=0, max=10, step=0.01)
    
    miner_dropdown = widgets.Dropdown(
        options=list(MINER_DATA.keys()),
        description='矿机型号: '
    )

    client_electricity_rate_input = widgets.BoundedFloatText(
        description='客户电费 ($/kWh):',
        min=0, max=10, step=0.01
    )
    curtailment_input = widgets.BoundedFloatText(
        description='削减百分比 (%):',
        min=0, max=100, step=0.1
    )

    confirm_button = widgets.Button(description="确认/Confirm")

    display(site_power_mw_input, electricity_rate_input,
            miner_dropdown, client_electricity_rate_input, curtailment_input, confirm_button)

    data = {}

    def on_confirm_click(b):
        selected_miner = miner_dropdown.value
        data["site_power_mw"] = site_power_mw_input.value
        data["electricity_rate"] = electricity_rate_input.value
        data["hashrate"] = MINER_DATA[selected_miner]["hashrate"]
        data["power_watt"] = MINER_DATA[selected_miner]["power_watt"]
        data["client_electricity_rate"] = client_electricity_rate_input.value
        data["curtailment"] = curtailment_input.value

        print("✅ 数据已确认！正在计算中...")
        display_results(data)

    confirm_button.on_click(on_confirm_click)



# 计算和显示结果
import requests

# 获取实时信息
def get_real_time_btc_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
        response.raise_for_status()  # 新增检查API响应状态
        data = response.json()
        return float(data['bitcoin']['usd'])
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 无法获取实时BTC价格，使用默认值 70000 USD: {e}")
        return 80000

def get_real_time_btc_hashrate():
    try:
        response = requests.get('https://blockchain.info/q/hashrate')
        if response.status_code == 200:
            hashrate_th = float(response.text.strip())  # 原始数据为 TH/s
            return hashrate_th / 1e9  # 转换为 EH/s
        else:
            raise Exception("API 响应异常")
    except Exception as e:
        print(f"⚠️ 无法获取实时BTC算力，使用默认值 700 EH/s: {e}")
        return 700


# 获取实时 BTC 难度
def get_real_time_difficulty():
    try:
        response = requests.get('https://blockchain.info/q/getdifficulty')
        if response.status_code == 200:
            difficulty = float(response.text.strip())
            return difficulty
        else:
            raise Exception("API 响应异常")
    except Exception as e:
        print(f"⚠️ 无法获取实时 BTC 难度，使用默认值 56T: {e}")
        return 56000000000000  # 默认值约为 56T


# 获取实时 Block Reward (区块奖励) via blockchain.info
def get_real_time_block_reward():
    try:
        response = requests.get('https://blockchain.info/q/getblockcount')
        if response.status_code == 200:
            block_height = int(response.text.strip())  # 获取当前区块高度
            if block_height >= 840000:
                block_reward = 3.125
            elif block_height >= 630000:
                block_reward = 6.25
            elif block_height >= 420000:
                block_reward = 12.5
            elif block_height >= 210000:
                block_reward = 25.0
            else:
                block_reward = 50.0
            return block_reward
        else:
            raise Exception("API 响应异常")
    except Exception as e:
        print(f"⚠️ 无法获取实时 Block Reward，使用默认值 3.125 BTC: {e}")
        return 3.125


def display_results(input_values):
    import matplotlib.pyplot as plt

    # === 数据获取 ===
    blocks_per_day = 144
    real_time_btc_price = get_real_time_btc_price()
    difficulty = get_real_time_difficulty() / 1e12  # 转换为 T
    real_time_btc_hashrate = get_real_time_btc_hashrate() or 700  # 默认值 700 EH/s
    block_reward = get_real_time_block_reward()

    # === 矿机数量 & 总算力计算 ===
    network_TH = real_time_btc_hashrate * 1e6
    site_miner_count = int((input_values['site_power_mw'] * 1000) / (input_values['power_watt'] / 1000))
    curtailment_factor = max(0, min(1, (100 - input_values['curtailment']) / 100))
    site_total_hashrate = site_miner_count * input_values['hashrate'] * curtailment_factor

    # === BTC 产出计算 ===
    btc_per_th = (block_reward * blocks_per_day) / network_TH
    site_daily_btc_output = site_total_hashrate * btc_per_th
    site_monthly_btc_output = site_daily_btc_output * 30.5
    daily_btc_per_miner = btc_per_th * input_values['hashrate']


    # === 方法二：按难度公式估算 BTC 产出 ===
    site_total_hashrate_Hs = site_total_hashrate * 1e12  # TH/s → H/s
    difficulty_raw = get_real_time_difficulty()  # 直接返回的值是原始 Difficulty
    difficulty_factor = 2 ** 32

    site_daily_btc_output_difficulty = (site_total_hashrate_Hs * block_reward * 86400) / (difficulty_raw * difficulty_factor)
    site_monthly_btc_output_difficulty = site_daily_btc_output_difficulty * 30.5

    # === 成本计算 ===
    monthly_power_consumption = site_miner_count * (input_values['power_watt'] / 1000) * 24 * 30.5
    electricity_cost = monthly_power_consumption * input_values['electricity_rate']
    client_electricity_cost = monthly_power_consumption * input_values['client_electricity_rate']

    # === 最优电价 (Optimal Electricity Rate) 计算 ===
    client_rate_range = np.around(np.linspace(0.02, 0.10, 5), 2)

    optimal_electricity_rate = (site_monthly_btc_output * real_time_btc_price) / monthly_power_consumption
    print(f"\n💡 最优电价 (Optimal Electricity Rate): ${optimal_electricity_rate:.4f}/kWh")
    optimal_electricity_rate_index = np.argmin(np.abs(client_rate_range - optimal_electricity_rate))

    # === 最优削减比例 (Optimal Curtailment) 计算 ===
    if input_values['electricity_rate'] > optimal_electricity_rate:
        optimal_curtailment = max(0, min(100, 100 * (1 - (optimal_electricity_rate / input_values['electricity_rate']))))
        print(f"🔻 最优削减比例 (Optimal Curtailment): {optimal_curtailment:.2f}%")
    else:
        optimal_curtailment = 0
        print(f"✅ 当前电价已为最优，无需削减。")

    # === 关机矿机数量 ===
    shutdown_miner_count = int(site_miner_count * (input_values['curtailment'] / 100))

    # === 数据输出 ===
    print(f"🟢 当前 BTC 价格: ${real_time_btc_price}")
    print(f"🟠 当前 Bitcoin Difficulty: {difficulty:.2f} T")
    print(f"🟣 当前 BTC 算力: {real_time_btc_hashrate:.2f} EH/s")
    print(f"🟡 当前 Block Reward: {block_reward:.3f} BTC")
    print(f"🔻 电力削减比例: {input_values['curtailment']}%")
    print(f"⚡ 削减后的每日BTC产出: {site_daily_btc_output:.8f} BTC")
    print(f"⚡ 削减后的每月BTC产出: {site_monthly_btc_output:.8f} BTC")
    print(f"💡 削减后的月电费支出 ($): ${electricity_cost:.2f}")
    print(f"💰 削减后的月收益 ($): ${site_monthly_btc_output * real_time_btc_price - electricity_cost:.2f}")
    print(f"⛔ 需关机矿机数量: {shutdown_miner_count}")
    print(f"✅ 运行中的矿机数量: {site_miner_count - shutdown_miner_count}")

    # === 额外收益分析 ===
    btc_price_range = np.linspace(real_time_btc_price * 0.8, real_time_btc_price * 1.2, 10)
    client_rate_range = np.around(np.linspace(0.02, 0.10, 5), 2)

    dynamic_profits = []
    for btc_price in btc_price_range:
        for client_rate in client_rate_range:
            dynamic_profit = site_monthly_btc_output * btc_price - (
                site_miner_count * (input_values['power_watt'] / 1000) * 24 * client_rate * 30.5
            )

            dynamic_profits.append({
                'BTC_Price': btc_price,
                'Client_electricity_cost($/kWh)': client_rate,
                'Client_Dynamic_Profit($)': dynamic_profit
            })

    dynamic_data = pd.DataFrame(dynamic_profits)
    pivot_data = dynamic_data.pivot(index='BTC_Price', 
                                columns='Client_electricity_cost($/kWh)', 
                                values='Client_Dynamic_Profit($)')


    # === 动态收益图表可视化 (优化版) ===
    plt.figure(figsize=(10, 6)) 
    plt.imshow(pivot_data, cmap='viridis', aspect='auto', origin='lower')
    plt.colorbar(label='Client Dynamic Profit ($)')

    # 标题
    plt.title(f"Client Dynamic Profit Analysis (BTC Price: ${real_time_btc_price:.2f})")

    # 难度 & 区块奖励
    plt.text(0.01, 0.98, f'Difficulty: {difficulty:.2f} T', 
            horizontalalignment='left', 
            verticalalignment='center',
            transform=plt.gca().transAxes,
            fontsize=10, color='orange', bbox=dict(facecolor='black', alpha=0.7))

    plt.text(0.99, 0.94, f'Block Reward: {block_reward:.3f} BTC', 
            horizontalalignment='right', 
            verticalalignment='center',
            transform=plt.gca().transAxes,
            fontsize=10, color='yellow', bbox=dict(facecolor='black', alpha=0.7))

    # 坐标标签
    plt.xlabel("Client Electricity Cost ($/kWh)")
    plt.xticks(np.arange(len(client_rate_range)), [f"${x:.2f}" for x in client_rate_range])
    plt.ylabel("BTC Price ($)")
    plt.yticks(np.arange(len(btc_price_range)), [f"${y:.2f}" for y in btc_price_range])

    # 电费 & BTC 价格标注
    btc_price_index = np.argmin(np.abs(btc_price_range - real_time_btc_price))
    client_rate_index = np.argmin(np.abs(client_rate_range - input_values['client_electricity_rate']))

    plt.axvline(x=client_rate_index, color='blue', linestyle='--')
    plt.text(client_rate_index, 0.5, f'Electricity: ${input_values["client_electricity_rate"]:.2f}/kWh',
            color='blue', fontsize=10, ha='right')

    plt.text(0.5, 0.02, f'Curtailment: {input_values["curtailment"]:.1f}%', 
            horizontalalignment='left', 
            verticalalignment='bottom',
            transform=plt.gca().transAxes,
            fontsize=10, color='cyan', bbox=dict(facecolor='black', alpha=0.7))

    #plt.axhline(y=btc_price_index, color='red', linestyle='--')
    #plt.text(0, btc_price_index + 0.5, f'BTC: ${real_time_btc_price:.2f}', color='red', fontsize=10, va='bottom')

    # ✅ 标注最优电价和BTC价格
    plt.axvline(x=optimal_electricity_rate_index, color='lime', linestyle='--', linewidth=2, label=f'Optimal Electricity Rate: ${optimal_electricity_rate:.4f}/kWh')
    plt.axhline(y=btc_price_index, color='cyan', linestyle='--', linewidth=2, label=f'BTC Price: ${real_time_btc_price:.2f}')

    # ✅ 标注最优电价 & 最优削减比例 (优化版)
    plt.annotate(f'Optimal Electricity Rate (${optimal_electricity_rate:.4f})\nOptimal Curtailment: {optimal_curtailment:.2f}%',
                xy=(optimal_electricity_rate_index, btc_price_index),
                xytext=(optimal_electricity_rate_index + 1, btc_price_index - 3),  # 位置优化
                arrowprops=dict(facecolor='white', arrowstyle='->', linewidth=1.5),
                fontsize=10, color='white', bbox=dict(facecolor='black', alpha=0.7))

    # 客户收益
    client_profit = site_monthly_btc_output * real_time_btc_price - client_electricity_cost
    plt.text(client_rate_index + 0.5, btc_price_index + 0.5, f'Profit: ${client_profit:.2f}',
            color='green', fontsize=10, ha='center', va='center', bbox=dict(facecolor='white', alpha=0.6))

    plt.legend(loc='lower left', fontsize=8, facecolor='white', edgecolor='white', framealpha=0.8)
    plt.show()


    # 输出最优值信息
    print(f"\n💡 最优电价 (Optimal Electricity Rate): ${optimal_electricity_rate:.4f}/kWh")
    print(f"🟠 最优削减比例 (Optimal Curtailment): {optimal_curtailment:.2f}%")




#客户成本与矿场成本
    print("\n### 成本与净收益 ###")
    print(f"电费支出 ($月): ${electricity_cost:.2f}")
    print(f"客户电费 ($月): ${client_electricity_cost:.2f}")
    net_profit = site_monthly_btc_output * real_time_btc_price - electricity_cost
    print(f"月净收益 ($): ${net_profit:.2f}")


# === 详细数据输出 ===
    # 客户和矿场收益分析
    real_time_btc_price = get_real_time_btc_price() or input_values.get('btc_price', 80000)
    print(f"🟢 当前 BTC 价格: ${real_time_btc_price:.2f}")

    btc_price_range = np.linspace(real_time_btc_price * 0.8, real_time_btc_price * 1.2, 10)
  
    site_profit = client_electricity_cost - electricity_cost
    print(f"🏭 矿场收益: ${site_profit:.2f}")

    client_specific_profit = site_monthly_btc_output * real_time_btc_price - client_electricity_cost
    print(f"📈 客户在当前 BTC 价格 (${real_time_btc_price}) 时的收益: ${client_specific_profit:.2f}")

    # 客户无收益的 BTC 价格 (Break-Even)
    client_break_even_price = client_electricity_cost / site_monthly_btc_output
    print(f"⛔ 客户无收益 BTC 价格 (Break-Even Price): ${client_break_even_price:.2f}")
  
  # 盈亏平衡电费
    monthly_power_consumption = site_miner_count * (input_values['power_watt'] / 1000) * 24 * 30.5
    break_even_electricity_rate = (site_monthly_btc_output * real_time_btc_price) / (monthly_power_consumption * curtailment_factor)
    print(f"⚡ 在当前 BTC 价格 (${real_time_btc_price}) 下的盈亏平衡电费 (USD/kWh): ${break_even_electricity_rate:.4f}")
  
# === 详细数据输出 ===
    print("\n### 矿场产出数据 ###")
    print(f"每TH/每日BTC产出: {btc_per_th:.8f} BTC")
    print(f"每台矿机算力 (TH): {input_values['hashrate']} TH")
    print(f"每日/每台矿机产出 (BTC): {daily_btc_per_miner:.8f} BTC")

    print("\n### 收益计算 ###")
    print(f"场地矿机数量: {site_miner_count}")
    print(f"矿场总算力 (TH/s): {site_total_hashrate}")
    print(f"每日BTC产出: {site_daily_btc_output:.8f} BTC")
    print(f"每月BTC产出: {site_monthly_btc_output:.8f} BTC")
    print(f"日收益 ($): ${site_daily_btc_output * real_time_btc_price:.2f}")
    print(f"月收益 ($): ${site_monthly_btc_output * real_time_btc_price:.2f}")

    print("\n📊 两种算法对比：")
    print(f"🔢 方法一（按算力占比）：每月 BTC ≈ {site_monthly_btc_output:.6f}")
    print(f"🧮 方法二（按难度公式）：每月 BTC ≈ {site_monthly_btc_output_difficulty:.6f}")

    # === 封装汇总数据并调用报告导出函数 ===
    report_data = {
        "btc_price": real_time_btc_price,
        "network_hashrate": f"{real_time_btc_hashrate:.2f} EH/s",
        "difficulty": f"{difficulty:.2f} T",
        "block_reward": block_reward,
        "miner_model": [k for k, v in MINER_DATA.items() if v["hashrate"] == input_values["hashrate"]][0],
        "miner_count": site_miner_count,
        "total_th": site_total_hashrate,
        "btc_day": site_daily_btc_output,
        "btc_month": site_monthly_btc_output,
        "btc_month_difficulty": site_monthly_btc_output_difficulty,
        "revenue_day": site_daily_btc_output * real_time_btc_price,
        "revenue_month": site_monthly_btc_output * real_time_btc_price,
        "electricity_cost": electricity_cost,
        "client_profit": client_specific_profit,
        "site_profit": site_profit,
        "pivot_data": pivot_data
    }

    generate_summary_report(report_data)

def generate_summary_report(data: dict):
    from IPython.display import display
    import pandas as pd

    with pd.ExcelWriter("矿场运营分析.xlsx") as writer:
        pd.DataFrame({
            "参数": ["BTC 价格", "网络算力", "难度", "区块奖励", "矿机型号", "矿机数量", "总算力 (TH)"],
            "数值": [data["btc_price"], data["network_hashrate"], data["difficulty"],
                    data["block_reward"], data["miner_model"], data["miner_count"], data["total_th"]]
        }).to_excel(writer, sheet_name="概况", index=False)

        pd.DataFrame({
            "项目": ["每日产出 (BTC)", "每月产出 (BTC)", "日收益 ($)", "月收益 ($)",
                    "电费 ($)", "客户收益 ($)", "矿场利润 ($)"],
            "数值": [data["btc_day"], data["btc_month"], data["revenue_day"], data["revenue_month"],
                    data["electricity_cost"], data["client_profit"], data["site_profit"]]
        }).to_excel(writer, sheet_name="收益成本", index=False)

        pd.DataFrame({
            "算法": ["方法一（算力占比）", "方法二（难度公式）"],
            "月产出 (BTC)": [data["btc_month"], data["btc_month_difficulty"]]
        }).to_excel(writer, sheet_name="算法对比", index=False)

        data["pivot_data"].to_excel(writer, sheet_name="动态收益热图")

    print("📁 已成功导出：矿场运营分析.xlsx")
    
    try:
        from google.colab import files
        files.download("矿场运营分析.xlsx")
    except Exception as e:
        print(f"⚠️ 下载失败：{e}")

if __name__ == "__main__":
    try:
        import google.colab
        get_user_input()
    except ImportError:
        print("请在 Google Colab 中运行以使用可视化控件。")
