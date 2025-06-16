"""
Admin Help System Views
Provides comprehensive documentation and help for the SOI Hub admin interface.
"""

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from accounts.models import User
from volunteers.models import VolunteerProfile
from events.models import Event, Venue, Role
from tasks.models import Task
from reporting.models import Report


@method_decorator(staff_member_required, name='dispatch')
class HelpIndexView(TemplateView):
    """Main help system index page"""
    template_name = 'admin/help/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'SOI Hub Help System',
            'help_sections': [
                {
                    'title': 'Getting Started',
                    'description': 'Learn the basics of using the admin interface',
                    'url': 'admin:help_getting_started',
                    'icon': '🚀'
                },
                {
                    'title': 'User Management',
                    'description': 'Manage user accounts and permissions',
                    'url': 'admin:help_user_management',
                    'icon': '👥'
                },
                {
                    'title': 'Volunteer Management',
                    'description': 'Handle volunteer applications and profiles',
                    'url': 'admin:help_volunteer_management',
                    'icon': '🤝'
                },
                {
                    'title': 'Event Management',
                    'description': 'Create and manage events, venues, and roles',
                    'url': 'admin:help_event_management',
                    'icon': '📅'
                },
                {
                    'title': 'Task Management',
                    'description': 'Assign and track volunteer tasks',
                    'url': 'admin:help_task_management',
                    'icon': '✅'
                },
                {
                    'title': 'Reporting & Analytics',
                    'description': 'Generate reports and view analytics',
                    'url': 'admin:help_reporting',
                    'icon': '📊'
                },
                {
                    'title': 'System Administration',
                    'description': 'System configuration and maintenance',
                    'url': 'admin:help_system_admin',
                    'icon': '⚙️'
                },
                {
                    'title': 'Troubleshooting',
                    'description': 'Common issues and solutions',
                    'url': 'admin:help_troubleshooting',
                    'icon': '🔧'
                }
            ]
        })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpGettingStartedView(TemplateView):
    """Getting started help page"""
    template_name = 'admin/help/getting_started.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Getting Started with SOI Hub',
            'breadcrumb': 'Getting Started'
        })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpUserManagementView(TemplateView):
    """User management help page"""
    template_name = 'admin/help/user_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update({
                'title': 'User Management Help',
                'breadcrumb': 'User Management',
                'user_types': User.UserType.choices,
                'total_users': User.objects.count(),
                'pending_users': User.objects.filter(is_active=False).count()
            })
        except Exception as e:
            # Fallback context if there are any issues
            context.update({
                'title': 'User Management Help',
                'breadcrumb': 'User Management',
                'user_types': [],
                'total_users': 0,
                'pending_users': 0
            })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpVolunteerManagementView(TemplateView):
    """Volunteer management help page"""
    template_name = 'admin/help/volunteer_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update({
                'title': 'Volunteer Management Help',
                'breadcrumb': 'Volunteer Management',
                'total_volunteers': VolunteerProfile.objects.count(),
                'active_volunteers': VolunteerProfile.objects.filter(status='ACTIVE').count()
            })
        except Exception as e:
            # Fallback context if there are any issues
            context.update({
                'title': 'Volunteer Management Help',
                'breadcrumb': 'Volunteer Management',
                'total_volunteers': 0,
                'active_volunteers': 0
            })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpEventManagementView(TemplateView):
    """Event management help page"""
    template_name = 'admin/help/event_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update({
                'title': 'Event Management Help',
                'breadcrumb': 'Event Management',
                'total_events': Event.objects.count(),
                'total_venues': Venue.objects.count(),
                'total_roles': Role.objects.count()
            })
        except Exception as e:
            # Fallback context if there are any issues
            context.update({
                'title': 'Event Management Help',
                'breadcrumb': 'Event Management',
                'total_events': 0,
                'total_venues': 0,
                'total_roles': 0
            })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpTaskManagementView(TemplateView):
    """Task management help page"""
    template_name = 'admin/help/task_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update({
                'title': 'Task Management Help',
                'breadcrumb': 'Task Management',
                'total_tasks': Task.objects.count(),
                'task_types': Task.TaskType.choices
            })
        except Exception as e:
            # Fallback context if there are any issues
            context.update({
                'title': 'Task Management Help',
                'breadcrumb': 'Task Management',
                'total_tasks': 0,
                'task_types': []
            })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpReportingView(TemplateView):
    """Reporting and analytics help page"""
    template_name = 'admin/help/reporting.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update({
                'title': 'Reporting & Analytics Help',
                'breadcrumb': 'Reporting & Analytics',
                'total_reports': Report.objects.count()
            })
        except Exception as e:
            # Fallback context if there are any issues
            context.update({
                'title': 'Reporting & Analytics Help',
                'breadcrumb': 'Reporting & Analytics',
                'total_reports': 0
            })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpSystemAdminView(TemplateView):
    """System administration help page"""
    template_name = 'admin/help/system_admin.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'System Administration Help',
            'breadcrumb': 'System Administration'
        })
        return context


@method_decorator(staff_member_required, name='dispatch')
class HelpTroubleshootingView(TemplateView):
    """Troubleshooting help page"""
    template_name = 'admin/help/troubleshooting.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Troubleshooting Help',
            'breadcrumb': 'Troubleshooting'
        })
        return context


@staff_member_required
def help_search(request):
    """Search help content"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    # Simple search implementation
    results = []
    
    # Search in help sections
    help_sections = [
        {'title': 'Getting Started', 'url': '/help/getting-started/', 'content': 'admin interface navigation basics'},
        {'title': 'User Management', 'url': '/help/user-management/', 'content': 'user accounts permissions approval'},
        {'title': 'Volunteer Management', 'url': '/help/volunteer-management/', 'content': 'volunteer applications profiles EOI'},
        {'title': 'Event Management', 'url': '/help/event-management/', 'content': 'events venues roles assignments'},
        {'title': 'Task Management', 'url': '/help/task-management/', 'content': 'tasks completion verification'},
        {'title': 'Reporting', 'url': '/help/reporting/', 'content': 'reports analytics statistics'},
        {'title': 'System Administration', 'url': '/help/system-admin/', 'content': 'configuration maintenance'},
        {'title': 'Troubleshooting', 'url': '/help/troubleshooting/', 'content': 'problems solutions errors'},
    ]
    
    query_lower = query.lower()
    for section in help_sections:
        if (query_lower in section['title'].lower() or 
            query_lower in section['content'].lower()):
            results.append({
                'title': section['title'],
                'url': section['url'],
                'excerpt': f"Help with {section['title'].lower()}"
            })
    
    return JsonResponse({'results': results[:10]})


@staff_member_required
def help_feedback(request):
    """Handle help system feedback"""
    if request.method == 'POST':
        feedback_data = {
            'page': request.POST.get('page', ''),
            'rating': request.POST.get('rating', ''),
            'comment': request.POST.get('comment', ''),
            'user': request.user.username,
            'timestamp': timezone.now().isoformat()
        }
        
        # In a real implementation, you would save this to a database
        # For now, we'll just log it
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Help feedback received: {feedback_data}")
        
        return JsonResponse({'status': 'success', 'message': 'Thank you for your feedback!'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}) 