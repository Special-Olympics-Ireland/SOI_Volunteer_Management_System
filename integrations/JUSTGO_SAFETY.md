# JustGo API Integration - Safety Measures

## 🔒 **READ-ONLY MODE (Default)**

By default, the JustGo integration operates in **READ-ONLY MODE** to prevent accidental modifications to live JustGo data.

### ✅ **Safe Operations (Always Available):**
- Member profile lookup by email or MID
- Credential retrieval and validation
- Health checks and API testing
- Data analysis and reporting

### ⚠️ **Write Operations (Disabled by Default):**
- Creating new member profiles
- Updating existing member profiles  
- Bi-directional synchronization (local ↔ JustGo)

## 🛡️ **Safety Configuration**

### Environment Variables:
```bash
# Keep this as 'true' for production safety
JUSTGO_READONLY_MODE=true

# Only set to 'false' in development/testing
JUSTGO_READONLY_MODE=false
```

### Django Settings:
```python
# Default: True (read-only mode enabled)
JUSTGO_READONLY_MODE = config('JUSTGO_READONLY_MODE', default=True, cast=bool)
```

## 🚨 **Error Messages**

When attempting write operations in read-only mode:

```
JustGoAPIError: SAFETY: Profile creation is disabled in read-only mode. 
Set JUSTGO_READONLY_MODE=False in settings to enable writes.
```

## 📋 **Testing Safely**

### Read-Only Testing (Safe):
```python
# These operations are always safe
client = JustGoAPIClient()
member = client.find_member_by_email('test@example.com')
credentials = client.get_member_credentials(member_id)
validation = client.validate_member_credentials_for_role(member_id, role_requirements)
```

### Write Testing (Development Only):
```python
# Only works when JUSTGO_READONLY_MODE=False
client = JustGoAPIClient()
result = client.create_member_profile(member_data)  # Will raise error in read-only mode
```

## 🔧 **Management Commands**

### Safe Testing Command:
```bash
# Always safe - read-only operations
python manage.py test_justgo_api --health-check-only
python manage.py test_justgo_api --member-id ME000001
```

### Development Testing:
```bash
# Set environment variable for testing
export JUSTGO_READONLY_MODE=false
python manage.py test_justgo_api --full-test
```

## 📊 **Current Implementation Status**

### ✅ **Completed & Safe:**
- Task 3.1: JustGo API client with authentication
- Task 3.2: Member profile lookup (READ-ONLY)
- Task 3.3: Credential retrieval (READ-ONLY)
- Task 3.6: Credential validation engine (READ-ONLY)

### ⚠️ **Completed but Protected:**
- Task 3.4: Profile creation (WRITE - disabled by default)
- Task 3.5: Bi-directional sync (WRITE - disabled by default)

### 🔄 **Remaining Tasks:**
- Task 3.7: Admin override system
- Task 3.8: Enhanced error handling
- Task 3.9: Integration models
- Task 3.10: Membership type handling
- Task 3.11: Comprehensive unit tests
- Task 3.12: Bulk sync management commands

## 🎯 **Best Practices**

1. **Always test in read-only mode first**
2. **Use test credentials for development**
3. **Never disable read-only mode in production**
4. **Monitor logs for write operation attempts**
5. **Validate data before any sync operations**

## 📞 **Support**

If you need to perform write operations:
1. Confirm you're in a development environment
2. Set `JUSTGO_READONLY_MODE=false`
3. Test with non-production data first
4. Re-enable read-only mode when done 