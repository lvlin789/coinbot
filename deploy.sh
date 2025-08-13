#!/bin/bash

echo "🚀 开始部署加密货币交易机器人..."

# Git仓库地址
GIT_REPO="https://github.com/lvlin789/coinbot.git"

# 更新系统包
echo "正在更新系统包..."
sudo apt update

# 安装Python和必要工具
echo "正在安装Python环境..."
sudo apt install -y python3 python3-pip python3-venv tmux git

# 创建项目目录
PROJECT_DIR="/home/$USER/coinone-bot"
echo "创建项目目录: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 从git仓库拉取代码
echo "从git仓库拉取代码: $GIT_REPO"
git clone $GIT_REPO .

# 创建Python虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装Python依赖
echo "安装Python依赖..."
pip install -r requirements.txt

echo "✅ 部署完成！"
echo ""
echo "📁 项目目录: $PROJECT_DIR"
echo "🐍 Python虚拟环境: $PROJECT_DIR/venv"
echo ""
echo "📝 手动启动命令:"
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python main.py balance    # 启动余额监控"
echo "  python main.py transfer   # 启动转账交易"
echo ""
echo "💡 使用tmux保持后台运行:"
echo "  tmux new-session -d -s crypto-bot"
echo "  tmux send-keys -t crypto-bot 'cd $PROJECT_DIR && source venv/bin/activate && python main.py balance' C-m"
echo ""
echo "⚠️  记得配置您的API密钥！"
