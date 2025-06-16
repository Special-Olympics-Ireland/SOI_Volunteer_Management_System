"""
Export Views for EOI System - ISG 2026 Volunteer Management

This module provides views for data export functionality including:
- Export configuration interface
- Data export endpoints
- Export statistics dashboard
"""

import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
import logging

from .eoi_export import EOIDataExporter, get_export_statistics
from .eoi_models import EOISubmission
from .permissions import IsStaffOrVMTOrCVT
from common.audit import log_audit_event

logger = logging.getLogger(__name__)


@login_required
def export_dashboard(request):
    """
    Export dashboard for staff to configure and download exports
    """
    # Check permissions
    if not IsStaffOrVMTOrCVT().has_permission(request, None):
        messages.error(request, _('You do not have permission to access the export dashboard.'))
        return redirect('volunteers:dashboard')
    
    try:
        # Get export statistics
        stats = get_export_statistics(request.user)
        
        # Get field definitions for export configuration
        exporter = EOIDataExporter(request.user)
        field_definitions = exporter.get_field_definitions()
        
        # Group fields by category
        fields_by_category = {}
        for field_key, field_info in field_definitions.items():
            category = field_info['category']
            if category not in fields_by_category:
                fields_by_category[category] = []
            fields_by_category[category].append({
                'key': field_key,
                'label': field_info['label']
            })
        
        # Get recent submissions for preview
        recent_submissions = EOISubmission.objects.select_related(
            'profile_information'
        ).order_by('-created_at')[:10]
        
        context = {
            'stats': stats,
            'fields_by_category': fields_by_category,
            'recent_submissions': recent_submissions,
            'volunteer_types': EOISubmission.VolunteerType.choices,
            'status_choices': EOISubmission.SubmissionStatus.choices,
            'title': _('Data Export Dashboard')
        }
        
        return render(request, 'volunteers/export/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading export dashboard: {e}")
        messages.error(request, _('Error loading export dashboard. Please try again.'))
        return redirect('volunteers:dashboard')


@login_required
@require_POST
def export_data(request):
    """
    Export EOI data based on user configuration
    """
    # Check permissions
    if not IsStaffOrVMTOrCVT().has_permission(request, None):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        # Parse request data
        data = json.loads(request.body)
        
        # Extract export configuration
        export_format = data.get('format', 'csv').lower()
        selected_fields = data.get('fields', [])
        filters = data.get('filters', {})
        
        # Validate export format
        if export_format not in ['csv', 'excel', 'pdf']:
            return JsonResponse({'error': 'Invalid export format'}, status=400)
        
        # Validate fields
        if not selected_fields:
            return JsonResponse({'error': 'No fields selected for export'}, status=400)
        
        # Create exporter
        exporter = EOIDataExporter(request.user, export_format)
        
        # Process filters
        processed_filters = {}
        
        # Date filters
        if filters.get('date_from'):
            try:
                processed_filters['date_from'] = datetime.strptime(filters['date_from'], '%Y-%m-%d')
            except ValueError:
                return JsonResponse({'error': 'Invalid date_from format'}, status=400)
        
        if filters.get('date_to'):
            try:
                processed_filters['date_to'] = datetime.strptime(filters['date_to'], '%Y-%m-%d')
            except ValueError:
                return JsonResponse({'error': 'Invalid date_to format'}, status=400)
        
        # Status filter
        if filters.get('status'):
            processed_filters['status'] = filters['status']
        
        # Volunteer type filter
        if filters.get('volunteer_type'):
            processed_filters['volunteer_type'] = filters['volunteer_type']
        
        # Email confirmation filter
        if filters.get('email_confirmed') is not None:
            processed_filters['email_confirmed'] = filters['email_confirmed']
        
        # Completion status filter
        if filters.get('completion_status'):
            processed_filters['completion_status'] = filters['completion_status']
        
        # Search filter
        if filters.get('search'):
            processed_filters['search'] = filters['search'].strip()
        
        # Export data
        response = exporter.export_data(
            filters=processed_filters,
            fields=selected_fields,
            format_type=export_format
        )
        
        # Log successful export
        log_audit_event(
            user=request.user,
            action='EOI_EXPORT_COMPLETED',
            resource_type='EOISubmission',
            resource_id='bulk',
            details={
                'format': export_format,
                'fields_count': len(selected_fields),
                'filters_applied': bool(processed_filters)
            }
        )
        
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return JsonResponse({'error': 'Export failed. Please try again.'}, status=500)


@login_required
@require_http_methods(["GET"])
def export_preview(request):
    """
    Preview export data before downloading
    """
    # Check permissions
    if not IsStaffOrVMTOrCVT().has_permission(request, None):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        # Get query parameters
        fields = request.GET.getlist('fields')
        status_filter = request.GET.getlist('status')
        volunteer_type_filter = request.GET.getlist('volunteer_type')
        search = request.GET.get('search', '').strip()
        
        if not fields:
            return JsonResponse({'error': 'No fields specified'}, status=400)
        
        # Create exporter
        exporter = EOIDataExporter(request.user)
        
        # Build filters
        filters = {}
        if status_filter:
            filters['status'] = status_filter
        if volunteer_type_filter:
            filters['volunteer_type'] = volunteer_type_filter
        if search:
            filters['search'] = search
        
        # Get limited queryset for preview
        queryset = exporter.get_base_queryset(filters)[:10]  # Limit to 10 records
        
        # Extract preview data
        preview_data = []
        field_definitions = exporter.get_field_definitions()
        
        for submission in queryset:
            row_data = exporter.extract_data(submission, fields)
            preview_data.append(row_data)
        
        # Prepare response
        response_data = {
            'headers': [field_definitions[field]['label'] for field in fields],
            'data': preview_data,
            'total_records': exporter.get_base_queryset(filters).count(),
            'preview_count': len(preview_data)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error generating export preview: {e}")
        return JsonResponse({'error': 'Preview failed. Please try again.'}, status=500)


@login_required
@require_http_methods(["GET"])
def export_statistics_api(request):
    """
    API endpoint for export statistics
    """
    # Check permissions
    if not IsStaffOrVMTOrCVT().has_permission(request, None):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        stats = get_export_statistics(request.user)
        return JsonResponse(stats)
    except Exception as e:
        logger.error(f"Error getting export statistics: {e}")
        return JsonResponse({'error': 'Failed to load statistics'}, status=500)


@login_required
@require_http_methods(["GET"])
def quick_export_csv(request):
    """
    Quick CSV export with default fields
    """
    # Check permissions
    if not IsStaffOrVMTOrCVT().has_permission(request, None):
        messages.error(request, _('You do not have permission to export data.'))
        return redirect('volunteers:export_dashboard')
    
    try:
        # Default fields for quick export
        default_fields = [
            'submission_id', 'volunteer_type', 'status', 'created_at',
            'first_name', 'last_name', 'email', 'phone_number',
            'volunteer_experience_level', 'preferred_roles'
        ]
        
        # Create exporter
        exporter = EOIDataExporter(request.user, 'csv')
        
        # Export with default configuration
        response = exporter.export_data(fields=default_fields)
        
        # Log export
        log_audit_event(
            user=request.user,
            action='EOI_QUICK_EXPORT',
            resource_type='EOISubmission',
            resource_id='bulk',
            details={'format': 'csv', 'type': 'quick_export'}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in quick CSV export: {e}")
        messages.error(request, _('Export failed. Please try again.'))
        return redirect('volunteers:export_dashboard')


@login_required
@require_http_methods(["GET"])
def export_template(request):
    """
    Download export template for bulk operations
    """
    # Check permissions
    if not IsStaffOrVMTOrCVT().has_permission(request, None):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        # Create CSV template with headers only
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="eoi_export_template.csv"'
        
        import csv
        writer = csv.writer(response)
        
        # Write headers for common fields
        headers = [
            'Submission ID', 'Volunteer Type', 'Status', 'Created Date',
            'First Name', 'Last Name', 'Email', 'Phone Number',
            'Experience Level', 'Preferred Roles', 'Preferred Venues',
            'T-Shirt Size', 'Dietary Requirements', 'Group Name'
        ]
        
        writer.writerow(headers)
        
        # Write one example row
        example_row = [
            'example-uuid', 'New Volunteer', 'Submitted', '2024-01-01 10:00:00',
            'John', 'Doe', 'john.doe@example.com', '+353 1 234 5678',
            'Beginner', 'Spectator Services, Hospitality', 'Main Stadium',
            'Large', 'Vegetarian', 'Example Group'
        ]
        
        writer.writerow(example_row)
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating export template: {e}")
        return JsonResponse({'error': 'Template generation failed'}, status=500) 