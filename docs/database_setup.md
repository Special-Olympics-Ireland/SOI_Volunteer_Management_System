# PostgreSQL Database Setup for SOI Hub

This document provides instructions for setting up PostgreSQL database for the ISG 2026 Volunteer Management Backend System.

## Prerequisites

- Ubuntu Server (tested on Ubuntu 20.04+)
- sudo access for PostgreSQL installation
- Python 3.12+ with Django

## Quick Setup

Run the automated setup script:

```bash
cd soi-hub
./scripts/setup_database.sh
```

This script will:
1. Install PostgreSQL if not already installed
2. Start and enable PostgreSQL service
3. Create database user and database
4. Set up required extensions
5. Configure proper permissions

## Manual Setup

If you prefer to set up the database manually:

### 1. Install PostgreSQL

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

### 2. Start PostgreSQL Service

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. Create Database and User

```bash
sudo -u postgres psql -f scripts/setup_database.sql
```

## Database Configuration

The default configuration uses:

- **Database Name**: `soi_hub_db`
- **Username**: `soi_user`
- **Password**: `soi_password`
- **Host**: `localhost`
- **Port**: `5432`

### Environment Variables

Configure these in your `.env` file:

```env
DB_NAME=soi_hub_db
DB_USER=soi_user
DB_PASSWORD=soi_password
DB_HOST=localhost
DB_PORT=5432
```

## JSON Field Support

PostgreSQL 12+ provides native JSON support. The setup includes:

- **JSON and JSONB data types** for flexible configuration storage
- **GIN indexes** for efficient JSON queries
- **JSON operators** for complex data manipulation

### Example JSON Field Usage

```python
# In Django models
from django.contrib.postgres.fields import JSONField

class Event(models.Model):
    configuration = JSONField(default=dict)
    
class Role(models.Model):
    requirements = JSONField(default=dict)
    
class VolunteerProfile(models.Model):
    preferences = JSONField(default=dict)
```

## Extensions Enabled

The database setup includes these PostgreSQL extensions:

1. **uuid-ossp**: UUID generation functions
2. **pg_trgm**: Trigram matching for text search
3. **unaccent**: Remove accents from text for better search

## Performance Optimization

### Indexes for JSON Fields

```sql
-- Example indexes for JSON fields
CREATE INDEX idx_event_config_gin ON events_event USING GIN (configuration);
CREATE INDEX idx_role_requirements_gin ON events_role USING GIN (requirements);
CREATE INDEX idx_volunteer_preferences_gin ON volunteers_volunteerprofile USING GIN (preferences);
```

### Connection Pooling

For production, consider using connection pooling:

```python
# In settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'soi_hub_db',
        'USER': 'soi_user',
        'PASSWORD': 'soi_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        },
    }
}
```

## Backup and Recovery

### Create Backup

```bash
pg_dump -U soi_user -h localhost soi_hub_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Backup

```bash
psql -U soi_user -h localhost soi_hub_db < backup_file.sql
```

## Security Considerations

1. **Change default passwords** in production
2. **Use SSL connections** for remote access
3. **Limit database user privileges** to minimum required
4. **Regular security updates** for PostgreSQL
5. **Network access restrictions** via pg_hba.conf

## Troubleshooting

### Common Issues

1. **Connection refused**: Check if PostgreSQL service is running
   ```bash
   sudo systemctl status postgresql
   ```

2. **Authentication failed**: Verify username and password
   ```bash
   psql -U soi_user -d soi_hub_db -h localhost
   ```

3. **Permission denied**: Check database user privileges
   ```sql
   \du soi_user
   ```

### Log Files

PostgreSQL logs are typically located at:
- Ubuntu: `/var/log/postgresql/postgresql-*.log`

## Django Integration

After database setup, run Django migrations:

```bash
cd soi-hub
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## Production Deployment

For production on server 195.7.35.202:

1. **Update firewall rules** to allow PostgreSQL connections
2. **Configure SSL certificates** for secure connections
3. **Set up automated backups** with cron jobs
4. **Monitor database performance** with appropriate tools
5. **Use environment-specific passwords** and credentials

## Testing Database Connection

Test the database connection:

```python
# test_db_connection.py
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soi_hub.settings')
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL connection successful!")
        print(f"Version: {version}")
except Exception as e:
    print(f"Database connection failed: {e}")
```

Run with:
```bash
python test_db_connection.py
``` 