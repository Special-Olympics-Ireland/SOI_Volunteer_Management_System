"""
URL patterns for the admin help system
"""

from django.urls import path
from . import help_views

app_name = 'help'

urlpatterns = [
    # Main help pages
    path('', help_views.HelpIndexView.as_view(), name='index'),
    path('getting-started/', help_views.HelpGettingStartedView.as_view(), name='getting_started'),
    path('user-management/', help_views.HelpUserManagementView.as_view(), name='user_management'),
    path('volunteer-management/', help_views.HelpVolunteerManagementView.as_view(), name='volunteer_management'),
    path('event-management/', help_views.HelpEventManagementView.as_view(), name='event_management'),
    path('task-management/', help_views.HelpTaskManagementView.as_view(), name='task_management'),
    path('reporting/', help_views.HelpReportingView.as_view(), name='reporting'),
    path('system-admin/', help_views.HelpSystemAdminView.as_view(), name='system_admin'),
    path('troubleshooting/', help_views.HelpTroubleshootingView.as_view(), name='troubleshooting'),
    
    # AJAX endpoints
    path('search/', help_views.help_search, name='search'),
    path('feedback/', help_views.help_feedback, name='feedback'),
] 