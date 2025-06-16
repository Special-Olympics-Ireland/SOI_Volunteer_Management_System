"""
URL patterns for Expression of Interest (EOI) system
"""

from django.urls import path
from . import eoi_views

app_name = 'eoi'

urlpatterns = [
    # EOI Form Flow
    path('start/', eoi_views.eoi_start, name='start'),
    path('<uuid:submission_id>/corporate-group/', eoi_views.eoi_corporate_group, name='corporate_group'),
    path('<uuid:submission_id>/profile/', eoi_views.eoi_profile, name='profile'),
    path('<uuid:submission_id>/recruitment/', eoi_views.eoi_recruitment, name='recruitment'),
    path('<uuid:submission_id>/games/', eoi_views.eoi_games, name='games'),
    path('<uuid:submission_id>/review/', eoi_views.eoi_review, name='review'),
    path('<uuid:submission_id>/confirmation/', eoi_views.eoi_confirmation, name='confirmation'),
    
    # AJAX Endpoints
    path('<uuid:submission_id>/status/', eoi_views.eoi_status, name='status'),
    path('api/corporate-groups/', eoi_views.get_corporate_groups, name='corporate_groups_api'),
    path('api/check-justgo/', eoi_views.check_justgo_membership, name='check_justgo'),
    
    # Corporate Group Registration
    path('corporate/register/', eoi_views.corporate_group_register, name='corporate_register'),
    path('corporate/success/', eoi_views.corporate_group_success, name='corporate_success'),
] 