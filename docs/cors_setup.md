# CORS Configuration for SOI Hub

This document provides instructions for configuring Cross-Origin Resource Sharing (CORS) for the ISG 2026 Volunteer Management Backend System.

## Overview

CORS (Cross-Origin Resource Sharing) is a security feature implemented by web browsers that restricts web pages from making requests to a different domain than the one serving the web page. SOI Hub implements enhanced CORS handling to support frontend integration while maintaining security.

## Quick Setup

The CORS configuration is already set up in Django settings with sensible defaults. For development, the default configuration allows:

- `http://localhost:3000` (React development server)
- `http://localhost:3001` (Alternative development port)
- `http://127.0.0.1:3000` and `http://127.0.0.1:3001`

## Configuration

### Environment Variables

Configure these in your `.env` file:

```env
# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
SOI_CORS_ENABLE_LOGGING=True
SOI_CORS_STRICT_MODE=False
```

### Django Settings

The CORS configuration in `settings.py` includes:

```python
# Basic CORS settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3001',
]

CORS_ALLOW_CREDENTIALS = True

# Enhanced CORS settings
CORS_ALLOWED_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT'
]

CORS_ALLOWED_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'x-soi-hub-version', 'cache-control'
]

CORS_EXPOSE_HEADERS = [
    'x-soi-hub-version', 'x-soi-hub-environment',
    'x-total-count', 'x-page-count'
]

CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours
```

## SOI Hub Enhanced CORS Features

### Custom Middleware

SOI Hub includes a custom CORS middleware (`common.cors_middleware.SOIHubCORSMiddleware`) that provides:

1. **Enhanced Security Headers**: Automatic addition of security headers
2. **Request Logging**: Detailed logging for debugging CORS issues
3. **Dynamic Origin Validation**: Support for regex patterns and development mode
4. **Rate Limiting Integration**: Ready for rate limiting implementation
5. **SOI Hub Specific Headers**: Custom headers for version and environment tracking

### Security Features

- **Strict Mode**: Configurable strict mode for production environments
- **Origin Validation**: Comprehensive origin validation with regex support
- **Header Validation**: Strict header validation for preflight requests
- **Method Validation**: Configurable allowed HTTP methods
- **Credential Handling**: Secure credential handling with proper validation

## Environment-Specific Configuration

### Development Environment

```python
CORS_PRESETS['development'] = {
    'CORS_ALLOWED_ORIGINS': [
        'http://localhost:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:3001',
    ],
    'CORS_ALLOW_CREDENTIALS': True,
    'SOI_CORS_ENABLE_LOGGING': True,
    'SOI_CORS_STRICT_MODE': False,
}
```

### Staging Environment

```python
CORS_PRESETS['staging'] = {
    'CORS_ALLOWED_ORIGINS': [
        'https://staging.specialolympics.ie',
        'https://staging-volunteers.specialolympics.ie',
    ],
    'CORS_ALLOW_CREDENTIALS': True,
    'SOI_CORS_ENABLE_LOGGING': True,
    'SOI_CORS_STRICT_MODE': True,
}
```

### Production Environment

```python
CORS_PRESETS['production'] = {
    'CORS_ALLOWED_ORIGINS': [
        'https://specialolympics.ie',
        'https://volunteers.specialolympics.ie',
        'https://isg2026.specialolympics.ie',
    ],
    'CORS_ALLOW_CREDENTIALS': True,
    'SOI_CORS_ENABLE_LOGGING': False,
    'SOI_CORS_STRICT_MODE': True,
}
```

## Testing CORS Configuration

### Management Command

Use the built-in management command to test CORS configuration:

```bash
# Test current configuration
python manage.py test_cors

# Test a specific origin
python manage.py test_cors --origin http://localhost:3000

# Generate comprehensive report
python manage.py test_cors --report

# Validate all configured origins
python manage.py test_cors --validate-all

# Save report to file
python manage.py test_cors --report --output-file cors_report.json
```

### API Endpoints

SOI Hub provides testing endpoints for CORS validation:

```bash
# Test GET request
curl -H "Origin: http://localhost:3000" http://localhost:8000/api/v1/cors/test/

# Test POST request
curl -X POST -H "Origin: http://localhost:3000" -H "Content-Type: application/json" \
     -d '{"test": "data"}' http://localhost:8000/api/v1/cors/test/

# Test preflight request
curl -X OPTIONS -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type,authorization" \
     http://localhost:8000/api/v1/cors/test/

# Validate specific origin
curl http://localhost:8000/api/v1/cors/validate/http://localhost:3000/

# Get CORS report
curl http://localhost:8000/api/v1/cors/report/
```

### Browser Testing

Test CORS in browser console:

```javascript
// Test simple GET request
fetch('http://localhost:8000/api/v1/cors/test/', {
    method: 'GET',
    credentials: 'include'
})
.then(response => response.json())
.then(data => console.log('GET test:', data))
.catch(error => console.error('GET error:', error));

// Test POST request with custom headers
fetch('http://localhost:8000/api/v1/cors/test/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token123'
    },
    credentials: 'include',
    body: JSON.stringify({test: 'data'})
})
.then(response => response.json())
.then(data => console.log('POST test:', data))
.catch(error => console.error('POST error:', error));
```

## Troubleshooting

### Common Issues

1. **CORS Error: Origin not allowed**
   - Check if origin is in `CORS_ALLOWED_ORIGINS`
   - Verify origin format (include protocol and port)
   - Check regex patterns in `CORS_ALLOWED_ORIGIN_REGEXES`

2. **Preflight request failed**
   - Verify requested method is in `CORS_ALLOWED_METHODS`
   - Check requested headers are in `CORS_ALLOWED_HEADERS`
   - Ensure origin is allowed

3. **Credentials not included**
   - Set `CORS_ALLOW_CREDENTIALS = True`
   - Ensure frontend sends `credentials: 'include'`
   - Verify origin is not wildcard (`*`)

4. **Headers not exposed**
   - Add headers to `CORS_EXPOSE_HEADERS`
   - Check browser developer tools for exposed headers

### Debug Mode

Enable debug logging in development:

```python
SOI_CORS_ENABLE_LOGGING = True
```

Check logs for CORS-related messages:

```bash
# View CORS logs
tail -f logs/django.log | grep CORS

# View audit logs
tail -f logs/audit.log | grep cors
```

### Configuration Validation

The system automatically validates CORS configuration on startup:

```python
from common.cors_middleware import CORSConfigValidator

try:
    CORSConfigValidator.validate_settings()
    print("CORS configuration is valid")
except Exception as e:
    print(f"CORS configuration error: {e}")
```

## Security Considerations

### Production Security

1. **Use HTTPS Only**: All production origins must use HTTPS
2. **Specific Origins**: Never use wildcard (`*`) with credentials
3. **Minimal Headers**: Only expose necessary headers
4. **Strict Mode**: Enable strict mode in production
5. **Regular Audits**: Regularly review and audit CORS configuration

### Security Headers

SOI Hub automatically adds security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'none'; frame-ancestors 'none';
X-SOI-Hub-Version: 1.0.0
X-SOI-Hub-Environment: production
```

### Best Practices

1. **Principle of Least Privilege**: Only allow necessary origins, methods, and headers
2. **Environment Separation**: Use different configurations for dev/staging/production
3. **Regular Testing**: Test CORS configuration regularly
4. **Monitor Logs**: Monitor CORS-related logs for suspicious activity
5. **Documentation**: Keep CORS configuration documented and up-to-date

## Integration with Frontend

### React/Next.js Integration

Configure your frontend to work with SOI Hub CORS:

```javascript
// API client configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,  // Include credentials
    headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
});

// Handle CORS errors
apiClient.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 403 && error.config?.url?.includes('cors')) {
            console.error('CORS error - check origin configuration');
        }
        return Promise.reject(error);
    }
);
```

### Environment Configuration

Frontend environment variables:

```env
# Development
REACT_APP_API_URL=http://localhost:8000

# Staging
REACT_APP_API_URL=https://api-staging.specialolympics.ie

# Production
REACT_APP_API_URL=https://api.specialolympics.ie
```

## Monitoring and Maintenance

### Health Checks

Monitor CORS health with regular checks:

```bash
# Check CORS configuration
python manage.py test_cors --validate-all

# Generate weekly reports
python manage.py test_cors --report --output-file "cors_report_$(date +%Y%m%d).json"
```

### Automated Testing

Include CORS tests in CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Test CORS Configuration
  run: |
    python manage.py test_cors --validate-all
    python manage.py test_cors --report
```

### Log Analysis

Analyze CORS logs for patterns:

```bash
# Count CORS requests by origin
grep "CORS request from origin" logs/django.log | awk '{print $6}' | sort | uniq -c

# Find rejected CORS requests
grep "CORS request rejected" logs/django.log

# Monitor preflight requests
grep "Preflight request" logs/django.log
```

This completes the CORS configuration setup for SOI Hub, providing secure and flexible cross-origin resource sharing for the ISG 2026 volunteer management system. 