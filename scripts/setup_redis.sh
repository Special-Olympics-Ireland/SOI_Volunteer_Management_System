#!/bin/bash

# SOI Hub Redis Setup Script
# This script sets up Redis for caching and session management

set -e  # Exit on any error

echo "=== SOI Hub Redis Setup ==="

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "Redis is not installed. Installing..."
    sudo apt update
    sudo apt install -y redis-server
    echo "Redis installed successfully."
fi

# Check if Redis service is running
if ! sudo systemctl is-active --quiet redis-server; then
    echo "Starting Redis service..."
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    echo "Redis service started and enabled."
fi

# Configure Redis for SOI Hub
echo "Configuring Redis for SOI Hub..."

# Create Redis configuration backup
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# Apply SOI Hub specific Redis configuration
sudo tee /etc/redis/redis.conf.soi > /dev/null << 'EOF'
# SOI Hub Redis Configuration
# Based on default Redis configuration with SOI-specific settings

# Network configuration
bind 127.0.0.1 ::1
port 6379
timeout 300
tcp-keepalive 300

# General configuration
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log

# Persistence configuration
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Security
requirepass soi_redis_password_change_in_production

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Append only file
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Client output buffer limits
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60

# SOI Hub specific databases
databases 16
EOF

# Apply the configuration
sudo cp /etc/redis/redis.conf.soi /etc/redis/redis.conf

# Restart Redis with new configuration
echo "Restarting Redis with SOI Hub configuration..."
sudo systemctl restart redis-server

# Test Redis connection
echo "Testing Redis connection..."
if redis-cli -a soi_redis_password_change_in_production ping | grep -q PONG; then
    echo "Redis connection test successful!"
else
    echo "Redis connection test failed. Please check the configuration."
    exit 1
fi

# Set up Redis for Django databases
echo "Setting up Redis databases for Django..."
redis-cli -a soi_redis_password_change_in_production << 'REDIS_COMMANDS'
SELECT 1
FLUSHDB
SET soi_hub:test "SOI Hub Cache Test"
EXPIRE soi_hub:test 60
SELECT 2
FLUSHDB
SET soi_hub:session:test "SOI Hub Session Test"
EXPIRE soi_hub:session:test 60
REDIS_COMMANDS

echo "Redis setup completed successfully!"
echo ""
echo "Redis Configuration:"
echo "  Host: 127.0.0.1"
echo "  Port: 6379"
echo "  Password: soi_redis_password_change_in_production"
echo "  Cache Database: 1"
echo "  Session Database: 2"
echo ""
echo "IMPORTANT: Change the Redis password in production!"
echo "Update your .env file with:"
echo "  REDIS_CACHE_URL=redis://:soi_redis_password_change_in_production@127.0.0.1:6379/1"
echo "  REDIS_SESSION_URL=redis://:soi_redis_password_change_in_production@127.0.0.1:6379/2" 