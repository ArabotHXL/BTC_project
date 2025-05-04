import gspread
from google.oauth2.service_account import Credentials
import os
import subprocess
import gdown

# Step 1: 下载 JSON 文件
file_id = "1iQBMilSDK-9KiNsyHpWKTaXpSAEAQ38h"
output = "/content/apt-cycling-430123-g9-716084faf348.json"
gdown.download(f"https://drive.google.com/uc?id={file_id}", output, quiet=False)

# Step 2: 授权 Google Sheets
SERVICE_ACCOUNT_FILE = output
credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
gc = gspread.authorize(credentials)


# Step 3: 打开 Google Sheets
spreadsheet_url = 'https://docs.google.com/spreadsheets/d/15maOE_0HzWA5upDmlYAK61GPVKUrhX6NURbmQcB5N2w/edit#gid=0'
info_sheet = gc.open_by_url(spreadsheet_url).worksheet('客户信息')
token_sheet = gc.open_by_url(spreadsheet_url).worksheet('Token')

# Step 4: 验证客户身份并获取 Unique ID
def verify_access(email):
    for subscriber in info_sheet.get_all_records():
        if subscriber['Email'] == email and subscriber['Access Granted'] == '✅':
            print(f"✅ 欢迎 {subscriber['Email']}！您已获得访问权限。")
            return subscriber['Unique ID']  # 返回 Unique ID 作为密钥
    print("❌ 抱歉，您尚未获得访问权限。请联系管理员。")
    return None

# Step 5: 匹配 Unique ID 并找到 Token
def get_token_by_unique_id(unique_id):
    token_data = token_sheet.get_all_records()
    for token_entry in token_data:
        if token_entry['Unique ID'] == unique_id:
            return token_entry['Token']
    print("❌ 未找到对应的 Token，请联系管理员。")
    return None

# Step 6: 用户输入邮箱并验证
user_email = input("请输入您的邮箱: ")
user_id = verify_access(user_email)

# Step 7: 使用 Token 执行计算器
if user_id:
    GITHUB_TOKEN = get_token_by_unique_id(user_id)
    if GITHUB_TOKEN:
        # 克隆 GitHub 仓库
        repo_url = f"https://{GITHUB_TOKEN}@github.com/ArabotHXL/BTC.git"
        try:
            subprocess.run(['git', 'clone', repo_url, 'BTC_Calculator'], check=True)
            print("✅ 仓库克隆成功！")
        except subprocess.CalledProcessError as e:
            print(f"❌ 克隆失败: {e}")

        # Step 8: 执行计算器
        os.chdir('BTC_Calculator')
        try:
            exec(open("mining_profit_calculator.py").read())
            print("✅ mining_profit_calculator.py 执行完成")
        except Exception as e:
            print(f"❌ mining_profit_calculator.py 执行失败: {e}")

        # Step 9: 安全删除 Token
        # Step 9: 安全删除 Token
        if 'GITHUB_TOKEN' in os.environ:
            del os.environ['GITHUB_TOKEN']
            print("✅ Token 已安全删除，访问已完成。")
        else:
            print("⚠️ Token 未找到，可能已被删除或未正确设置。")

    #else:
        #print("❌ 未找到对应的 Token，请联系管理员。")
else:
    print("❌ 无法访问，请联系管理员。")
