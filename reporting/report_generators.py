"""
Specific report generators for different report types.
Each generator implements the abstract methods from BaseReportGenerator.
"""

from typing import Dict, List, Any, Optional
from django.db.models import QuerySet, Count, Q, Avg, Sum, F
from django.utils import timezone
from datetime import datetime, timedelta

from .base import BaseReportGenerator
from volunteers.models import VolunteerProfile
from events.models import Event, Venue, Role, Assignment
from accounts.models import User
from tasks.models import Task


class VolunteerSummaryReportGenerator(BaseReportGenerator):
    """
    Generate summary report of volunteers with key statistics.
    """
    
    def get_queryset(self) -> QuerySet:
        """Get volunteer queryset with applied filters"""
        queryset = VolunteerProfile.objects.select_related('user')
        
        # Apply filters from parameters
        if self.parameters.get('status'):
            queryset = queryset.filter(status=self.parameters['status'])
        
        if self.parameters.get('role_id'):
            queryset = queryset.filter(roles__id=self.parameters['role_id'])
        
        if self.parameters.get('event_id'):
            queryset = queryset.filter(events__id=self.parameters['event_id'])
        
        if self.parameters.get('venue_id'):
            queryset = queryset.filter(preferred_venues__id=self.parameters['venue_id'])
        
        if self.parameters.get('training_status'):
            if self.parameters['training_status'] == 'completed':
                queryset = queryset.filter(training_completed=True)
            elif self.parameters['training_status'] == 'pending':
                queryset = queryset.filter(training_completed=False)
        
        if self.parameters.get('background_check_status'):
            if self.parameters['background_check_status'] == 'approved':
                queryset = queryset.filter(background_check_status='APPROVED')
            elif self.parameters['background_check_status'] == 'pending':
                queryset = queryset.filter(background_check_status='PENDING')
        
        return queryset.distinct()
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Define columns for volunteer summary report"""
        return [
            {'key': 'volunteer_id', 'label': 'Volunteer ID', 'type': 'text'},
            {'key': 'full_name', 'label': 'Full Name', 'type': 'text'},
            {'key': 'email', 'label': 'Email', 'type': 'text'},
            {'key': 'phone', 'label': 'Phone', 'type': 'text'},
            {'key': 'status', 'label': 'Status', 'type': 'text'},
            {'key': 'roles', 'label': 'Roles', 'type': 'text'},
            {'key': 'events_count', 'label': 'Events Assigned', 'type': 'number'},
            {'key': 'training_status', 'label': 'Training Status', 'type': 'text'},
            {'key': 'background_check', 'label': 'Background Check', 'type': 'text'},
            {'key': 'registration_date', 'label': 'Registration Date', 'type': 'date'},
            {'key': 'last_activity', 'label': 'Last Activity', 'type': 'datetime'},
        ]
    
    def format_row_data(self, volunteer: VolunteerProfile) -> List[Any]:
        """Format volunteer data for export"""
        return [
            getattr(volunteer, 'volunteer_id', str(volunteer.id)),
            volunteer.user.get_full_name(),
            volunteer.user.email,
            getattr(volunteer, 'phone_number', ''),
            getattr(volunteer, 'status', 'Unknown'),
            '',  # Roles - simplified for now
            0,   # Events count - simplified for now
            'Unknown',  # Training status - simplified for now
            'Unknown',  # Background check - simplified for now
            volunteer.created_at.date(),
            volunteer.updated_at,
        ]


class VolunteerDetailedReportGenerator(BaseReportGenerator):
    """
    Generate detailed report of volunteers with comprehensive information.
    """
    
    def get_queryset(self) -> QuerySet:
        """Get volunteer queryset with comprehensive data"""
        queryset = VolunteerProfile.objects.select_related('user')
        
        # Apply same filters as summary report
        if self.parameters.get('status'):
            queryset = queryset.filter(status=self.parameters['status'])
        
        if self.parameters.get('role_id'):
            queryset = queryset.filter(roles__id=self.parameters['role_id'])
        
        if self.parameters.get('event_id'):
            queryset = queryset.filter(events__id=self.parameters['event_id'])
        
        return queryset.distinct()
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Define columns for detailed volunteer report"""
        return [
            {'key': 'volunteer_id', 'label': 'Volunteer ID', 'type': 'text'},
            {'key': 'full_name', 'label': 'Full Name', 'type': 'text'},
            {'key': 'email', 'label': 'Email', 'type': 'text'},
            {'key': 'phone', 'label': 'Phone', 'type': 'text'},
            {'key': 'address', 'label': 'Address', 'type': 'text'},
            {'key': 'date_of_birth', 'label': 'Date of Birth', 'type': 'date'},
            {'key': 'gender', 'label': 'Gender', 'type': 'text'},
            {'key': 'status', 'label': 'Status', 'type': 'text'},
            {'key': 'roles', 'label': 'Roles', 'type': 'text'},
            {'key': 'skills', 'label': 'Skills', 'type': 'text'},
            {'key': 'preferred_venues', 'label': 'Preferred Venues', 'type': 'text'},
            {'key': 'events_assigned', 'label': 'Events Assigned', 'type': 'text'},
            {'key': 'training_status', 'label': 'Training Status', 'type': 'text'},
            {'key': 'background_check', 'label': 'Background Check', 'type': 'text'},
            {'key': 'emergency_contact', 'label': 'Emergency Contact', 'type': 'text'},
            {'key': 'dietary_requirements', 'label': 'Dietary Requirements', 'type': 'text'},
            {'key': 'accessibility_needs', 'label': 'Accessibility Needs', 'type': 'text'},
            {'key': 'registration_date', 'label': 'Registration Date', 'type': 'date'},
            {'key': 'last_activity', 'label': 'Last Activity', 'type': 'datetime'},
        ]
    
    def format_row_data(self, volunteer: VolunteerProfile) -> List[Any]:
        """Format detailed volunteer data for export"""
        return [
            getattr(volunteer, 'volunteer_id', str(volunteer.id)),
            volunteer.user.get_full_name(),
            volunteer.user.email,
            getattr(volunteer, 'phone_number', ''),
            getattr(volunteer, 'address', ''),
            getattr(volunteer, 'date_of_birth', None),
            getattr(volunteer, 'gender', ''),
            getattr(volunteer, 'status', 'Unknown'),
            '',  # Roles - simplified
            '',  # Skills - simplified
            '',  # Preferred venues - simplified
            '',  # Events assigned - simplified
            'Unknown',  # Training status - simplified
            'Unknown',  # Background check - simplified
            getattr(volunteer, 'emergency_contact_name', ''),
            getattr(volunteer, 'dietary_requirements', ''),
            getattr(volunteer, 'accessibility_needs', ''),
            volunteer.created_at.date(),
            volunteer.updated_at,
        ]


class EventSummaryReportGenerator(BaseReportGenerator):
    """
    Generate summary report of events with key statistics.
    """
    
    def get_queryset(self) -> QuerySet:
        """Get event queryset with applied filters"""
        queryset = Event.objects.select_related('venue').prefetch_related(
            'volunteers', 'roles'
        ).annotate(
            volunteer_count=Count('volunteers'),
            role_count=Count('roles')
        )
        
        # Apply filters from parameters
        if self.parameters.get('status'):
            queryset = queryset.filter(status=self.parameters['status'])
        
        if self.parameters.get('venue_id'):
            queryset = queryset.filter(venue_id=self.parameters['venue_id'])
        
        if self.parameters.get('date_from'):
            queryset = queryset.filter(start_date__gte=self.parameters['date_from'])
        
        if self.parameters.get('date_to'):
            queryset = queryset.filter(end_date__lte=self.parameters['date_to'])
        
        if self.parameters.get('event_type'):
            queryset = queryset.filter(event_type=self.parameters['event_type'])
        
        return queryset
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Define columns for event summary report"""
        return [
            {'key': 'event_id', 'label': 'Event ID', 'type': 'text'},
            {'key': 'name', 'label': 'Event Name', 'type': 'text'},
            {'key': 'event_type', 'label': 'Event Type', 'type': 'text'},
            {'key': 'status', 'label': 'Status', 'type': 'text'},
            {'key': 'venue', 'label': 'Venue', 'type': 'text'},
            {'key': 'start_date', 'label': 'Start Date', 'type': 'datetime'},
            {'key': 'end_date', 'label': 'End Date', 'type': 'datetime'},
            {'key': 'volunteer_count', 'label': 'Volunteers Assigned', 'type': 'number'},
            {'key': 'roles_count', 'label': 'Roles Available', 'type': 'number'},
            {'key': 'capacity', 'label': 'Capacity', 'type': 'number'},
            {'key': 'created_date', 'label': 'Created Date', 'type': 'date'},
        ]
    
    def format_row_data(self, event: Event) -> List[Any]:
        """Format event data for export"""
        return [
            event.event_id,
            event.name,
            event.get_event_type_display(),
            event.get_status_display(),
            event.venue.name if event.venue else '',
            event.start_date,
            event.end_date,
            event.volunteer_count,
            event.role_count,
            event.capacity or 0,
            event.created_at.date(),
        ]


class VenueUtilizationReportGenerator(BaseReportGenerator):
    """
    Generate venue utilization report showing usage statistics.
    """
    
    def get_queryset(self) -> QuerySet:
        """Get venue queryset with utilization data"""
        queryset = Venue.objects.prefetch_related('events').annotate(
            total_events=Count('events'),
            active_events=Count('events', filter=Q(events__status='ACTIVE')),
            total_volunteers=Count('events__volunteers', distinct=True)
        )
        
        # Apply filters from parameters
        if self.parameters.get('venue_type'):
            queryset = queryset.filter(venue_type=self.parameters['venue_type'])
        
        if self.parameters.get('location'):
            queryset = queryset.filter(location__icontains=self.parameters['location'])
        
        return queryset
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Define columns for venue utilization report"""
        return [
            {'key': 'venue_id', 'label': 'Venue ID', 'type': 'text'},
            {'key': 'name', 'label': 'Venue Name', 'type': 'text'},
            {'key': 'venue_type', 'label': 'Venue Type', 'type': 'text'},
            {'key': 'location', 'label': 'Location', 'type': 'text'},
            {'key': 'capacity', 'label': 'Capacity', 'type': 'number'},
            {'key': 'total_events', 'label': 'Total Events', 'type': 'number'},
            {'key': 'active_events', 'label': 'Active Events', 'type': 'number'},
            {'key': 'total_volunteers', 'label': 'Total Volunteers', 'type': 'number'},
            {'key': 'utilization_rate', 'label': 'Utilization Rate %', 'type': 'percentage'},
            {'key': 'accessibility_features', 'label': 'Accessibility Features', 'type': 'text'},
        ]
    
    def format_row_data(self, venue: Venue) -> List[Any]:
        """Format venue utilization data for export"""
        # Calculate utilization rate (simplified)
        utilization_rate = 0
        if venue.capacity and venue.capacity > 0:
            utilization_rate = min(100, (venue.total_volunteers / venue.capacity) * 100)
        
        return [
            venue.venue_id,
            venue.name,
            venue.get_venue_type_display(),
            venue.location,
            venue.capacity or 0,
            venue.total_events,
            venue.active_events,
            venue.total_volunteers,
            round(utilization_rate, 2),
            venue.accessibility_features or '',
        ]


class RoleAssignmentReportGenerator(BaseReportGenerator):
    """
    Generate role assignment report showing volunteer-role mappings.
    """
    
    def get_queryset(self) -> QuerySet:
        """Get role assignment data"""
        # Get all volunteer-role relationships through events
        queryset = Assignment.objects.select_related(
            'volunteer__user', 'event', 'role'
        )
        
        # Apply filters from parameters
        if self.parameters.get('event_id'):
            queryset = queryset.filter(event_id=self.parameters['event_id'])
        
        if self.parameters.get('role_id'):
            queryset = queryset.filter(role_id=self.parameters['role_id'])
        
        if self.parameters.get('volunteer_status'):
            queryset = queryset.filter(volunteer__status=self.parameters['volunteer_status'])
        
        return queryset
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Define columns for role assignment report"""
        return [
            {'key': 'volunteer_name', 'label': 'Volunteer Name', 'type': 'text'},
            {'key': 'volunteer_id', 'label': 'Volunteer ID', 'type': 'text'},
            {'key': 'event_name', 'label': 'Event Name', 'type': 'text'},
            {'key': 'role_name', 'label': 'Role Name', 'type': 'text'},
            {'key': 'assignment_status', 'label': 'Assignment Status', 'type': 'text'},
            {'key': 'assigned_date', 'label': 'Assigned Date', 'type': 'date'},
            {'key': 'shift_start', 'label': 'Shift Start', 'type': 'datetime'},
            {'key': 'shift_end', 'label': 'Shift End', 'type': 'datetime'},
            {'key': 'hours', 'label': 'Hours', 'type': 'number'},
        ]
    
    def format_row_data(self, assignment: Assignment) -> List[Any]:
        """Format role assignment data for export"""
        hours = 0
        # Simplified for now - using available fields
        
        return [
            getattr(assignment.volunteer, 'user', {}).get('get_full_name', lambda: 'Unknown')() if hasattr(assignment, 'volunteer') else 'Unknown',
            getattr(assignment.volunteer, 'volunteer_id', 'Unknown') if hasattr(assignment, 'volunteer') else 'Unknown',
            assignment.event.name if hasattr(assignment, 'event') else 'Unknown',
            assignment.role.name if hasattr(assignment, 'role') and assignment.role else '',
            getattr(assignment, 'status', 'Unknown'),
            assignment.created_at.date() if hasattr(assignment, 'created_at') else '',
            None,  # Shift start - simplified
            None,  # Shift end - simplified
            hours,
        ]


class TrainingStatusReportGenerator(BaseReportGenerator):
    """
    Generate training status report for volunteers.
    """
    
    def get_queryset(self) -> QuerySet:
        """Get volunteer training data"""
        queryset = VolunteerProfile.objects.select_related('user')
        
        # Apply filters from parameters
        if self.parameters.get('training_status'):
            if self.parameters['training_status'] == 'completed':
                queryset = queryset.filter(training_completed=True)
            elif self.parameters['training_status'] == 'pending':
                queryset = queryset.filter(training_completed=False)
        
        if self.parameters.get('role_id'):
            queryset = queryset.filter(roles__id=self.parameters['role_id'])
        
        return queryset.distinct()
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Define columns for training status report"""
        return [
            {'key': 'volunteer_name', 'label': 'Volunteer Name', 'type': 'text'},
            {'key': 'volunteer_id', 'label': 'Volunteer ID', 'type': 'text'},
            {'key': 'email', 'label': 'Email', 'type': 'text'},
            {'key': 'roles', 'label': 'Roles', 'type': 'text'},
            {'key': 'training_status', 'label': 'Training Status', 'type': 'text'},
            {'key': 'training_completed_date', 'label': 'Training Completed Date', 'type': 'date'},
            {'key': 'training_expiry_date', 'label': 'Training Expiry Date', 'type': 'date'},
            {'key': 'certification_number', 'label': 'Certification Number', 'type': 'text'},
            {'key': 'training_provider', 'label': 'Training Provider', 'type': 'text'},
        ]
    
    def format_row_data(self, volunteer: VolunteerProfile) -> List[Any]:
        """Format training status data for export"""
        return [
            volunteer.user.get_full_name(),
            getattr(volunteer, 'volunteer_id', str(volunteer.id)),
            volunteer.user.email,
            '',  # Roles - simplified
            'Unknown',  # Training status - simplified
            None,  # Training completed date
            None,  # Training expiry date
            '',  # Certification number
            '',  # Training provider
        ]


# Report generator registry
REPORT_GENERATORS = {
    'VOLUNTEER_SUMMARY': VolunteerSummaryReportGenerator,
    'VOLUNTEER_DETAILED': VolunteerDetailedReportGenerator,
    'EVENT_SUMMARY': EventSummaryReportGenerator,
    'VENUE_UTILIZATION': VenueUtilizationReportGenerator,
    'ROLE_ASSIGNMENT': RoleAssignmentReportGenerator,
    'TRAINING_STATUS': TrainingStatusReportGenerator,
}


def get_report_generator_class(report_type: str):
    """Get the appropriate report generator class for a report type"""
    return REPORT_GENERATORS.get(report_type) 