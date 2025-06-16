#!/usr/bin/env python3
import re

# Read the file
with open('accounts/views.py', 'r') as f:
    content = f.read()

# Fix the specific problematic calls
# Fix PASSWORD_RESET_REQUESTED call
content = re.sub(
    r'AdminAuditService\.log_security_operation\(\s*operation=\'LOGIN_SUCCESS\',\s*request=request,\s*user=user,\s*request=request,\s*operation=\'PASSWORD_RESET_REQUESTED\',',
    'AdminAuditService.log_security_operation(\n                operation=\'PASSWORD_RESET_REQUESTED\',\n                user=user,\n                request=request,',
    content
)

# Fix TOKEN_CREATED call
content = re.sub(
    r'AdminAuditService\.log_security_operation\(\s*operation=\'LOGIN_SUCCESS\',\s*request=request,\s*user=user,\s*request=request,\s*operation=\'TOKEN_CREATED\',',
    'AdminAuditService.log_security_operation(\n                    operation=\'TOKEN_CREATED\',\n                    user=user,\n                    request=request,',
    content
)

# Write back
with open('accounts/views.py', 'w') as f:
    f.write(content)

print('Fixed duplicate parameters in audit calls') 