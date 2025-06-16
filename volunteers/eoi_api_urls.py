"""
EOI API URL Configuration for ISG 2026 Volunteer Management System

This module defines the URL patterns for the EOI REST API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .eoi_api_views import (
    EOISubmissionListCreateAPIView,
    EOISubmissionDetailAPIView,
    CorporateVolunteerGroupListCreateAPIView,
    CorporateVolunteerGroupDetailAPIView,
    eoi_stats_api_view,
    bulk_update_eoi_status,
    eoi_submission_status_check,
    resend_confirmation_email
)

app_name = 'eoi_api'

urlpatterns = [
    # EOI Submission endpoints
    path('submissions/', EOISubmissionListCreateAPIView.as_view(), name='submission-list-create'),
    path('submissions/<uuid:pk>/', EOISubmissionDetailAPIView.as_view(), name='submission-detail'),
    path('submissions/<uuid:submission_id>/status/', eoi_submission_status_check, name='submission-status-check'),
    path('submissions/<uuid:submission_id>/resend-email/', resend_confirmation_email, name='resend-confirmation-email'),
    
    # Corporate Group endpoints
    path('corporate-groups/', CorporateVolunteerGroupListCreateAPIView.as_view(), name='corporate-group-list-create'),
    path('corporate-groups/<uuid:pk>/', CorporateVolunteerGroupDetailAPIView.as_view(), name='corporate-group-detail'),
    
    # Statistics and bulk operations
    path('stats/', eoi_stats_api_view, name='eoi-stats'),
    path('bulk-update-status/', bulk_update_eoi_status, name='bulk-update-status'),
] 