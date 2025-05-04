#!/usr/bin/env python3
import os
import zipfile
import datetime

# 创建一个带时间戳的文件名
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
zip_filename = f"btc_mining_calculator_{timestamp}.zip"

# 要包含在zip文件中的文件列表
files_to_include = [
    "app.py",
    "auth.py",
    "db.py",
    "main.py",
    "mining_calculator.py",
    "models.py",
    "pyproject.toml",
    "requirements-local.txt",
    "local_run_guide.md"
]

# 要包含的目录
dirs_to_include = [
    "templates",
    "static"
]

print(f"正在创建 {zip_filename}...")

# 创建zip文件
with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # 添加单个文件
    for file in files_to_include:
        if os.path.exists(file):
            zipf.write(file)
            print(f"已添加: {file}")
        else:
            print(f"文件不存在，已跳过: {file}")
    
    # 添加整个目录
    for dir_name in dirs_to_include:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            for root, dirs, files in os.walk(dir_name):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path)
                    print(f"已添加: {file_path}")
            print(f"已添加目录: {dir_name}")
        else:
            print(f"目录不存在，已跳过: {dir_name}")

print(f"\n打包完成! 文件已保存为: {zip_filename}")
print(f"您现在可以下载文件 {zip_filename} 到本地。")