import re

# Read the backup file
with open('accounts/views.py.backup', 'r') as f:
    content = f.read()

# Replace all log_security_event with log_security_operation
content = content.replace('AdminAuditService.log_security_event(', 'AdminAuditService.log_security_operation(')

# Replace event_type with operation
content = content.replace('event_type=', 'operation=')

# Write the fixed content
with open('accounts/views.py', 'w') as f:
    f.write(content)

print("Fixed accounts/views.py") 