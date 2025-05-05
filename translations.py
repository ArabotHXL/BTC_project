"""
系统中英文翻译文件
Bilingual translations for the system (Chinese-English)
"""

# 翻译字典，键名为英文，值为中文
# Translation dictionary, keys are English, values are Chinese
translations = {
    # 通用元素 / Common elements
    "language": "语言",
    "english": "英文",
    "chinese": "中文",
    "submit": "提交",
    "cancel": "取消",
    "save": "保存",
    "back": "返回",
    "logout": "退出登录",
    "success": "成功",
    "error": "错误",
    "warning": "警告",
    "info": "信息",
    
    # 登录页面 / Login page
    "login": "登录",
    "login_title": "登录 - BTC挖矿计算器",
    "email_verification_login": "邮箱验证登录",
    "email_address": "邮箱地址",
    "enter_authorized_email": "请输入授权邮箱",
    "use_authorized_email": "请使用已获授权的邮箱地址登录。",
    "login_success": "登录成功！欢迎使用BTC挖矿计算器",
    "login_failed": "登录失败！您没有访问权限",
    "you_logged_out": "您已成功退出登录",
    
    # 主页面 / Main page
    "btc_mining_calculator": "BTC挖矿计算器",
    "bitcoin_mining_profitability_calculator": "比特币挖矿收益计算器",
    "btc_price": "BTC价格",
    "difficulty": "难度",
    "network_hashrate": "网络算力",
    "block_reward": "区块奖励",
    "network_and_mining_details": "网络和挖矿详情",
    "bitcoin_network_information": "比特币网络信息",
    "mining_site_information": "挖矿场信息",
    "btc_output_algorithms": "BTC产出算法",
    "profitability_heatmap": "收益热力图",
    "refresh_chart": "刷新图表",
    "generate_chart": "生成热力图",
    "daily_btc_total": "日产BTC总量",
    "by_hashrate": "按算力占比",
    "by_difficulty": "按难度公式",
    "algorithm_1": "算法1",
    "algorithm_2": "算法2",
    "total_site_hashrate": "场地总算力",
    "btc_per_th_daily": "每TH日产BTC",
    "optimal_electricity_rate": "最优电费",
    
    # 计算表单 / Calculator form
    "miner_settings": "矿机设置",
    "mining_calculator": "挖矿计算器",
    "miner_model": "矿机型号",
    "select_miner": "选择矿机",
    "hashrate": "算力",
    "power_consumption": "功耗",
    "electricity_cost": "电费成本",
    "use_real_time_data": "使用实时数据",
    "miner_count": "矿机数量",
    "site_power_mw": "矿场功率 (MW)",
    "calculate": "计算",
    "reset": "重置",
    
    # 结果部分 / Results section
    "results": "计算结果",
    "daily": "每日",
    "monthly": "每月",
    "yearly": "每年",
    "btc_mined": "挖矿产出",
    "revenue": "收入",
    "costs": "成本",
    "profit": "利润",
    "customer_information": "客户信息",
    "customer_income": "客户收入",
    "customer_expenses": "客户支出",
    "monthly_btc": "月度BTC产出",
    "monthly_btc_revenue": "月度BTC收入",
    "customer_monthly_electricity": "客户月度电费",
    "customer_monthly_profit": "客户月度收益",
    "customer_yearly_profit": "客户年度收益",
    "customer_break_even_electricity": "客户盈亏平衡电价",
    "customer_break_even_btc": "客户盈亏平衡BTC价格",
    
    # 高级设置 / Advanced settings
    "advanced_settings": "高级设置",
    "customer_electricity_cost": "客户电费",
    "curtailment": "限电比例",
    "maintenance_fee": "维护费用",
    "advanced_options": "高级选项",
    
    # 投资回报 / ROI section
    "investment": "投资",
    "host_investment": "矿场投资",
    "client_investment": "客户投资",
    "roi_analysis": "投资回报分析",
    "host_roi_analysis": "矿场主投资回报",
    "client_roi_analysis": "客户投资回报",
    "your_profit_information": "您的收益信息",
    "payback_period": "回本周期",
    "roi_percentage": "投资回报率",
    "profit_forecast": "利润预测",
    "cumulative_profit": "累计利润",
    "monthly_cash_flow": "每月现金流",
    "investment_amount": "投资金额",
    "annual_roi": "年化投资回报率",
    "payback_months": "投资回收期",
    "payback_years": "回收期",
    "host_monthly_profit": "矿场主月度收益",
    "host_income": "矿场主收入",
    "host_expenses": "矿场主支出",
    "host_electric_profit": "矿场主电费差收益",
    "host_operation_profit": "矿场主运营收益",
    "total_site_revenue": "矿场总收入",
    "total_income": "总收入",
    "monthly_electricity_cost": "月度电费",
    "operation_cost": "运维费用",
    "total_expenses": "总支出",
    
    # 管理页面 / Admin pages
    "login_records": "登录记录",
    "login_records_management": "登录记录管理",
    "user_access_management": "用户权限管理",
    "return_to_calculator": "返回计算器",
    "last_100_records": "最近100条登录记录",
    "id": "ID",
    "user_email": "用户邮箱",
    "login_time": "登录时间",
    "status": "状态",
    "ip_address": "IP地址",
    "country_region": "国家/地区",
    "location_details": "详细位置",
    "view_details": "查看详情",
    "unknown_location": "未知位置",
    
    # 用户角色 / User roles
    "owner": "拥有者",
    "admin": "管理员",
    "mining_site": "矿场管理",
    "customer": "客户",
    "guest": "访客",
    
    # 错误信息 / Error messages
    "error_fetching_network_stats": "获取网络状态失败",
    "error_fetching_miners": "获取矿机列表失败",
    "calculation_error": "计算过程中出错",
    "invalid_input": "无效的输入参数",
    "server_error": "服务器错误",
    "unauthorized": "未授权访问",
    "access_denied": "访问被拒绝",
    "session_expired": "会话已过期"
}

# 获取翻译函数，如果没有找到对应翻译，返回原文
# Function to get translation, returns original text if no translation found
def get_translation(text, to_lang='zh'):
    """
    获取文本翻译
    Get text translation
    
    :param text: 原文本 / Original text
    :param to_lang: 目标语言 'zh' 或 'en' / Target language 'zh' or 'en'
    :return: 翻译后的文本 / Translated text
    """
    if to_lang == 'en':
        # 如果目标语言是英文，查找中文对应的英文
        # If target language is English, find English for Chinese
        for en_text, zh_text in translations.items():
            if zh_text == text:
                return en_text
        # 如果没找到，返回原文
        # If not found, return original text
        return text
    elif to_lang == 'zh':
        # 如果目标语言是中文，从字典中获取翻译
        # If target language is Chinese, get translation from dictionary
        return translations.get(text, text)
    else:
        # 不支持的语言，返回原文
        # Unsupported language, return original text
        return text