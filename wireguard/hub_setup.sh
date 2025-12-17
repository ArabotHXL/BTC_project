#!/bin/bash
# HashInsight Enterprise - WireGuard Hub Setup Script
# WireGuard云端Hub自动安装脚本

set -e

echo "=== HashInsight WireGuard Hub Setup ==="
echo "Starting WireGuard server installation..."

# 检查系统
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# 更新系统
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# 安装WireGuard
echo "Installing WireGuard..."
apt-get install -y wireguard wireguard-tools

# 配置IP转发
echo "Configuring IP forwarding..."
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
sysctl -p

# 生成服务器密钥对
echo "Generating server keys..."
cd /etc/wireguard
umask 077
wg genkey | tee privatekey | wg pubkey > publickey

PRIVATE_KEY=$(cat privatekey)
PUBLIC_KEY=$(cat publickey)

# 创建WireGuard配置
echo "Creating WireGuard configuration..."
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = $PRIVATE_KEY
PostUp = ufw route allow in on wg0 out on eth0
PostUp = iptables -t nat -I POSTROUTING -o eth0 -j MASQUERADE
PreDown = ufw route delete allow in on wg0 out on eth0
PreDown = iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Site peers will be added here dynamically
EOF

# 配置防火墙
echo "Configuring firewall..."
ufw allow 51820/udp
ufw allow OpenSSH
ufw --force enable

# 启动WireGuard
echo "Starting WireGuard service..."
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# 显示服务器信息
echo ""
echo "=== WireGuard Hub Setup Complete ==="
echo "Server Public Key: $PUBLIC_KEY"
echo "Server Endpoint: $(curl -s ifconfig.me):51820"
echo "Virtual Network: 10.8.0.0/24"
echo ""
echo "Status:"
wg show

echo ""
echo "Next steps:"
echo "1. Use key_manager.py to generate client keys"
echo "2. Add peers to /etc/wireguard/wg0.conf"
echo "3. Reload: wg-quick down wg0 && wg-quick up wg0"
