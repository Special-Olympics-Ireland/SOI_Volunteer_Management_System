"""
File Upload Handlers for EOI System - ISG 2026 Volunteer Management

This module provides secure file upload handling for volunteer photos with:
- Image validation and security checks
- File size and format restrictions
- Image optimization and resizing
- Secure file storage and naming
- Virus scanning integration
- Metadata cleaning
"""

import os
import uuid
import hashlib
import mimetypes
from PIL import Image, ImageOps
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# File upload configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
MAX_IMAGE_DIMENSION = 2048  # Maximum width or height
THUMBNAIL_SIZE = (300, 300)
OPTIMIZED_SIZE = (800, 800)


class VolunteerPhotoHandler:
    """
    Handles volunteer photo uploads with security and optimization
    """
    
    def __init__(self):
        self.upload_path = 'volunteers/photos/'
        self.thumbnail_path = 'volunteers/photos/thumbnails/'
        self.temp_path = 'temp/uploads/'
    
    def validate_file(self, uploaded_file):
        """
        Comprehensive file validation
        """
        errors = []
        
        # Check file size
        if uploaded_file.size > MAX_FILE_SIZE:
            errors.append(_('File size must be less than 10MB.'))
        
        # Check file extension
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            errors.append(_('Only JPEG, PNG, and WebP images are allowed.'))
        
        # Check MIME type
        mime_type = mimetypes.guess_type(uploaded_file.name)[0]
        if mime_type not in ALLOWED_IMAGE_TYPES:
            errors.append(_('Invalid file type. Only images are allowed.'))
        
        # Validate file content
        try:
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Try to open as image
            with Image.open(uploaded_file) as img:
                # Verify it's actually an image
                img.verify()
                
                # Reset file pointer after verify
                uploaded_file.seek(0)
                
                # Check image dimensions
                with Image.open(uploaded_file) as img:
                    width, height = img.size
                    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                        errors.append(_(f'Image dimensions must be less than {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION} pixels.'))
                    
                    if width < 100 or height < 100:
                        errors.append(_('Image must be at least 100x100 pixels.'))
        
        except Exception as e:
            errors.append(_('Invalid image file or corrupted data.'))
            logger.warning(f"Image validation error: {e}")
        
        # Reset file pointer
        uploaded_file.seek(0)
        
        if errors:
            raise ValidationError(errors)
        
        return True
    
    def scan_for_malware(self, file_path):
        """
        Placeholder for malware scanning
        In production, integrate with ClamAV or similar
        """
        # TODO: Implement actual virus scanning
        # For now, just check file headers for common malware signatures
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)
                
                # Check for suspicious patterns
                suspicious_patterns = [
                    b'MZ',  # PE executable header
                    b'\x7fELF',  # ELF executable header
                    b'PK\x03\x04',  # ZIP file (could contain executables)
                ]
                
                for pattern in suspicious_patterns:
                    if pattern in header:
                        logger.warning(f"Suspicious file pattern detected in {file_path}")
                        return False
                
                return True
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            return False
    
    def clean_metadata(self, image):
        """
        Remove EXIF and other metadata from image
        """
        try:
            # Create a new image without metadata
            clean_image = Image.new(image.mode, image.size)
            clean_image.putdata(list(image.getdata()))
            return clean_image
        except Exception as e:
            logger.warning(f"Error cleaning metadata: {e}")
            return image
    
    def optimize_image(self, image, max_size=OPTIMIZED_SIZE, quality=85):
        """
        Optimize image for web display
        """
        try:
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize if necessary
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Auto-orient based on EXIF
            image = ImageOps.exif_transpose(image)
            
            # Clean metadata
            image = self.clean_metadata(image)
            
            return image
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            return image
    
    def create_thumbnail(self, image, size=THUMBNAIL_SIZE):
        """
        Create thumbnail version of image
        """
        try:
            thumbnail = image.copy()
            thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
            return thumbnail
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return None
    
    def generate_secure_filename(self, original_filename, user_id=None):
        """
        Generate secure filename with UUID and timestamp
        """
        # Get file extension
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()
        
        # Generate unique filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        
        if user_id:
            filename = f"volunteer_{user_id}_{timestamp}_{unique_id}{ext}"
        else:
            filename = f"volunteer_{timestamp}_{unique_id}{ext}"
        
        return filename
    
    def save_image(self, image, filename, path, format='JPEG', quality=85):
        """
        Save image to storage
        """
        try:
            from io import BytesIO
            
            # Create BytesIO buffer
            buffer = BytesIO()
            
            # Save image to buffer
            if format.upper() == 'JPEG':
                image.save(buffer, format='JPEG', quality=quality, optimize=True)
            elif format.upper() == 'PNG':
                image.save(buffer, format='PNG', optimize=True)
            elif format.upper() == 'WEBP':
                image.save(buffer, format='WEBP', quality=quality, optimize=True)
            else:
                image.save(buffer, format='JPEG', quality=quality, optimize=True)
            
            # Create ContentFile
            content_file = ContentFile(buffer.getvalue())
            
            # Save to storage
            full_path = os.path.join(path, filename)
            saved_path = default_storage.save(full_path, content_file)
            
            return saved_path
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise ValidationError(_('Error saving image file.'))
    
    def process_upload(self, uploaded_file, user_id=None, eoi_submission_id=None):
        """
        Main method to process uploaded volunteer photo
        """
        try:
            # Validate file
            self.validate_file(uploaded_file)
            
            # Generate secure filename
            secure_filename = self.generate_secure_filename(
                uploaded_file.name, 
                user_id or eoi_submission_id
            )
            
            # Save temporary file for scanning
            temp_path = os.path.join(settings.MEDIA_ROOT, self.temp_path, secure_filename)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'wb') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
            
            # Scan for malware
            if not self.scan_for_malware(temp_path):
                os.remove(temp_path)
                raise ValidationError(_('File failed security scan.'))
            
            # Process image
            with Image.open(temp_path) as original_image:
                # Optimize main image
                optimized_image = self.optimize_image(original_image)
                
                # Create thumbnail
                thumbnail_image = self.create_thumbnail(optimized_image)
                
                # Save optimized image
                main_filename = secure_filename
                main_path = self.save_image(
                    optimized_image, 
                    main_filename, 
                    self.upload_path,
                    format='JPEG',
                    quality=85
                )
                
                # Save thumbnail
                thumbnail_filename = f"thumb_{secure_filename}"
                thumbnail_path = None
                if thumbnail_image:
                    thumbnail_path = self.save_image(
                        thumbnail_image,
                        thumbnail_filename,
                        self.thumbnail_path,
                        format='JPEG',
                        quality=80
                    )
                
                # Clean up temp file
                os.remove(temp_path)
                
                # Log successful upload
                logger.info(f"Successfully processed photo upload: {main_path}")
                
                return {
                    'main_path': main_path,
                    'thumbnail_path': thumbnail_path,
                    'filename': main_filename,
                    'size': optimized_image.size,
                    'file_size': default_storage.size(main_path)
                }
        
        except ValidationError:
            # Clean up temp file if it exists
            temp_path = os.path.join(settings.MEDIA_ROOT, self.temp_path, 
                                   self.generate_secure_filename(uploaded_file.name, user_id))
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
        
        except Exception as e:
            # Clean up temp file if it exists
            temp_path = os.path.join(settings.MEDIA_ROOT, self.temp_path, 
                                   self.generate_secure_filename(uploaded_file.name, user_id))
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            logger.error(f"Error processing photo upload: {e}")
            raise ValidationError(_('Error processing image file.'))
    
    def delete_photo(self, file_path, thumbnail_path=None):
        """
        Delete photo and thumbnail from storage
        """
        try:
            # Delete main file
            if file_path and default_storage.exists(file_path):
                default_storage.delete(file_path)
                logger.info(f"Deleted photo: {file_path}")
            
            # Delete thumbnail
            if thumbnail_path and default_storage.exists(thumbnail_path):
                default_storage.delete(thumbnail_path)
                logger.info(f"Deleted thumbnail: {thumbnail_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting photo files: {e}")
            return False


class FileUploadValidator:
    """
    Standalone validator for file uploads
    """
    
    @staticmethod
    def validate_volunteer_photo(file):
        """
        Django form field validator for volunteer photos
        """
        handler = VolunteerPhotoHandler()
        return handler.validate_file(file)


def get_photo_upload_path(instance, filename):
    """
    Generate upload path for volunteer photos
    """
    handler = VolunteerPhotoHandler()
    user_id = None
    
    if hasattr(instance, 'eoi_submission') and instance.eoi_submission:
        if instance.eoi_submission.user:
            user_id = instance.eoi_submission.user.id
        else:
            user_id = str(instance.eoi_submission.id)[:8]
    
    secure_filename = handler.generate_secure_filename(filename, user_id)
    return os.path.join(handler.upload_path, secure_filename)


def process_volunteer_photo(uploaded_file, user_id=None, eoi_submission_id=None):
    """
    Convenience function to process volunteer photo uploads
    """
    handler = VolunteerPhotoHandler()
    return handler.process_upload(uploaded_file, user_id, eoi_submission_id) 