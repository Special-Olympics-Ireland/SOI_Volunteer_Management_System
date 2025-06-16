# Redis Setup and Configuration for SOI Hub

This document provides instructions for setting up Redis for caching and session management in the ISG 2026 Volunteer Management Backend System.

## Prerequisites

- Ubuntu Server (tested on Ubuntu 20.04+)
- sudo access for Redis installation
- Python 3.12+ with Django

## Quick Setup

Run the automated setup script:

```bash
cd soi-hub
./scripts/setup_redis.sh
```

This script will:
1. Install Redis if not already installed
2. Configure Redis with SOI Hub specific settings
3. Start and enable Redis service
4. Set up separate databases for caching and sessions
5. Test the Redis connection

## Manual Setup

If you prefer to set up Redis manually:

### 1. Install Redis

```bash
sudo apt update
sudo apt install -y redis-server
```

### 2. Configure Redis

Edit the Redis configuration file:

```bash
sudo nano /etc/redis/redis.conf
```

Apply these SOI Hub specific settings:

```conf
# Security
requirepass soi_redis_password_change_in_production

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Network
bind 127.0.0.1 ::1
port 6379
```

### 3. Start Redis Service

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

## Django Configuration

The Redis configuration is already set up in Django settings:

### Cache Configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://:password@127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'soi_hub',
        'TIMEOUT': 300,
    }
}
```

### Session Configuration

```python
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hour
```

## Environment Variables

Configure these in your `.env` file:

```env
# Redis Configuration
REDIS_CACHE_URL=redis://:soi_redis_password_change_in_production@127.0.0.1:6379/1
REDIS_SESSION_URL=redis://:soi_redis_password_change_in_production@127.0.0.1:6379/2
```

## Database Usage

SOI Hub uses separate Redis databases for different purposes:

- **Database 0**: Default (not used by Django)
- **Database 1**: Django caching
- **Database 2**: Session storage (future use)
- **Database 3-15**: Available for future features

## Performance Optimization

### Memory Management

Redis is configured with:
- **Max Memory**: 256MB (adjust based on server capacity)
- **Eviction Policy**: allkeys-lru (removes least recently used keys)
- **Persistence**: RDB snapshots + AOF logging

### Key Patterns

SOI Hub uses these key patterns:
- `soi_hub:cache:*` - General caching
- `soi_hub:session:*` - Session data
- `soi_hub:volunteer:*` - Volunteer-specific cache
- `soi_hub:justgo:*` - JustGo API response cache

## Monitoring and Maintenance

### Check Redis Status

```bash
sudo systemctl status redis-server
```

### Monitor Redis Performance

```bash
redis-cli -a your_password info
redis-cli -a your_password monitor
```

### View Cache Statistics

```bash
redis-cli -a your_password info stats
```

### Clear Cache

```bash
# Clear all cache (Database 1)
redis-cli -a your_password -n 1 FLUSHDB

# Clear specific pattern
redis-cli -a your_password -n 1 --scan --pattern "soi_hub:volunteer:*" | xargs redis-cli -a your_password -n 1 DEL
```

## Security Considerations

1. **Password Protection**: Always use a strong password in production
2. **Network Binding**: Redis is bound to localhost only (127.0.0.1)
3. **Firewall**: Ensure Redis port (6379) is not exposed externally
4. **Regular Updates**: Keep Redis updated with security patches

## Backup and Recovery

### Create Backup

```bash
# RDB backup (automatic based on save configuration)
sudo cp /var/lib/redis/dump.rdb /backup/redis/dump_$(date +%Y%m%d_%H%M%S).rdb

# AOF backup
sudo cp /var/lib/redis/appendonly.aof /backup/redis/appendonly_$(date +%Y%m%d_%H%M%S).aof
```

### Restore Backup

```bash
sudo systemctl stop redis-server
sudo cp /backup/redis/dump_backup.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo systemctl start redis-server
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check if Redis service is running
   ```bash
   sudo systemctl status redis-server
   sudo systemctl start redis-server
   ```

2. **Authentication Failed**: Verify password in configuration
   ```bash
   redis-cli -a your_password ping
   ```

3. **Memory Issues**: Check memory usage and adjust maxmemory
   ```bash
   redis-cli -a your_password info memory
   ```

4. **Permission Denied**: Check Redis file permissions
   ```bash
   sudo chown -R redis:redis /var/lib/redis
   ```

### Log Files

Redis logs are located at:
- **Service logs**: `/var/log/redis/redis-server.log`
- **System logs**: `sudo journalctl -u redis-server`

## Testing Redis Connection

Test the Redis connection from Django:

```python
# test_redis_connection.py
import os
import django
from django.conf import settings
from django.core.cache import cache

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

try:
    # Test cache
    cache.set('test_key', 'test_value', 30)
    value = cache.get('test_key')
    
    if value == 'test_value':
        print("Redis cache connection successful!")
        print(f"Cache backend: {settings.CACHES['default']['BACKEND']}")
    else:
        print("Redis cache test failed!")
        
except Exception as e:
    print(f"Redis connection failed: {e}")
```

Run with:
```bash
python test_redis_connection.py
```

## Production Deployment

For production on server 195.7.35.202:

1. **Update passwords** in Redis configuration and environment files
2. **Adjust memory limits** based on server capacity
3. **Set up monitoring** with appropriate alerting
4. **Configure backup automation** with cron jobs
5. **Review security settings** and network access
6. **Test failover scenarios** and recovery procedures

## Integration with SOI Hub Features

Redis supports these SOI Hub features:

- **JustGo API Response Caching**: Reduces API calls and improves performance
- **Session Management**: Secure session storage for authenticated users
- **Volunteer Data Caching**: Frequently accessed volunteer information
- **Report Caching**: Cache generated reports for faster access
- **Rate Limiting**: Track API usage and implement rate limiting 