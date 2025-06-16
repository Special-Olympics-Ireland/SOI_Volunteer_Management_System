# Static Files and Media Handling Setup for SOI Hub

This document provides instructions for setting up static files and media handling for the ISG 2026 Volunteer Management Backend System.

## Overview

SOI Hub handles two types of files:
- **Static Files**: CSS, JavaScript, images, and other assets that are part of the application
- **Media Files**: User-uploaded content such as volunteer photos, documents, and task attachments

## Directory Structure

```
soi-hub/
├── static/                     # Static files (development)
│   └── admin/
│       ├── css/
│       │   └── soi-admin.css   # Custom admin styling
│       └── img/
├── staticfiles/                # Collected static files (production)
├── media/                      # User uploads
│   ├── volunteers/
│   │   ├── photos/            # Volunteer profile photos
│   │   └── documents/         # Volunteer documents
│   ├── events/                # Event-related files
│   ├── tasks/                 # Task attachments
│   └── general/               # General uploads
└── templates/
    └── admin/
        └── base_site.html     # Custom admin template
```

## Static Files Configuration

### Django Settings

The following settings are configured in `settings.py`:

```python
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644
```

### Static Files Collection

For production deployment, collect static files:

```bash
python manage.py collectstatic --noinput
```

## Media Files Handling

### File Upload Security

SOI Hub implements comprehensive file upload security:

1. **File Type Validation**: Only allowed file types are accepted
2. **File Size Limits**: 2MB for images, 5MB for documents
3. **Filename Sanitization**: Secure filename generation
4. **Content Validation**: Image files are verified for integrity
5. **Path Organization**: Files are organized by date and user

### Allowed File Types

#### Images (Volunteer Photos)
- JPEG/JPG (image/jpeg)
- PNG (image/png)
- GIF (image/gif)
- WebP (image/webp)

#### Documents
- PDF (application/pdf)
- Word Documents (.doc, .docx)
- Text Files (.txt)

### File Organization

Files are automatically organized using this structure:

```
media/
├── volunteers/
│   └── photos/
│       └── 2024/
│           └── 12/
│               └── user_123/
│                   ├── main_user_123_20241201_120000_abc12345.jpg
│                   └── thumb_user_123_20241201_120000_def67890.jpg
└── tasks/
    └── 2024/
        └── 12/
            └── user_456/
                └── task_789/
                    └── attachment_user_456_20241201_130000_ghi12345.pdf
```

## File Upload Implementation

### Using the FileUploadHandler

```python
from common.file_utils import FileUploadHandler, save_volunteer_photo

# For volunteer photos
def upload_volunteer_photo(request, volunteer_id):
    if 'photo' in request.FILES:
        uploaded_file = request.FILES['photo']
        try:
            result = save_volunteer_photo(uploaded_file, volunteer_id)
            # result contains file paths and metadata
            return JsonResponse({'success': True, 'data': result})
        except ValidationError as e:
            return JsonResponse({'success': False, 'errors': e.messages})

# For general file uploads
handler = FileUploadHandler('task_attachment')
result = handler.save_file(uploaded_file, user_id=user.id, subfolder='task_123')
```

### Image Processing

Volunteer photos are automatically processed:

1. **Format Conversion**: Converted to JPEG for consistency
2. **Resizing**: Large images are resized to max 1920x1080
3. **Optimization**: Images are optimized for web delivery
4. **Thumbnail Creation**: 300x300 thumbnails are generated
5. **Quality Control**: JPEG quality set to 85% for main images, 75% for thumbnails

## Admin Interface Customization

### SOI Branding

The admin interface includes custom SOI branding:

- **Colors**: Green (#228B22), White (#FFFFFF), Gold (#FFD700)
- **Logo**: SVG-based SOI logo in header
- **Typography**: Professional fonts with proper hierarchy
- **Responsive Design**: Mobile-friendly interface

### Custom Features

1. **Enhanced File Uploads**: Drag-and-drop functionality
2. **Loading States**: Visual feedback for form submissions
3. **Keyboard Shortcuts**: Ctrl+S to save, Ctrl+H for home
4. **Auto-save Drafts**: Automatic draft saving for long forms
5. **Confirmation Dialogs**: Safety prompts for delete operations

## Production Deployment

### Nginx Configuration

For production, configure Nginx to serve static and media files:

```nginx
server {
    listen 80;
    server_name 195.7.35.202;

    # Static files
    location /static/ {
        alias /path/to/soi-hub/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /path/to/soi-hub/media/;
        expires 1y;
        add_header Cache-Control "public";
        
        # Security headers for uploads
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
    }

    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### File Permissions

Set appropriate file permissions:

```bash
# Static files (read-only)
chmod -R 644 staticfiles/
find staticfiles/ -type d -exec chmod 755 {} \;

# Media files (read-write for Django)
chmod -R 644 media/
find media/ -type d -exec chmod 755 {} \;
chown -R www-data:www-data media/
```

### Backup Strategy

Implement regular backups for media files:

```bash
#!/bin/bash
# backup_media.sh

BACKUP_DIR="/backup/soi-hub/media"
MEDIA_DIR="/path/to/soi-hub/media"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create compressed backup
tar -czf "$BACKUP_DIR/media_backup_$DATE.tar.gz" -C "$MEDIA_DIR" .

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "media_backup_*.tar.gz" -mtime +30 -delete

echo "Media backup completed: media_backup_$DATE.tar.gz"
```

## Security Considerations

### File Upload Security

1. **Virus Scanning**: Consider integrating virus scanning for uploads
2. **Content Validation**: All images are validated and re-processed
3. **Access Control**: Media files should not be directly executable
4. **Rate Limiting**: Implement upload rate limiting per user
5. **Storage Limits**: Monitor and limit storage usage per user

### Access Control

```python
# Example view with proper access control
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied

@login_required
def serve_volunteer_photo(request, photo_id):
    # Check if user has permission to view this photo
    photo = get_object_or_404(VolunteerPhoto, id=photo_id)
    
    if not user_can_view_photo(request.user, photo):
        raise PermissionDenied
    
    # Serve file securely
    response = HttpResponse(photo.file.read(), content_type='image/jpeg')
    response['Content-Disposition'] = f'inline; filename="{photo.filename}"'
    return response
```

## Monitoring and Maintenance

### File System Monitoring

Monitor disk usage and file system health:

```bash
# Check disk usage
df -h /path/to/soi-hub/media

# Monitor file counts
find /path/to/soi-hub/media -type f | wc -l

# Check for large files
find /path/to/soi-hub/media -type f -size +10M -ls
```

### Cleanup Tasks

Implement periodic cleanup tasks:

```python
# management/commands/cleanup_files.py
from django.core.management.base import BaseCommand
from common.file_utils import cleanup_orphaned_files

class Command(BaseCommand):
    help = 'Clean up orphaned files'

    def handle(self, *args, **options):
        cleanup_orphaned_files()
        self.stdout.write(
            self.style.SUCCESS('Successfully cleaned up orphaned files')
        )
```

Run cleanup weekly:

```bash
# Add to crontab
0 2 * * 0 cd /path/to/soi-hub && python manage.py cleanup_files
```

## Testing File Uploads

### Unit Tests

```python
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from common.file_utils import FileUploadHandler

class FileUploadTests(TestCase):
    def test_valid_image_upload(self):
        # Create test image
        image_content = b'\x89PNG\r\n\x1a\n...'  # Valid PNG content
        uploaded_file = SimpleUploadedFile(
            "test.png", 
            image_content, 
            content_type="image/png"
        )
        
        handler = FileUploadHandler('volunteer_photo')
        validation = handler.validate_file(uploaded_file)
        
        self.assertTrue(validation['valid'])
        self.assertEqual(len(validation['errors']), 0)

    def test_invalid_file_type(self):
        # Test with invalid file type
        uploaded_file = SimpleUploadedFile(
            "test.exe", 
            b"executable content", 
            content_type="application/x-executable"
        )
        
        handler = FileUploadHandler('volunteer_photo')
        validation = handler.validate_file(uploaded_file)
        
        self.assertFalse(validation['valid'])
        self.assertIn('Invalid image type', str(validation['errors']))
```

### Manual Testing

Test file uploads through the admin interface:

1. Navigate to volunteer profile creation
2. Upload various file types and sizes
3. Verify proper validation messages
4. Check file organization in media directory
5. Test thumbnail generation for images

## Troubleshooting

### Common Issues

1. **Permission Denied**: Check file permissions and ownership
2. **File Not Found**: Verify MEDIA_ROOT and MEDIA_URL settings
3. **Upload Fails**: Check file size limits and allowed types
4. **Images Not Processing**: Verify Pillow installation and dependencies

### Debug Commands

```bash
# Check Django settings
python manage.py shell -c "from django.conf import settings; print(f'MEDIA_ROOT: {settings.MEDIA_ROOT}'); print(f'MEDIA_URL: {settings.MEDIA_URL}')"

# Test file upload handler
python manage.py shell -c "from common.file_utils import FileUploadHandler; handler = FileUploadHandler('volunteer_photo'); print('Handler created successfully')"

# Check static files
python manage.py findstatic admin/css/soi-admin.css
```

## Performance Optimization

### CDN Integration

For production, consider using a CDN for static files:

```python
# settings.py for CDN
if not DEBUG:
    STATIC_URL = 'https://cdn.specialolympics.ie/static/'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.StaticS3Boto3Storage'
```

### Image Optimization

Implement additional image optimization:

1. **WebP Conversion**: Convert images to WebP for better compression
2. **Lazy Loading**: Implement lazy loading for image galleries
3. **Progressive JPEG**: Use progressive JPEG for better perceived performance
4. **Image Sprites**: Combine small icons into sprites

This completes the static files and media handling setup for SOI Hub, providing secure, organized, and efficient file management for the ISG 2026 volunteer management system. 