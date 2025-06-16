"""
Mobile-Optimized Admin Views for SOI Hub

This module provides mobile-specific admin views that are optimized for
touch interfaces and smaller screens while maintaining full functionality.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
import json

from accounts.models import User
from events.models import Event, Assignment
from volunteers.models import VolunteerProfile
from tasks.models import Task, TaskCompletion
from common.models import AdminOverride, AuditLog


@staff_member_required
@login_required
def mobile_admin_dashboard(request):
    """
    Mobile-optimized admin dashboard with key metrics and quick actions.
    """
    # Get key statistics
    stats = {
        'total_volunteers': User.objects.filter(user_type='VOLUNTEER').count(),
        'active_events': Event.objects.filter(
            status='ACTIVE',
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).count(),
        'pending_assignments': Assignment.objects.filter(status='PENDING').count(),
        'overdue_tasks': Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['PENDING', 'IN_PROGRESS']
        ).count(),
        'recent_registrations': User.objects.filter(
            user_type='VOLUNTEER',
            date_joined__gte=timezone.now() - timezone.timedelta(days=7)
        ).count(),
        'active_overrides': AdminOverride.objects.filter(
            status='ACTIVE',
            expiry_date__gt=timezone.now()
        ).count(),
    }
    
    # Get recent activity
    recent_activity = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    # Get upcoming events
    upcoming_events = Event.objects.filter(
        start_date__gt=timezone.now()
    ).order_by('start_date')[:5]
    
    # Get recent volunteer registrations
    recent_volunteers = User.objects.filter(
        user_type='VOLUNTEER'
    ).select_related('volunteerprofile').order_by('-date_joined')[:5]
    
    context = {
        'title': 'Mobile Admin Dashboard',
        'stats': stats,
        'recent_activity': recent_activity,
        'upcoming_events': upcoming_events,
        'recent_volunteers': recent_volunteers,
        'is_mobile': True,
    }
    
    return render(request, 'admin/mobile/dashboard.html', context)


@staff_member_required
@login_required
def mobile_volunteer_list(request):
    """
    Mobile-optimized volunteer list with search and filtering.
    """
    volunteers = User.objects.filter(user_type='VOLUNTEER').select_related('volunteerprofile')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        volunteers = volunteers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        volunteers = volunteers.filter(is_active=status_filter == 'active')
    
    # Pagination for mobile
    paginator = Paginator(volunteers, 20)  # Show 20 volunteers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Volunteers',
        'volunteers': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'is_mobile': True,
    }
    
    return render(request, 'admin/mobile/volunteer_list.html', context)


@staff_member_required
@login_required
def mobile_event_list(request):
    """
    Mobile-optimized event list with quick actions.
    """
    events = Event.objects.all().annotate(
        assignment_count=Count('assignment')
    ).order_by('-start_date')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        events = events.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(events, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Events',
        'events': page_obj,
        'status_filter': status_filter,
        'is_mobile': True,
    }
    
    return render(request, 'admin/mobile/event_list.html', context)


@staff_member_required
@login_required
def mobile_assignment_management(request):
    """
    Mobile-optimized assignment management interface.
    """
    assignments = Assignment.objects.select_related(
        'volunteer', 'event', 'role'
    ).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        assignments = assignments.filter(status=status_filter)
    
    # Filter by event
    event_filter = request.GET.get('event', '')
    if event_filter:
        assignments = assignments.filter(event_id=event_filter)
    
    # Pagination
    paginator = Paginator(assignments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get events for filter dropdown
    events = Event.objects.filter(status__in=['ACTIVE', 'UPCOMING']).order_by('name')
    
    context = {
        'title': 'Assignments',
        'assignments': page_obj,
        'events': events,
        'status_filter': status_filter,
        'event_filter': event_filter,
        'is_mobile': True,
    }
    
    return render(request, 'admin/mobile/assignment_list.html', context)


@staff_member_required
@login_required
@require_http_methods(["POST"])
def mobile_quick_action(request):
    """
    Handle quick actions from mobile interface.
    """
    action = request.POST.get('action')
    object_id = request.POST.get('object_id')
    object_type = request.POST.get('object_type')
    
    try:
        if object_type == 'assignment' and action == 'approve':
            assignment = Assignment.objects.get(id=object_id)
            assignment.status = 'CONFIRMED'
            assignment.save()
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='ASSIGNMENT_APPROVED',
                object_type='Assignment',
                object_id=object_id,
                details=f'Assignment approved via mobile interface'
            )
            
            messages.success(request, f'Assignment for {assignment.volunteer.get_full_name()} approved.')
            
        elif object_type == 'assignment' and action == 'reject':
            assignment = Assignment.objects.get(id=object_id)
            assignment.status = 'REJECTED'
            assignment.save()
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='ASSIGNMENT_REJECTED',
                object_type='Assignment',
                object_id=object_id,
                details=f'Assignment rejected via mobile interface'
            )
            
            messages.success(request, f'Assignment for {assignment.volunteer.get_full_name()} rejected.')
            
        elif object_type == 'volunteer' and action == 'activate':
            volunteer = User.objects.get(id=object_id)
            volunteer.is_active = True
            volunteer.save()
            
            messages.success(request, f'Volunteer {volunteer.get_full_name()} activated.')
            
        elif object_type == 'volunteer' and action == 'deactivate':
            volunteer = User.objects.get(id=object_id)
            volunteer.is_active = False
            volunteer.save()
            
            messages.success(request, f'Volunteer {volunteer.get_full_name()} deactivated.')
            
        else:
            messages.error(request, 'Invalid action or object type.')
            
    except Exception as e:
        messages.error(request, f'Error performing action: {str(e)}')
    
    # Return to the referring page
    return redirect(request.META.get('HTTP_REFERER', '/admin/'))


@staff_member_required
@login_required
def mobile_search_api(request):
    """
    API endpoint for mobile search functionality.
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    results = []
    
    if search_type in ['all', 'volunteers']:
        volunteers = User.objects.filter(
            user_type='VOLUNTEER'
        ).filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )[:10]
        
        for volunteer in volunteers:
            results.append({
                'type': 'volunteer',
                'id': volunteer.id,
                'title': volunteer.get_full_name(),
                'subtitle': volunteer.email,
                'url': f'/admin/accounts/user/{volunteer.id}/change/',
                'status': 'Active' if volunteer.is_active else 'Inactive'
            })
    
    if search_type in ['all', 'events']:
        events = Event.objects.filter(
            name__icontains=query
        )[:10]
        
        for event in events:
            results.append({
                'type': 'event',
                'id': event.id,
                'title': event.name,
                'subtitle': f'{event.start_date} - {event.end_date}',
                'url': f'/admin/events/event/{event.id}/change/',
                'status': event.status
            })
    
    if search_type in ['all', 'assignments']:
        assignments = Assignment.objects.select_related(
            'volunteer', 'event'
        ).filter(
            Q(volunteer__first_name__icontains=query) |
            Q(volunteer__last_name__icontains=query) |
            Q(event__name__icontains=query)
        )[:10]
        
        for assignment in assignments:
            results.append({
                'type': 'assignment',
                'id': assignment.id,
                'title': f'{assignment.volunteer.get_full_name()} - {assignment.event.name}',
                'subtitle': f'Role: {assignment.role.name}',
                'url': f'/admin/events/assignment/{assignment.id}/change/',
                'status': assignment.status
            })
    
    return JsonResponse({'results': results})


@staff_member_required
@login_required
def mobile_stats_api(request):
    """
    API endpoint for mobile dashboard statistics.
    """
    stats = {
        'volunteers': {
            'total': User.objects.filter(user_type='VOLUNTEER').count(),
            'active': User.objects.filter(user_type='VOLUNTEER', is_active=True).count(),
            'new_this_week': User.objects.filter(
                user_type='VOLUNTEER',
                date_joined__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        },
        'events': {
            'total': Event.objects.count(),
            'active': Event.objects.filter(status='ACTIVE').count(),
            'upcoming': Event.objects.filter(
                status='UPCOMING',
                start_date__gt=timezone.now()
            ).count(),
        },
        'assignments': {
            'total': Assignment.objects.count(),
            'pending': Assignment.objects.filter(status='PENDING').count(),
            'confirmed': Assignment.objects.filter(status='CONFIRMED').count(),
        },
        'tasks': {
            'total': Task.objects.count(),
            'overdue': Task.objects.filter(
                due_date__lt=timezone.now(),
                status__in=['PENDING', 'IN_PROGRESS']
            ).count(),
            'completed_today': TaskCompletion.objects.filter(
                completed_at__date=timezone.now().date()
            ).count(),
        }
    }
    
    return JsonResponse(stats)


@staff_member_required
@login_required
def mobile_notifications_api(request):
    """
    API endpoint for mobile notifications.
    """
    notifications = []
    
    # Check for overdue tasks
    overdue_tasks = Task.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['PENDING', 'IN_PROGRESS']
    ).count()
    
    if overdue_tasks > 0:
        notifications.append({
            'type': 'warning',
            'title': 'Overdue Tasks',
            'message': f'{overdue_tasks} task(s) are overdue',
            'action_url': '/admin/tasks/task/?status=overdue'
        })
    
    # Check for pending assignments
    pending_assignments = Assignment.objects.filter(status='PENDING').count()
    
    if pending_assignments > 0:
        notifications.append({
            'type': 'info',
            'title': 'Pending Assignments',
            'message': f'{pending_assignments} assignment(s) need review',
            'action_url': '/admin/events/assignment/?status=PENDING'
        })
    
    # Check for active admin overrides
    active_overrides = AdminOverride.objects.filter(
        status='ACTIVE',
        expiry_date__gt=timezone.now()
    ).count()
    
    if active_overrides > 0:
        notifications.append({
            'type': 'warning',
            'title': 'Active Overrides',
            'message': f'{active_overrides} admin override(s) are active',
            'action_url': '/admin/common/adminoverride/?status=ACTIVE'
        })
    
    return JsonResponse({'notifications': notifications})


@staff_member_required
@login_required
def mobile_bulk_actions(request):
    """
    Handle bulk actions from mobile interface.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        object_ids = request.POST.getlist('object_ids')
        object_type = request.POST.get('object_type')
        
        if not object_ids:
            messages.error(request, 'No items selected.')
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))
        
        try:
            if object_type == 'volunteers' and action == 'activate':
                User.objects.filter(id__in=object_ids).update(is_active=True)
                messages.success(request, f'{len(object_ids)} volunteer(s) activated.')
                
            elif object_type == 'volunteers' and action == 'deactivate':
                User.objects.filter(id__in=object_ids).update(is_active=False)
                messages.success(request, f'{len(object_ids)} volunteer(s) deactivated.')
                
            elif object_type == 'assignments' and action == 'approve':
                Assignment.objects.filter(id__in=object_ids).update(status='CONFIRMED')
                messages.success(request, f'{len(object_ids)} assignment(s) approved.')
                
            elif object_type == 'assignments' and action == 'reject':
                Assignment.objects.filter(id__in=object_ids).update(status='REJECTED')
                messages.success(request, f'{len(object_ids)} assignment(s) rejected.')
                
            else:
                messages.error(request, 'Invalid bulk action.')
                
            # Log bulk action
            AuditLog.objects.create(
                user=request.user,
                action=f'BULK_{action.upper()}',
                object_type=object_type,
                details=f'Bulk {action} performed on {len(object_ids)} items via mobile interface'
            )
            
        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', '/admin/'))


# Mobile-specific context processor
def mobile_context(request):
    """
    Add mobile-specific context variables.
    """
    is_mobile = False
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # Simple mobile detection
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
    is_mobile = any(keyword in user_agent for keyword in mobile_keywords)
    
    # Also check screen width if available
    if not is_mobile and 'HTTP_SEC_CH_UA_MOBILE' in request.META:
        is_mobile = request.META['HTTP_SEC_CH_UA_MOBILE'] == '?1'
    
    return {
        'is_mobile': is_mobile,
        'mobile_optimized': True,
        'touch_friendly': is_mobile,
    } 