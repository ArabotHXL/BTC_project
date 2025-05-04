# GitHub 上传指南

以下是将代码上传到GitHub的详细步骤：

## 1. 准备工作

### 下载代码包
首先，从Replit下载生成的zip文件 `btc_mining_calculator_20250504_065223.zip`。

### 安装Git
确保你的电脑上已安装Git。如果没有，请从[Git官网](https://git-scm.com/downloads)下载并安装。

### 创建GitHub账户
如果你还没有GitHub账户，请在[GitHub](https://github.com/)上注册一个。

## 2. 在GitHub上创建新仓库

1. 登录GitHub账户
2. 点击右上角"+"图标，选择"New repository"
3. 输入仓库名称，例如"btc-mining-calculator"
4. 添加描述（可选）
5. 选择仓库可见性（公开或私有）
6. 不要勾选"Initialize this repository with a README"
7. 点击"Create repository"

## 3. 上传代码到GitHub

### 方法1：使用命令行（推荐）

1. 解压下载的zip文件到一个新文件夹
2. 打开命令行终端，进入该文件夹：
   ```bash
   cd 路径/到/解压后的文件夹
   ```

3. 初始化Git仓库：
   ```bash
   git init
   ```

4. 添加远程仓库地址（替换URL为你的GitHub仓库地址）：
   ```bash
   git remote add origin https://github.com/你的用户名/btc-mining-calculator.git
   ```

5. 添加所有文件到暂存区：
   ```bash
   git add .
   ```

6. 提交更改：
   ```bash
   git commit -m "初始提交：完整的BTC挖矿计算器项目"
   ```

7. 推送代码到GitHub：
   ```bash
   git push -u origin master
   # 或者如果默认分支是main：
   git push -u origin main
   ```

### 方法2：直接在GitHub网页上传

对于小型项目，也可以直接在GitHub网页上传文件：

1. 进入你刚创建的GitHub仓库页面
2. 点击"Add file" > "Upload files"
3. 拖放解压后的文件到上传区域，或点击"choose your files"选择文件
4. 添加提交信息
5. 点击"Commit changes"

## 4. 验证上传

上传完成后，刷新GitHub仓库页面，确认所有文件都已成功上传。README.md内容应该显示在仓库主页。

## 5. 后续维护

如果你需要继续更新代码，可以：

1. 本地修改代码
2. 添加修改的文件：`git add 修改的文件`
3. 提交更改：`git commit -m "更新说明"`
4. 推送到GitHub：`git push`

## 注意事项

- 确保已添加.gitignore文件，避免上传不必要的文件
- 不要上传任何包含敏感信息的文件（如API密钥、数据库密码等）
- 定期更新仓库，保持代码同步