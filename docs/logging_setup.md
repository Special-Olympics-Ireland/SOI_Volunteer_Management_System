# SOI Hub Logging and Audit System

## Overview

The SOI Hub volunteer management system implements a comprehensive logging and audit system to track all critical operations, user actions, and system events. This is essential for compliance, security monitoring, and troubleshooting.

## Log Files Structure

The system creates several specialized log files in the `logs/` directory:

### Core Log Files

- **`django.log`** - General Django application logs (INFO level and above)
- **`audit.log`** - Audit trail for all critical user actions and data changes
- **`security.log`** - Security-related events (login attempts, permission denials, etc.)
- **`justgo.log`** - JustGo API integration logs and synchronization events

### Log Rotation

All log files use rotating file handlers with the following configuration:
- **File size limit**: 15MB (10MB for JustGo logs)
- **Backup count**: 10-20 files (more for audit and security logs)
- **Format**: Timestamped with detailed context information

## Logging Categories

### 1. Audit Logging (`soi_hub.audit`)

Tracks all critical business operations:
- User registrations and profile updates
- EOI submissions and modifications
- Volunteer assignments and role changes
- Admin actions and bulk operations
- Data exports and reports

### 2. Security Logging (`soi_hub.security`)

Monitors security-related events:
- Login/logout attempts (successful and failed)
- Permission denied events
- Admin overrides with justifications
- Suspicious activity patterns

### 3. JustGo Integration Logging (`soi_hub.justgo`)

Tracks all JustGo API interactions:
- Member profile lookups
- Credential synchronization
- API errors and rate limiting
- Data consistency checks

### 4. Application Logging

Standard Django logging for:
- Request/response cycles
- Database queries (in DEBUG mode)
- Error handling and exceptions
- Performance monitoring

## Using the Audit System

### Basic Usage

```python
from common.audit import log_audit_event, AuditEvent

# Create and log an audit event
event = AuditEvent(
    category=AuditEvent.USER_ACTION,
    event_type=AuditEvent.CREATE,
    description="New volunteer profile created",
    user=request.user,
    request=request,
    resource_type='volunteer',
    resource_id=volunteer.id
)
log_audit_event(event)
```

### Convenience Functions

The system provides pre-built functions for common events:

```python
from common.audit import (
    log_user_login, log_eoi_submission, 
    log_volunteer_assignment, log_admin_override
)

# Log user login
log_user_login(user, request, success=True)

# Log EOI submission
log_eoi_submission(user, request, volunteer_id, 'general')

# Log volunteer assignment
log_volunteer_assignment(admin_user, request, volunteer_id, role_id, event_id)

# Log admin override
log_admin_override(
    admin_user, request, 'credential_bypass', 
    'volunteer', volunteer_id, 'Emergency assignment needed'
)
```

### Decorator for Automatic Logging

Use the `@audit_action` decorator for automatic logging:

```python
from common.audit import audit_action, AuditEvent

@audit_action(
    category=AuditEvent.USER_ACTION,
    event_type=AuditEvent.VIEW,
    description="Volunteer profile viewed",
    resource_type='volunteer'
)
def volunteer_detail_view(request, pk):
    # View logic here
    pass
```

## Log Analysis and Monitoring

### Log File Locations

```bash
# View recent audit events
tail -f logs/audit.log

# Search for specific user actions
grep "user_id.*123" logs/audit.log

# Monitor security events
tail -f logs/security.log

# Check JustGo integration status
tail -f logs/justgo.log
```

### Log Format

Each log entry includes:
- **Timestamp** - ISO format with timezone
- **Log Level** - INFO, WARNING, ERROR
- **Logger Name** - Identifies the source component
- **Message** - Human-readable description
- **JSON Data** - Structured event data

Example audit log entry:
```
[AUDIT] 2024-01-15 10:30:45,123 soi_hub.audit INFO EOI submitted for general volunteer | {"timestamp": "2024-01-15T10:30:45.123456+00:00", "category": "USER_ACTION", "event_type": "EOI_SUBMIT", "user_id": 123, "resource_type": "volunteer", ...}
```

## Security Considerations

### Sensitive Data Handling

- **Passwords**: Never logged in plain text
- **Personal Data**: Minimal PII in logs, use IDs where possible
- **API Keys**: Masked or excluded from logs
- **File Uploads**: Log metadata only, not content

### Log File Security

- Log files should have restricted permissions (600 or 640)
- Regular log rotation prevents disk space issues
- Consider log shipping to secure centralized logging system
- Implement log integrity monitoring for tampering detection

### Compliance Requirements

The audit system supports:
- **GDPR**: Data processing activities tracking
- **SOX**: Financial controls and access monitoring
- **ISO 27001**: Information security management
- **Local Regulations**: Irish data protection requirements

## Configuration

### Environment Variables

```bash
# Enable/disable detailed logging
DJANGO_LOG_LEVEL=INFO

# Log file retention
LOG_RETENTION_DAYS=90

# Security logging sensitivity
SECURITY_LOG_LEVEL=WARNING
```

### Django Settings

Key logging settings in `settings.py`:

```python
# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    # ... (see settings.py for full configuration)
}

# Create logs directory
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
```

## Troubleshooting

### Common Issues

1. **Log files not created**
   - Check directory permissions
   - Verify LOGS_DIR path exists
   - Check Django user write permissions

2. **Missing audit events**
   - Verify logger names match configuration
   - Check log level settings
   - Ensure audit functions are called correctly

3. **Log rotation not working**
   - Check file permissions
   - Verify disk space availability
   - Review rotation configuration

### Debug Commands

```bash
# Test logging configuration
python manage.py test_cors  # Also tests logging

# Check log file permissions
ls -la logs/

# Verify log directory creation
python manage.py shell -c "from django.conf import settings; print(settings.LOGS_DIR)"
```

## Best Practices

### Development

- Use appropriate log levels (DEBUG for development, INFO+ for production)
- Include relevant context in log messages
- Test audit logging in development environment
- Review logs regularly during development

### Production

- Monitor log file sizes and rotation
- Set up log aggregation and analysis tools
- Implement alerting for security events
- Regular audit log reviews
- Backup critical audit logs

### Performance

- Avoid excessive logging in high-traffic areas
- Use asynchronous logging for high-volume events
- Monitor logging performance impact
- Consider log sampling for very high-volume operations

## Integration with Monitoring Tools

The logging system is designed to integrate with:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk** for enterprise log analysis
- **Grafana** for log visualization
- **Prometheus** for metrics collection
- **Sentry** for error tracking and alerting

## Maintenance

### Regular Tasks

- **Weekly**: Review security logs for anomalies
- **Monthly**: Analyze audit patterns and trends
- **Quarterly**: Review log retention policies
- **Annually**: Audit logging system effectiveness

### Log Cleanup

```bash
# Clean old log files (automated via logrotate)
find logs/ -name "*.log.*" -mtime +90 -delete

# Archive important audit logs
tar -czf audit_archive_$(date +%Y%m).tar.gz logs/audit.log.*
``` 