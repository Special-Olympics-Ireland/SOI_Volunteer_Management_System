"""
File upload utilities for SOI Hub.
Handles secure file uploads, validation, and organization.
"""

import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.utils.text import slugify


class FileUploadHandler:
    """
    Handles secure file uploads with validation and organization.
    """
    
    # Allowed file types and their MIME types
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/webp': ['.webp'],
    }
    
    ALLOWED_DOCUMENT_TYPES = {
        'application/pdf': ['.pdf'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'text/plain': ['.txt'],
    }
    
    # Maximum file sizes (in bytes)
    MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB
    
    # Image processing settings
    MAX_IMAGE_DIMENSIONS = (1920, 1080)
    THUMBNAIL_SIZE = (300, 300)
    
    def __init__(self, upload_type='general'):
        """
        Initialize the file upload handler.
        
        Args:
            upload_type (str): Type of upload ('volunteer_photo', 'volunteer_document', 
                             'event_file', 'task_attachment', 'general')
        """
        self.upload_type = upload_type
        self.base_path = self._get_base_path()
    
    def _get_base_path(self):
        """Get the base path for the upload type."""
        paths = {
            'volunteer_photo': 'volunteers/photos',
            'volunteer_document': 'volunteers/documents',
            'event_file': 'events',
            'task_attachment': 'tasks',
            'general': 'general',
        }
        return paths.get(self.upload_type, 'general')
    
    def validate_file(self, uploaded_file):
        """
        Validate uploaded file for security and compliance.
        
        Args:
            uploaded_file: Django UploadedFile object
            
        Returns:
            dict: Validation result with 'valid' boolean and 'errors' list
        """
        errors = []
        
        # Check file size
        if self.upload_type == 'volunteer_photo':
            if uploaded_file.size > self.MAX_IMAGE_SIZE:
                errors.append(f'Image file too large. Maximum size is {self.MAX_IMAGE_SIZE // (1024*1024)}MB.')
        else:
            if uploaded_file.size > self.MAX_DOCUMENT_SIZE:
                errors.append(f'File too large. Maximum size is {self.MAX_DOCUMENT_SIZE // (1024*1024)}MB.')
        
        # Check file type
        content_type = uploaded_file.content_type
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        if self.upload_type == 'volunteer_photo':
            if content_type not in self.ALLOWED_IMAGE_TYPES:
                errors.append(f'Invalid image type. Allowed types: {", ".join(self.ALLOWED_IMAGE_TYPES.keys())}')
            elif file_extension not in self.ALLOWED_IMAGE_TYPES.get(content_type, []):
                errors.append(f'File extension {file_extension} does not match content type {content_type}')
        else:
            allowed_types = {**self.ALLOWED_IMAGE_TYPES, **self.ALLOWED_DOCUMENT_TYPES}
            if content_type not in allowed_types:
                errors.append(f'Invalid file type. Allowed types: {", ".join(allowed_types.keys())}')
            elif file_extension not in allowed_types.get(content_type, []):
                errors.append(f'File extension {file_extension} does not match content type {content_type}')
        
        # Check filename for security
        if not self._is_safe_filename(uploaded_file.name):
            errors.append('Invalid filename. Please use only letters, numbers, hyphens, and underscores.')
        
        # Additional validation for images
        if self.upload_type == 'volunteer_photo' and not errors:
            try:
                image = Image.open(uploaded_file)
                # Check image dimensions
                if image.size[0] > 5000 or image.size[1] > 5000:
                    errors.append('Image dimensions too large. Maximum 5000x5000 pixels.')
                # Verify it's a valid image
                image.verify()
            except Exception as e:
                errors.append(f'Invalid image file: {str(e)}')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _is_safe_filename(self, filename):
        """Check if filename is safe (no path traversal, etc.)."""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Check for dangerous patterns
        dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for pattern in dangerous_patterns:
            if pattern in filename:
                return False
        
        # Check length
        if len(filename) > 255:
            return False
        
        return True
    
    def generate_filename(self, original_filename, user_id=None, prefix=None):
        """
        Generate a secure, unique filename.
        
        Args:
            original_filename (str): Original filename
            user_id (int): User ID for organization
            prefix (str): Optional prefix for filename
            
        Returns:
            str: Generated filename
        """
        # Get file extension
        file_extension = Path(original_filename).suffix.lower()
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create filename components
        components = []
        
        if prefix:
            components.append(slugify(prefix))
        
        if user_id:
            components.append(f'user_{user_id}')
        
        components.extend([timestamp, unique_id])
        
        # Join components and add extension
        filename = '_'.join(components) + file_extension
        
        return filename
    
    def get_upload_path(self, filename, user_id=None, subfolder=None):
        """
        Get the full upload path for a file.
        
        Args:
            filename (str): Filename
            user_id (int): User ID for organization
            subfolder (str): Optional subfolder
            
        Returns:
            str: Full upload path
        """
        path_components = [self.base_path]
        
        # Add date-based organization
        date_folder = datetime.now().strftime('%Y/%m')
        path_components.append(date_folder)
        
        # Add user-based organization if provided
        if user_id:
            path_components.append(f'user_{user_id}')
        
        # Add subfolder if provided
        if subfolder:
            path_components.append(slugify(subfolder))
        
        path_components.append(filename)
        
        return '/'.join(path_components)
    
    def process_image(self, uploaded_file, create_thumbnail=True):
        """
        Process uploaded image (resize, optimize, create thumbnail).
        
        Args:
            uploaded_file: Django UploadedFile object
            create_thumbnail (bool): Whether to create a thumbnail
            
        Returns:
            dict: Processing result with file paths
        """
        try:
            image = Image.open(uploaded_file)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize if too large
            if image.size[0] > self.MAX_IMAGE_DIMENSIONS[0] or image.size[1] > self.MAX_IMAGE_DIMENSIONS[1]:
                image.thumbnail(self.MAX_IMAGE_DIMENSIONS, Image.Resampling.LANCZOS)
            
            result = {'main_image': None, 'thumbnail': None}
            
            # Save main image
            main_filename = self.generate_filename(uploaded_file.name, prefix='main')
            main_path = self.get_upload_path(main_filename)
            
            # Save to storage
            from io import BytesIO
            output = BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            saved_path = default_storage.save(main_path, output)
            result['main_image'] = saved_path
            
            # Create thumbnail if requested
            if create_thumbnail:
                thumbnail = image.copy()
                thumbnail.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                
                thumb_filename = self.generate_filename(uploaded_file.name, prefix='thumb')
                thumb_path = self.get_upload_path(thumb_filename)
                
                thumb_output = BytesIO()
                thumbnail.save(thumb_output, format='JPEG', quality=75, optimize=True)
                thumb_output.seek(0)
                
                thumb_saved_path = default_storage.save(thumb_path, thumb_output)
                result['thumbnail'] = thumb_saved_path
            
            return result
            
        except Exception as e:
            raise ValidationError(f'Error processing image: {str(e)}')
    
    def calculate_file_hash(self, uploaded_file):
        """
        Calculate SHA-256 hash of uploaded file for integrity checking.
        
        Args:
            uploaded_file: Django UploadedFile object
            
        Returns:
            str: SHA-256 hash
        """
        hash_sha256 = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def save_file(self, uploaded_file, user_id=None, subfolder=None, process_image=True):
        """
        Save uploaded file with all processing and validation.
        
        Args:
            uploaded_file: Django UploadedFile object
            user_id (int): User ID for organization
            subfolder (str): Optional subfolder
            process_image (bool): Whether to process images
            
        Returns:
            dict: Save result with file information
        """
        # Validate file
        validation = self.validate_file(uploaded_file)
        if not validation['valid']:
            raise ValidationError(validation['errors'])
        
        # Generate filename
        filename = self.generate_filename(uploaded_file.name, user_id=user_id)
        
        # Calculate file hash
        file_hash = self.calculate_file_hash(uploaded_file)
        uploaded_file.seek(0)  # Reset file pointer after hash calculation
        
        result = {
            'original_filename': uploaded_file.name,
            'filename': filename,
            'file_hash': file_hash,
            'file_size': uploaded_file.size,
            'content_type': uploaded_file.content_type,
        }
        
        # Process image if it's an image file and processing is enabled
        if (self.upload_type == 'volunteer_photo' and 
            uploaded_file.content_type in self.ALLOWED_IMAGE_TYPES and 
            process_image):
            
            image_result = self.process_image(uploaded_file)
            result.update(image_result)
        else:
            # Save regular file
            file_path = self.get_upload_path(filename, user_id=user_id, subfolder=subfolder)
            saved_path = default_storage.save(file_path, uploaded_file)
            result['file_path'] = saved_path
        
        return result


def get_file_upload_handler(upload_type):
    """
    Factory function to get appropriate file upload handler.
    
    Args:
        upload_type (str): Type of upload
        
    Returns:
        FileUploadHandler: Configured handler instance
    """
    return FileUploadHandler(upload_type)


def validate_volunteer_photo(uploaded_file):
    """
    Convenience function to validate volunteer photo uploads.
    
    Args:
        uploaded_file: Django UploadedFile object
        
    Returns:
        dict: Validation result
    """
    handler = FileUploadHandler('volunteer_photo')
    return handler.validate_file(uploaded_file)


def save_volunteer_photo(uploaded_file, volunteer_id):
    """
    Convenience function to save volunteer photo.
    
    Args:
        uploaded_file: Django UploadedFile object
        volunteer_id (int): Volunteer ID
        
    Returns:
        dict: Save result
    """
    handler = FileUploadHandler('volunteer_photo')
    return handler.save_file(uploaded_file, user_id=volunteer_id)


def save_task_attachment(uploaded_file, task_id, user_id):
    """
    Convenience function to save task attachment.
    
    Args:
        uploaded_file: Django UploadedFile object
        task_id (int): Task ID
        user_id (int): User ID
        
    Returns:
        dict: Save result
    """
    handler = FileUploadHandler('task_attachment')
    return handler.save_file(uploaded_file, user_id=user_id, subfolder=f'task_{task_id}')


# File cleanup utilities
def cleanup_orphaned_files():
    """
    Clean up orphaned files that are no longer referenced in the database.
    This should be run as a periodic task.
    """
    # This would implement logic to find and remove orphaned files
    # Implementation would depend on specific model relationships
    pass


def get_file_info(file_path):
    """
    Get information about a stored file.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        dict: File information
    """
    if not default_storage.exists(file_path):
        return None
    
    try:
        file_size = default_storage.size(file_path)
        file_url = default_storage.url(file_path)
        
        return {
            'path': file_path,
            'size': file_size,
            'url': file_url,
            'exists': True,
        }
    except Exception:
        return None


def validate_image_file(uploaded_file):
    """
    Validate an image file upload (Django validator function).
    
    Args:
        uploaded_file: Django UploadedFile object
        
    Raises:
        ValidationError: If file is invalid
    """
    handler = FileUploadHandler('volunteer_photo')
    result = handler.validate_file(uploaded_file)
    
    if not result['valid']:
        raise ValidationError('; '.join(result['errors'])) 