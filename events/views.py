from django.shortcuts import render
from rest_framework import generics, viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.exceptions import ValidationError

from .models import Event, Venue, Role, Assignment
from .serializers import (
    EventListSerializer, EventDetailSerializer, EventCreateSerializer,
    EventUpdateSerializer, EventConfigurationSerializer, EventStatusSerializer,
    EventStatsSerializer, VenueListSerializer, VenueDetailSerializer,
    VenueCreateSerializer, VenueUpdateSerializer, VenueStatsSerializer,
    RoleListSerializer, RoleDetailSerializer, RoleCreateSerializer,
    RoleUpdateSerializer, RoleStatusSerializer, RoleCapacitySerializer,
    AssignmentListSerializer, AssignmentCreateSerializer, AssignmentUpdateSerializer,
    AssignmentStatusSerializer, AssignmentWorkflowSerializer, AssignmentAttendanceSerializer,
    AssignmentBulkSerializer, AssignmentStatsSerializer
)
from .permissions import IsEventManager
from accounts.permissions import CanManageEvents
from common.permissions import EventManagementPermission
from common.audit_service import AdminAuditService

# Initialize audit service
audit_service = AdminAuditService()


class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Event management with full CRUD operations.
    
    Provides:
    - List events with filtering and search
    - Create new events
    - Retrieve event details
    - Update events
    - Delete events
    - Custom actions for configuration, status, and statistics
    """
    queryset = Event.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'event_type', 'is_active', 'is_public', 'is_featured']
    search_fields = ['name', 'short_name', 'description', 'host_city', 'host_country']
    ordering_fields = ['name', 'start_date', 'end_date', 'created_at', 'volunteer_target']
    ordering = ['-start_date', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return EventListSerializer
        elif self.action == 'create':
            return EventCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EventUpdateSerializer
        elif self.action == 'configuration':
            return EventConfigurationSerializer
        elif self.action == 'status':
            return EventStatusSerializer
        elif self.action == 'stats':
            return EventStatsSerializer
        else:
            return EventDetailSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action in ['list', 'retrieve']:
            # Public read access for active events
            permission_classes = [permissions.AllowAny]
        else:
            # Write operations require event management permissions
            permission_classes = [EventManagementPermission]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and request parameters"""
        queryset = Event.objects.all()
        
        # For non-authenticated users or public access, show only public events
        if not self.request.user.is_authenticated or self.action in ['list', 'retrieve']:
            if not (self.request.user.is_authenticated and 
                   (self.request.user.is_staff or self.request.user.is_superuser)):
                queryset = queryset.filter(is_public=True, is_active=True)
        
        # Add select_related and prefetch_related for performance
        queryset = queryset.select_related('created_by').prefetch_related(
            'event_managers', 'venues', 'roles'
        )
        
        return queryset
    
    def perform_create(self, serializer):
        """Create event with audit logging"""
        event = serializer.save()
        
        # Log event creation
        audit_service.log_event_management_operation(
            operation='EVENT_CREATED',
            user=self.request.user,
            event=event,
            details={
                'event_name': event.name,
                'event_type': event.event_type,
                'start_date': event.start_date.isoformat(),
                'end_date': event.end_date.isoformat(),
                'volunteer_target': event.volunteer_target,
                'via_api': True
            }
        )
    
    def perform_update(self, serializer):
        """Update event with audit logging"""
        old_instance = self.get_object()
        old_data = {
            'name': old_instance.name,
            'status': old_instance.status,
            'volunteer_target': old_instance.volunteer_target,
            'is_active': old_instance.is_active
        }
        
        event = serializer.save()
        
        # Log event update
        audit_service.log_event_management_operation(
            operation='EVENT_UPDATED',
            user=self.request.user,
            event=event,
            details={
                'event_name': event.name,
                'old_data': old_data,
                'changes': serializer.validated_data,
                'via_api': True
            }
        )
    
    def perform_destroy(self, instance):
        """Delete event with audit logging"""
        audit_service.log_event_management_operation(
            operation='EVENT_DELETED',
            user=self.request.user,
            event=instance,
            details={
                'event_name': instance.name,
                'event_type': instance.event_type,
                'status': instance.status,
                'venue_count': instance.get_venue_count(),
                'role_count': instance.get_role_count(),
                'volunteer_count': instance.get_volunteer_count(),
                'via_api': True
            }
        )
        instance.delete()
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def configuration(self, request, pk=None):
        """
        Manage event configuration JSON fields.
        
        GET: Retrieve current configuration
        PUT/PATCH: Update configuration
        """
        event = self.get_object()
        
        if request.method == 'GET':
            serializer = EventConfigurationSerializer(event)
            return Response(serializer.data)
        
        else:
            serializer = EventConfigurationSerializer(
                event, data=request.data, partial=(request.method == 'PATCH')
            )
            if serializer.is_valid():
                old_config = {
                    'event_configuration': event.event_configuration,
                    'volunteer_configuration': event.volunteer_configuration,
                    'venue_configuration': event.venue_configuration,
                    'role_configuration': event.role_configuration
                }
                
                serializer.save()
                
                # Log configuration update
                audit_service.log_event_management_operation(
                    operation='EVENT_CONFIGURATION_UPDATED',
                    user=request.user,
                    event=event,
                    details={
                        'event_name': event.name,
                        'old_configuration': old_config,
                        'new_configuration': serializer.validated_data,
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'put'])
    def status(self, request, pk=None):
        """
        Manage event status.
        
        GET: Get current status
        PUT: Change status
        """
        event = self.get_object()
        
        if request.method == 'GET':
            return Response({
                'status': event.status,
                'status_changed_at': event.status_changed_at,
                'status_changed_by': event.status_changed_by.get_full_name() if event.status_changed_by else None,
                'available_statuses': [choice[0] for choice in Event.EventStatus.choices]
            })
        
        else:
            serializer = EventStatusSerializer(
                event, data=request.data, context={'request': request}
            )
            if serializer.is_valid():
                old_status = event.status
                serializer.save()
                
                # Log status change
                audit_service.log_event_management_operation(
                    operation='EVENT_STATUS_CHANGED',
                    user=request.user,
                    event=event,
                    details={
                        'event_name': event.name,
                        'old_status': old_status,
                        'new_status': event.status,
                        'notes': request.data.get('status_change_notes', ''),
                        'via_api': True
                    }
                )
                
                return Response({
                    'status': event.status,
                    'status_changed_at': event.status_changed_at,
                    'status_changed_by': event.status_changed_by.get_full_name() if event.status_changed_by else None,
                    'message': f'Event status changed to {event.get_status_display()}'
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get event statistics and analytics"""
        event = self.get_object()
        serializer = EventStatsSerializer(event)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def venues(self, request, pk=None):
        """Get all venues for this event"""
        event = self.get_object()
        venues = event.venues.all()
        serializer = VenueListSerializer(venues, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def roles(self, request, pk=None):
        """Get all roles for this event"""
        event = self.get_object()
        roles = event.roles.all()
        # Would need RoleListSerializer - will implement in next sub-task
        return Response({'message': 'Role serializer will be implemented in next sub-task'})
    
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """Get all assignments for this event"""
        event = self.get_object()
        assignments = event.assignments.all()
        # Would need AssignmentListSerializer - will implement in next sub-task
        return Response({'message': 'Assignment serializer will be implemented in next sub-task'})
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured events"""
        events = self.get_queryset().filter(is_featured=True, is_active=True)
        serializer = EventListSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming events"""
        today = timezone.now().date()
        events = self.get_queryset().filter(
            start_date__gte=today, is_active=True
        ).order_by('start_date')
        serializer = EventListSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active/ongoing events"""
        today = timezone.now().date()
        events = self.get_queryset().filter(
            start_date__lte=today, end_date__gte=today, is_active=True
        )
        serializer = EventListSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)


class VenueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Venue management with full CRUD operations.
    
    Provides:
    - List venues with filtering and search
    - Create new venues
    - Retrieve venue details
    - Update venues
    - Delete venues
    - Custom actions for statistics and capacity management
    """
    queryset = Venue.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event', 'venue_type', 'status', 'city', 'country', 'accessibility_level', 'is_active']
    search_fields = ['name', 'short_name', 'description', 'address_line_1', 'city']
    ordering_fields = ['name', 'venue_type', 'total_capacity', 'volunteer_capacity', 'created_at']
    ordering = ['event', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return VenueListSerializer
        elif self.action == 'create':
            return VenueCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VenueUpdateSerializer
        elif self.action == 'stats':
            return VenueStatsSerializer
        else:
            return VenueDetailSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action in ['list', 'retrieve']:
            # Public read access for active venues
            permission_classes = [permissions.AllowAny]
        else:
            # Write operations require event management permissions
            permission_classes = [EventManagementPermission]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = Venue.objects.all()
        
        # For non-authenticated users, show only active venues from public events
        if not self.request.user.is_authenticated or self.action in ['list', 'retrieve']:
            if not (self.request.user.is_authenticated and 
                   (self.request.user.is_staff or self.request.user.is_superuser)):
                queryset = queryset.filter(
                    is_active=True, 
                    event__is_public=True, 
                    event__is_active=True
                )
        
        # Add select_related for performance
        queryset = queryset.select_related('event', 'created_by').prefetch_related(
            'venue_coordinators', 'roles'
        )
        
        return queryset
    
    def perform_create(self, serializer):
        """Create venue with audit logging"""
        venue = serializer.save()
        
        # Log venue creation
        audit_service.log_event_management_operation(
            operation='VENUE_CREATED',
            user=self.request.user,
            event=venue.event,
            details={
                'venue_id': str(venue.id),
                'venue_name': venue.name,
                'venue_type': venue.venue_type,
                'event_name': venue.event.name,
                'total_capacity': venue.total_capacity,
                'volunteer_capacity': venue.volunteer_capacity,
                'via_api': True
            }
        )
    
    def perform_update(self, serializer):
        """Update venue with audit logging"""
        old_instance = self.get_object()
        old_data = {
            'name': old_instance.name,
            'status': old_instance.status,
            'total_capacity': old_instance.total_capacity,
            'volunteer_capacity': old_instance.volunteer_capacity,
            'is_active': old_instance.is_active
        }
        
        venue = serializer.save()
        
        # Log venue update
        audit_service.log_event_management_operation(
            operation='VENUE_UPDATED',
            user=self.request.user,
            event=venue.event,
            details={
                'venue_id': str(venue.id),
                'venue_name': venue.name,
                'event_name': venue.event.name,
                'old_data': old_data,
                'changes': serializer.validated_data,
                'via_api': True
            }
        )
    
    def perform_destroy(self, instance):
        """Delete venue with audit logging"""
        audit_service.log_event_management_operation(
            operation='VENUE_DELETED',
            user=self.request.user,
            event=instance.event,
            details={
                'venue_id': str(instance.id),
                'venue_name': instance.name,
                'venue_type': instance.venue_type,
                'event_name': instance.event.name,
                'role_count': instance.get_role_count(),
                'assigned_volunteers': instance.get_assigned_volunteer_count(),
                'via_api': True
            }
        )
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get venue statistics and analytics"""
        venue = self.get_object()
        serializer = VenueStatsSerializer(venue)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def capacity(self, request, pk=None):
        """Get venue capacity information"""
        venue = self.get_object()
        return Response({
            'venue_id': str(venue.id),
            'venue_name': venue.name,
            'total_capacity': venue.total_capacity,
            'volunteer_capacity': venue.volunteer_capacity,
            'spectator_capacity': venue.spectator_capacity,
            'assigned_volunteers': venue.get_assigned_volunteer_count(),
            'available_capacity': venue.get_available_capacity(),
            'utilization_percentage': venue.get_capacity_utilization(),
            'is_at_capacity': venue.is_at_capacity(),
            'can_accommodate_more': venue.can_accommodate_volunteers()
        })
    
    @action(detail=True, methods=['get'])
    def roles(self, request, pk=None):
        """Get all roles for this venue"""
        venue = self.get_object()
        roles = venue.roles.all()
        # Would need RoleListSerializer - will implement in next sub-task
        return Response({'message': 'Role serializer will be implemented in next sub-task'})
    
    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get venues filtered by event"""
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        venues = self.get_queryset().filter(event_id=event_id)
        serializer = VenueListSerializer(venues, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def accessible(self, request):
        """Get venues with accessibility features"""
        venues = self.get_queryset().filter(
            Q(accessibility_level__in=['FULL', 'PARTIAL']) |
            Q(wheelchair_accessible=True) |
            Q(accessible_parking=True) |
            Q(accessible_toilets=True)
        )
        serializer = VenueListSerializer(venues, many=True, context={'request': request})
        return Response(serializer.data)


# Additional API Views for specific event management operations

class EventVenuesView(generics.ListAPIView):
    """List all venues for a specific event"""
    serializer_class = VenueListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        event_id = self.kwargs['event_id']
        return Venue.objects.filter(event_id=event_id, is_active=True)


class EventRolesView(generics.ListAPIView):
    """List all roles for a specific event"""
    serializer_class = RoleListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        event_id = self.kwargs['event_id']
        return Role.objects.filter(event_id=event_id, is_public=True, status='ACTIVE')


class EventAssignmentsView(generics.ListAPIView):
    """List all assignments for a specific event"""
    serializer_class = AssignmentListSerializer
    permission_classes = [EventManagementPermission]
    
    def get_queryset(self):
        event_id = self.kwargs['event_id']
        return Assignment.objects.filter(event_id=event_id).select_related(
            'volunteer', 'role', 'venue', 'assigned_by'
        )


class VenueRolesView(generics.ListAPIView):
    """List all roles for a specific venue"""
    serializer_class = RoleListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        venue_id = self.kwargs['venue_id']
        return Role.objects.filter(venue_id=venue_id, is_public=True, status='ACTIVE')


class VenueCapacityView(generics.RetrieveAPIView):
    """Get venue capacity information"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, venue_id):
        try:
            venue = Venue.objects.get(id=venue_id)
            return Response({
                'venue_id': str(venue.id),
                'venue_name': venue.name,
                'total_capacity': venue.total_capacity,
                'volunteer_capacity': venue.volunteer_capacity,
                'spectator_capacity': venue.spectator_capacity,
                'assigned_volunteers': venue.get_assigned_volunteer_count(),
                'available_capacity': venue.get_available_capacity(),
                'utilization_percentage': venue.get_capacity_utilization(),
                'is_at_capacity': venue.is_at_capacity()
            })
        except Venue.DoesNotExist:
            return Response(
                {'error': 'Venue not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


# Bulk Operations Views

class BulkEventOperationsView(generics.GenericAPIView):
    """Handle bulk operations on events"""
    permission_classes = [EventManagementPermission]
    
    def post(self, request):
        """
        Perform bulk operations on events.
        
        Expected payload:
        {
            "operation": "activate|deactivate|delete|update_status",
            "event_ids": ["uuid1", "uuid2", ...],
            "data": {...}  # Additional data for the operation
        }
        """
        operation = request.data.get('operation')
        event_ids = request.data.get('event_ids', [])
        operation_data = request.data.get('data', {})
        
        if not operation or not event_ids:
            return Response(
                {'error': 'operation and event_ids are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        events = Event.objects.filter(id__in=event_ids)
        if not events.exists():
            return Response(
                {'error': 'No events found with provided IDs'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        results = []
        
        for event in events:
            try:
                if operation == 'activate':
                    event.activate(activated_by=request.user)
                    results.append({'id': str(event.id), 'status': 'activated'})
                
                elif operation == 'deactivate':
                    reason = operation_data.get('reason', 'Bulk deactivation')
                    event.deactivate(deactivated_by=request.user, reason=reason)
                    results.append({'id': str(event.id), 'status': 'deactivated'})
                
                elif operation == 'update_status':
                    new_status = operation_data.get('status')
                    if new_status:
                        notes = operation_data.get('notes', 'Bulk status update')
                        event.change_status(new_status, changed_by=request.user, notes=notes)
                        results.append({'id': str(event.id), 'status': f'updated to {new_status}'})
                    else:
                        results.append({'id': str(event.id), 'error': 'status required for update_status operation'})
                
                elif operation == 'delete':
                    event_name = event.name
                    event.delete()
                    results.append({'id': str(event.id), 'status': f'deleted ({event_name})'})
                
                else:
                    results.append({'id': str(event.id), 'error': f'Unknown operation: {operation}'})
            
            except Exception as e:
                results.append({'id': str(event.id), 'error': str(e)})
        
        # Log bulk operation
        audit_service.log_bulk_operations(
            user=request.user,
            operation=f'BULK_EVENT_{operation.upper()}',
            resource_type='Event',
            resource_count=len(event_ids),
            details={
                'operation': operation,
                'event_ids': event_ids,
                'operation_data': operation_data,
                'results': results,
                'via_api': True
            }
        )
        
        return Response({
            'operation': operation,
            'processed': len(results),
            'results': results
        })


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Role management with full CRUD operations and capacity tracking.
    
    Provides:
    - List roles with filtering and search
    - Create new roles
    - Retrieve role details
    - Update roles
    - Delete roles
    - Custom actions for capacity management, status, and statistics
    """
    queryset = Role.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'event', 'venue', 'role_type', 'status', 'skill_level_required',
        'commitment_level', 'is_featured', 'is_urgent', 'is_public',
        'training_required', 'requires_garda_vetting', 'requires_child_protection',
        'requires_security_clearance', 'priority_level'
    ]
    search_fields = ['name', 'short_name', 'description', 'summary', 'role_type']
    ordering_fields = [
        'name', 'role_type', 'priority_level', 'total_positions', 'filled_positions',
        'minimum_age', 'application_deadline', 'created_at'
    ]
    ordering = ['event', 'venue', 'priority_level', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return RoleListSerializer
        elif self.action == 'create':
            return RoleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RoleUpdateSerializer
        elif self.action == 'status':
            return RoleStatusSerializer
        elif self.action == 'capacity':
            return RoleCapacitySerializer
        else:
            return RoleDetailSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action in ['list', 'retrieve']:
            # Public read access for active roles
            permission_classes = [permissions.AllowAny]
        else:
            # Write operations require event management permissions
            permission_classes = [EventManagementPermission]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions and request parameters"""
        queryset = Role.objects.all()
        
        # For non-authenticated users or public access, show only public roles
        if not self.request.user.is_authenticated or self.action in ['list', 'retrieve']:
            if not (self.request.user.is_authenticated and 
                   (self.request.user.is_staff or self.request.user.is_superuser)):
                queryset = queryset.filter(is_public=True, status='ACTIVE')
        
        # Add select_related and prefetch_related for performance
        queryset = queryset.select_related(
            'event', 'venue', 'created_by', 'role_supervisor', 'status_changed_by'
        ).prefetch_related('role_coordinators')
        
        return queryset
    
    def perform_create(self, serializer):
        """Create role with audit logging"""
        role = serializer.save()
        
        # Log role creation
        audit_service.log_event_management_operation(
            operation='ROLE_CREATED',
            user=self.request.user,
            event=role.event,
            details={
                'role_name': role.name,
                'role_type': role.role_type,
                'event_name': role.event.name,
                'venue_name': role.venue.name if role.venue else None,
                'total_positions': role.total_positions,
                'minimum_volunteers': role.minimum_volunteers,
                'via_api': True
            }
        )
    
    def perform_update(self, serializer):
        """Update role with audit logging"""
        old_instance = self.get_object()
        old_data = {
            'name': old_instance.name,
            'status': old_instance.status,
            'total_positions': old_instance.total_positions,
            'filled_positions': old_instance.filled_positions,
            'priority_level': old_instance.priority_level
        }
        
        role = serializer.save()
        
        # Log role update
        audit_service.log_event_management_operation(
            operation='ROLE_UPDATED',
            user=self.request.user,
            event=role.event,
            details={
                'role_name': role.name,
                'role_type': role.role_type,
                'event_name': role.event.name,
                'venue_name': role.venue.name if role.venue else None,
                'old_data': old_data,
                'changes': serializer.validated_data,
                'via_api': True
            }
        )
    
    def perform_destroy(self, instance):
        """Delete role with audit logging"""
        audit_service.log_event_management_operation(
            operation='ROLE_DELETED',
            user=self.request.user,
            event=instance.event,
            details={
                'role_name': instance.name,
                'role_type': instance.role_type,
                'event_name': instance.event.name,
                'venue_name': instance.venue.name if instance.venue else None,
                'total_positions': instance.total_positions,
                'filled_positions': instance.filled_positions,
                'volunteer_count': instance.get_volunteer_count(),
                'via_api': True
            }
        )
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def capacity(self, request, pk=None):
        """
        Get detailed capacity information for this role.
        
        Returns comprehensive capacity tracking data including:
        - Current capacity utilization
        - Available positions
        - Application status
        - Requirements summary
        """
        role = self.get_object()
        serializer = RoleCapacitySerializer(role, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'put'])
    def status(self, request, pk=None):
        """
        Manage role status with audit trail.
        
        GET: Retrieve current status
        PUT: Update status with reason
        """
        role = self.get_object()
        
        if request.method == 'GET':
            return Response({
                'role_id': str(role.id),
                'role_name': role.name,
                'status': role.status,
                'status_changed_at': role.status_changed_at,
                'status_changed_by': role.status_changed_by.get_full_name() if role.status_changed_by else None,
                'is_active': role.status == 'ACTIVE',
                'is_full': role.is_full(),
                'can_accept_volunteers': role.can_accept_volunteers()
            })
        
        else:
            serializer = RoleStatusSerializer(
                role, data=request.data, context={'request': request}
            )
            if serializer.is_valid():
                old_status = role.status
                serializer.save()
                
                # Log status change
                audit_service.log_event_management_operation(
                    operation='ROLE_STATUS_CHANGED',
                    user=request.user,
                    event=role.event,
                    details={
                        'role_name': role.name,
                        'role_type': role.role_type,
                        'event_name': role.event.name,
                        'venue_name': role.venue.name if role.venue else None,
                        'old_status': old_status,
                        'new_status': role.status,
                        'reason': request.data.get('status_change_reason', ''),
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """Get all assignments for this role"""
        role = self.get_object()
        assignments = role.assignments.all().select_related(
            'volunteer', 'event', 'venue', 'assigned_by'
        )
        serializer = AssignmentListSerializer(assignments, many=True, context={'request': request})
        
        return Response({
            'role_id': str(role.id),
            'role_name': role.name,
            'total_assignments': assignments.count(),
            'capacity_info': {
                'total_positions': role.total_positions,
                'filled_positions': role.filled_positions,
                'available_positions': role.get_available_positions(),
                'capacity_percentage': role.get_capacity_percentage()
            },
            'assignments': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def update_capacity(self, request, pk=None):
        """
        Update role capacity with validation.
        
        Allows updating total_positions and minimum_volunteers
        with proper validation against current assignments.
        """
        role = self.get_object()
        
        new_total = request.data.get('total_positions')
        new_minimum = request.data.get('minimum_volunteers')
        
        if new_total is not None:
            current_assignments = role.get_volunteer_count()
            if new_total < current_assignments:
                return Response({
                    'error': f'Cannot reduce capacity below current assignments ({current_assignments})'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            old_total = role.total_positions
            role.total_positions = new_total
        
        if new_minimum is not None:
            if new_minimum > role.total_positions:
                return Response({
                    'error': 'Minimum volunteers cannot exceed total positions'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            old_minimum = role.minimum_volunteers
            role.minimum_volunteers = new_minimum
        
        role.save()
        
        # Log capacity update
        audit_service.log_event_management_operation(
            operation='ROLE_CAPACITY_UPDATED',
            user=request.user,
            event=role.event,
            details={
                'role_name': role.name,
                'role_type': role.role_type,
                'event_name': role.event.name,
                'venue_name': role.venue.name if role.venue else None,
                'old_total_positions': old_total if new_total else role.total_positions,
                'new_total_positions': role.total_positions,
                'old_minimum_volunteers': old_minimum if new_minimum else role.minimum_volunteers,
                'new_minimum_volunteers': role.minimum_volunteers,
                'via_api': True
            }
        )
        
        serializer = RoleCapacitySerializer(role, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get roles filtered by event"""
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        roles = self.get_queryset().filter(event_id=event_id)
        serializer = RoleListSerializer(roles, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_venue(self, request):
        """Get roles filtered by venue"""
        venue_id = request.query_params.get('venue_id')
        if not venue_id:
            return Response(
                {'error': 'venue_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        roles = self.get_queryset().filter(venue_id=venue_id)
        serializer = RoleListSerializer(roles, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def urgent(self, request):
        """Get urgent roles that need filling"""
        roles = self.get_queryset().filter(
            is_urgent=True, 
            status='ACTIVE',
            is_public=True
        ).order_by('priority_level', 'application_deadline')
        
        serializer = RoleListSerializer(roles, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def understaffed(self, request):
        """Get roles that are understaffed"""
        # This would require a custom query - for now return basic filter
        roles = self.get_queryset().filter(
            status='ACTIVE',
            is_public=True
        )
        
        # Filter understaffed roles in Python (could be optimized with database query)
        understaffed_roles = [role for role in roles if role.is_understaffed()]
        
        serializer = RoleListSerializer(understaffed_roles, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get roles that can accept more volunteers"""
        roles = self.get_queryset().filter(
            status='ACTIVE',
            is_public=True
        )
        
        # Filter available roles in Python (could be optimized with database query)
        available_roles = [role for role in roles if role.can_accept_volunteers()]
        
        serializer = RoleListSerializer(available_roles, many=True, context={'request': request})
        return Response(serializer.data)


# Additional API Views for specific event management operations

class RoleRequirementsView(generics.RetrieveAPIView):
    """Get role requirements and qualifications"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, role_id):
        try:
            role = Role.objects.get(id=role_id)
            return Response({
                'role_id': str(role.id),
                'role_name': role.name,
                'requirements': {
                    'minimum_age': role.minimum_age,
                    'maximum_age': role.maximum_age,
                    'skill_level_required': role.skill_level_required,
                    'physical_requirements': role.physical_requirements,
                    'language_requirements': role.language_requirements,
                    'required_credentials': role.required_credentials,
                    'preferred_credentials': role.preferred_credentials,
                    'justgo_credentials_required': role.justgo_credentials_required,
                    'requires_garda_vetting': role.requires_garda_vetting,
                    'requires_child_protection': role.requires_child_protection,
                    'requires_security_clearance': role.requires_security_clearance,
                    'training_required': role.training_required,
                    'training_duration_hours': float(role.training_duration_hours) if role.training_duration_hours else None
                },
                'time_commitment': {
                    'commitment_level': role.commitment_level,
                    'estimated_hours_per_day': float(role.estimated_hours_per_day) if role.estimated_hours_per_day else None,
                    'total_estimated_hours': float(role.total_estimated_hours) if role.total_estimated_hours else None,
                    'schedule_requirements': role.schedule_requirements,
                    'availability_windows': role.availability_windows
                },
                'benefits': {
                    'benefits': role.benefits,
                    'meal_provided': role.meal_provided,
                    'transport_provided': role.transport_provided,
                    'accommodation_provided': role.accommodation_provided,
                    'uniform_required': role.uniform_required,
                    'uniform_details': role.uniform_details,
                    'equipment_provided': role.equipment_provided,
                    'equipment_required': role.equipment_required
                }
            })
        except Role.DoesNotExist:
            return Response(
                {'error': 'Role not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class RoleVolunteersView(generics.ListAPIView):
    """Get volunteers assigned to a specific role"""
    serializer_class = AssignmentListSerializer
    permission_classes = [EventManagementPermission]
    
    def get_queryset(self):
        role_id = self.kwargs['role_id']
        return Assignment.objects.filter(role_id=role_id).select_related(
            'volunteer', 'role', 'event', 'venue', 'assigned_by'
        )
    
    def list(self, request, *args, **kwargs):
        try:
            role = Role.objects.get(id=self.kwargs['role_id'])
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'role_id': str(role.id),
                'role_name': role.name,
                'total_assignments': queryset.count(),
                'capacity_info': {
                    'total_positions': role.total_positions,
                    'filled_positions': role.filled_positions,
                    'available_positions': role.get_available_positions(),
                    'capacity_percentage': role.get_capacity_percentage()
                },
                'assignments': serializer.data
            })
        except Role.DoesNotExist:
            return Response(
                {'error': 'Role not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


# Assignment Management ViewSet and API Views

class AssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Assignment management with full CRUD operations and status workflows.
    
    Provides:
    - List assignments with filtering and search
    - Create new assignments
    - Retrieve assignment details
    - Update assignments
    - Delete assignments
    - Custom actions for status workflows, attendance, and bulk operations
    """
    queryset = Assignment.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'volunteer', 'role', 'event', 'venue', 'assignment_type', 'status',
        'priority_level', 'is_admin_override', 'assigned_by', 'reviewed_by',
        'approved_by', 'start_date', 'end_date'
    ]
    search_fields = [
        'volunteer__first_name', 'volunteer__last_name', 'volunteer__email',
        'role__name', 'event__name', 'venue__name', 'special_instructions',
        'notes'
    ]
    ordering_fields = [
        'assigned_date', 'start_date', 'end_date', 'status', 'priority_level',
        'volunteer__last_name', 'role__name', 'event__name'
    ]
    ordering = ['-assigned_date', 'start_date', 'volunteer__last_name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return AssignmentListSerializer
        elif self.action == 'create':
            return AssignmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AssignmentUpdateSerializer
        elif self.action == 'status':
            return AssignmentStatusSerializer
        elif self.action == 'workflow':
            return AssignmentWorkflowSerializer
        elif self.action == 'attendance':
            return AssignmentAttendanceSerializer
        elif self.action == 'bulk_operations':
            return AssignmentBulkSerializer
        else:
            return AssignmentDetailSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [EventManagementPermission]
        elif self.action in ['status', 'workflow', 'attendance', 'bulk_operations']:
            permission_classes = [EventManagementPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return filtered queryset based on user permissions"""
        queryset = Assignment.objects.select_related(
            'volunteer', 'role', 'event', 'venue',
            'assigned_by', 'reviewed_by', 'approved_by',
            'status_changed_by', 'admin_override_by'
        ).prefetch_related(
            'role__required_credentials',
            'role__preferred_credentials'
        )
        
        # Filter based on user permissions
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        
        # Volunteers can only see their own assignments
        if hasattr(user, 'volunteer_profile'):
            return queryset.filter(volunteer=user)
        
        # Staff can see assignments they manage
        if user.is_staff:
            # Event managers can see assignments in their events
            if hasattr(user, 'managed_events'):
                managed_events = user.managed_events.all()
                if managed_events.exists():
                    queryset = queryset.filter(event__in=managed_events)
            
            # Role coordinators can see assignments for their roles
            if hasattr(user, 'coordinated_roles'):
                coordinated_roles = user.coordinated_roles.all()
                if coordinated_roles.exists():
                    queryset = queryset.filter(role__in=coordinated_roles)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create assignment with audit logging"""
        assignment = serializer.save(assigned_by=self.request.user)
        
        # Log assignment creation
        audit_service.log_event_management_operation(
            operation='ASSIGNMENT_CREATED',
            user=self.request.user,
            event=assignment.event,
            details={
                'assignment_id': str(assignment.id),
                'volunteer_name': assignment.volunteer.get_full_name(),
                'volunteer_email': assignment.volunteer.email,
                'role_name': assignment.role.name,
                'event_name': assignment.event.name,
                'venue_name': assignment.venue.name if assignment.venue else None,
                'assignment_type': assignment.assignment_type,
                'priority_level': assignment.priority_level,
                'start_date': assignment.start_date.isoformat() if assignment.start_date else None,
                'end_date': assignment.end_date.isoformat() if assignment.end_date else None,
                'via_api': True
            }
        )
    
    def perform_update(self, serializer):
        """Update assignment with audit logging"""
        old_data = {
            'status': serializer.instance.status,
            'assignment_type': serializer.instance.assignment_type,
            'priority_level': serializer.instance.priority_level,
            'start_date': serializer.instance.start_date,
            'end_date': serializer.instance.end_date
        }
        
        assignment = serializer.save()
        
        # Log significant changes
        changes = {}
        for field, old_value in old_data.items():
            new_value = getattr(assignment, field)
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}
        
        if changes:
            audit_service.log_event_management_operation(
                operation='ASSIGNMENT_UPDATED',
                user=self.request.user,
                event=assignment.event,
                details={
                    'assignment_id': str(assignment.id),
                    'volunteer_name': assignment.volunteer.get_full_name(),
                    'role_name': assignment.role.name,
                    'event_name': assignment.event.name,
                    'changes': changes,
                    'via_api': True
                }
            )
    
    def perform_destroy(self, instance):
        """Delete assignment with audit logging"""
        audit_service.log_event_management_operation(
            operation='ASSIGNMENT_DELETED',
            user=self.request.user,
            event=instance.event,
            details={
                'assignment_id': str(instance.id),
                'volunteer_name': instance.volunteer.get_full_name(),
                'volunteer_email': instance.volunteer.email,
                'role_name': instance.role.name,
                'event_name': instance.event.name,
                'venue_name': instance.venue.name if instance.venue else None,
                'status': instance.status,
                'via_api': True
            }
        )
        
        instance.delete()
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def status(self, request, pk=None):
        """
        Get or update assignment status with workflow validation.
        
        GET: Returns current status and available transitions
        PUT/PATCH: Updates status with workflow validation
        """
        assignment = self.get_object()
        
        if request.method == 'GET':
            # Return current status and available transitions
            available_transitions = assignment.get_available_status_transitions()
            
            return Response({
                'assignment_id': str(assignment.id),
                'current_status': assignment.status,
                'status_display': assignment.get_status_display(),
                'status_changed_at': assignment.status_changed_at,
                'status_changed_by': assignment.status_changed_by.get_full_name() if assignment.status_changed_by else None,
                'status_change_reason': assignment.status_change_reason,
                'available_transitions': available_transitions,
                'can_be_modified': assignment.can_be_modified(),
                'can_be_cancelled': assignment.can_be_cancelled(),
                'workflow_info': {
                    'is_pending': assignment.is_pending(),
                    'is_active': assignment.is_active(),
                    'is_completed': assignment.is_completed(),
                    'is_cancelled': assignment.is_cancelled()
                }
            })
        
        else:
            # Update status
            serializer = AssignmentStatusSerializer(
                assignment, 
                data=request.data, 
                context={'request': request}
            )
            
            if serializer.is_valid():
                old_status = assignment.status
                serializer.save()
                
                # Log status change
                audit_service.log_event_management_operation(
                    operation='ASSIGNMENT_STATUS_CHANGED',
                    user=request.user,
                    event=assignment.event,
                    details={
                        'assignment_id': str(assignment.id),
                        'volunteer_name': assignment.volunteer.get_full_name(),
                        'role_name': assignment.role.name,
                        'event_name': assignment.event.name,
                        'old_status': old_status,
                        'new_status': assignment.status,
                        'reason': request.data.get('status_change_reason', ''),
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def workflow(self, request, pk=None):
        """
        Execute workflow actions on assignment.
        
        Supported actions: approve, confirm, activate, complete, cancel, 
        reject, withdraw, mark_no_show, suspend
        """
        assignment = self.get_object()
        
        serializer = AssignmentWorkflowSerializer(
            data=request.data,
            context={'request': request, 'assignment': assignment}
        )
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            performance_rating = serializer.validated_data.get('performance_rating')
            
            try:
                # Execute workflow action
                if action == 'approve':
                    assignment.approve(approved_by=request.user, notes=notes)
                elif action == 'confirm':
                    assignment.confirm(confirmed_by=request.user, notes=notes)
                elif action == 'activate':
                    assignment.activate(activated_by=request.user, notes=notes)
                elif action == 'complete':
                    assignment.complete(
                        completed_by=request.user, 
                        notes=notes,
                        performance_rating=performance_rating
                    )
                elif action == 'cancel':
                    assignment.cancel(cancelled_by=request.user, reason=notes)
                elif action == 'reject':
                    assignment.reject(rejected_by=request.user, reason=notes)
                elif action == 'withdraw':
                    assignment.withdraw(withdrawn_by=request.user, reason=notes)
                elif action == 'mark_no_show':
                    assignment.mark_no_show(marked_by=request.user, notes=notes)
                elif action == 'suspend':
                    assignment.suspend(suspended_by=request.user, reason=notes)
                
                # Log workflow action
                audit_service.log_event_management_operation(
                    operation=f'ASSIGNMENT_{action.upper()}',
                    user=request.user,
                    event=assignment.event,
                    details={
                        'assignment_id': str(assignment.id),
                        'volunteer_name': assignment.volunteer.get_full_name(),
                        'role_name': assignment.role.name,
                        'event_name': assignment.event.name,
                        'action': action,
                        'notes': notes,
                        'performance_rating': performance_rating,
                        'new_status': assignment.status,
                        'via_api': True
                    }
                )
                
                return Response({
                    'success': True,
                    'message': f'Assignment {action} successful',
                    'assignment_id': str(assignment.id),
                    'new_status': assignment.status,
                    'status_display': assignment.get_status_display()
                })
                
            except ValidationError as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def attendance(self, request, pk=None):
        """
        Get or update assignment attendance information.
        
        Handles check-in/check-out times and actual hours worked.
        """
        assignment = self.get_object()
        
        if request.method == 'GET':
            serializer = AssignmentAttendanceSerializer(assignment)
            return Response(serializer.data)
        
        else:
            serializer = AssignmentAttendanceSerializer(
                assignment,
                data=request.data,
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                
                # Log attendance update
                audit_service.log_event_management_operation(
                    operation='ASSIGNMENT_ATTENDANCE_UPDATED',
                    user=request.user,
                    event=assignment.event,
                    details={
                        'assignment_id': str(assignment.id),
                        'volunteer_name': assignment.volunteer.get_full_name(),
                        'role_name': assignment.role.name,
                        'event_name': assignment.event.name,
                        'check_in_time': assignment.check_in_time.isoformat() if assignment.check_in_time else None,
                        'check_out_time': assignment.check_out_time.isoformat() if assignment.check_out_time else None,
                        'actual_hours_worked': float(assignment.actual_hours_worked) if assignment.actual_hours_worked else None,
                        'via_api': True
                    }
                )
                
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Quick check-in action for assignment"""
        assignment = self.get_object()
        
        if assignment.check_in_time:
            return Response({
                'error': 'Assignment already checked in'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        assignment.check_in_time = timezone.now()
        assignment.save()
        
        # Log check-in
        audit_service.log_event_management_operation(
            operation='ASSIGNMENT_CHECK_IN',
            user=request.user,
            event=assignment.event,
            details={
                'assignment_id': str(assignment.id),
                'volunteer_name': assignment.volunteer.get_full_name(),
                'role_name': assignment.role.name,
                'event_name': assignment.event.name,
                'check_in_time': assignment.check_in_time.isoformat(),
                'via_api': True
            }
        )
        
        return Response({
            'success': True,
            'message': 'Checked in successfully',
            'check_in_time': assignment.check_in_time
        })
    
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """Quick check-out action for assignment"""
        assignment = self.get_object()
        
        if not assignment.check_in_time:
            return Response({
                'error': 'Must check in before checking out'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if assignment.check_out_time:
            return Response({
                'error': 'Assignment already checked out'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        assignment.check_out_time = timezone.now()
        
        # Calculate hours worked
        if assignment.check_in_time:
            duration = assignment.check_out_time - assignment.check_in_time
            assignment.actual_hours_worked = duration.total_seconds() / 3600
        
        assignment.save()
        
        # Log check-out
        audit_service.log_event_management_operation(
            operation='ASSIGNMENT_CHECK_OUT',
            user=request.user,
            event=assignment.event,
            details={
                'assignment_id': str(assignment.id),
                'volunteer_name': assignment.volunteer.get_full_name(),
                'role_name': assignment.role.name,
                'event_name': assignment.event.name,
                'check_out_time': assignment.check_out_time.isoformat(),
                'actual_hours_worked': float(assignment.actual_hours_worked) if assignment.actual_hours_worked else None,
                'via_api': True
            }
        )
        
        return Response({
            'success': True,
            'message': 'Checked out successfully',
            'check_out_time': assignment.check_out_time,
            'actual_hours_worked': assignment.actual_hours_worked
        })
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get assignment status change history"""
        assignment = self.get_object()
        
        return Response({
            'assignment_id': str(assignment.id),
            'volunteer_name': assignment.volunteer.get_full_name(),
            'role_name': assignment.role.name,
            'event_name': assignment.event.name,
            'status_history': assignment.get_status_history(),
            'timeline': {
                'assigned_date': assignment.assigned_date,
                'application_date': assignment.application_date,
                'review_date': assignment.review_date,
                'approval_date': assignment.approval_date,
                'confirmation_date': assignment.confirmation_date,
                'completion_date': assignment.completion_date,
                'status_changed_at': assignment.status_changed_at
            },
            'admin_overrides': {
                'is_admin_override': assignment.is_admin_override,
                'admin_override_reason': assignment.admin_override_reason,
                'admin_override_by': assignment.admin_override_by.get_full_name() if assignment.admin_override_by else None,
                'admin_override_date': assignment.admin_override_date,
                'age_requirement_override': assignment.age_requirement_override,
                'credential_requirement_override': assignment.credential_requirement_override,
                'capacity_override': assignment.capacity_override,
                'override_justification': assignment.override_justification
            }
        })
    
    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """
        Perform bulk operations on multiple assignments.
        
        Supported actions: approve, cancel, activate, complete, send_notification
        """
        serializer = AssignmentBulkSerializer(data=request.data)
        
        if serializer.is_valid():
            assignment_ids = serializer.validated_data['assignment_ids']
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            
            assignments = Assignment.objects.filter(id__in=assignment_ids)
            
            if assignments.count() != len(assignment_ids):
                return Response({
                    'error': 'Some assignment IDs were not found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            results = {
                'total_requested': len(assignment_ids),
                'successful': 0,
                'failed': 0,
                'errors': []
            }
            
            for assignment in assignments:
                try:
                    if action == 'approve':
                        assignment.approve(approved_by=request.user, notes=notes)
                    elif action == 'cancel':
                        assignment.cancel(cancelled_by=request.user, reason=notes)
                    elif action == 'activate':
                        assignment.activate(activated_by=request.user, notes=notes)
                    elif action == 'complete':
                        assignment.complete(completed_by=request.user, notes=notes)
                    elif action == 'send_notification':
                        # Would integrate with notification system
                        pass
                    
                    results['successful'] += 1
                    
                except ValidationError as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'assignment_id': str(assignment.id),
                        'volunteer_name': assignment.volunteer.get_full_name(),
                        'error': str(e)
                    })
            
            # Log bulk operation
            audit_service.log_event_management_operation(
                operation=f'ASSIGNMENT_BULK_{action.upper()}',
                user=request.user,
                details={
                    'action': action,
                    'total_requested': results['total_requested'],
                    'successful': results['successful'],
                    'failed': results['failed'],
                    'notes': notes,
                    'via_api': True
                }
            )
            
            return Response(results)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_volunteer(self, request):
        """Get assignments filtered by volunteer"""
        volunteer_id = request.query_params.get('volunteer_id')
        if not volunteer_id:
            return Response(
                {'error': 'volunteer_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignments = self.get_queryset().filter(volunteer_id=volunteer_id)
        serializer = AssignmentListSerializer(assignments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get assignments filtered by role"""
        role_id = request.query_params.get('role_id')
        if not role_id:
            return Response(
                {'error': 'role_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignments = self.get_queryset().filter(role_id=role_id)
        serializer = AssignmentListSerializer(assignments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get assignments filtered by event"""
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assignments = self.get_queryset().filter(event_id=event_id)
        serializer = AssignmentListSerializer(assignments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending assignments that need review"""
        assignments = self.get_queryset().filter(status='PENDING').order_by('assigned_date')
        serializer = AssignmentListSerializer(assignments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active assignments"""
        assignments = self.get_queryset().filter(status='ACTIVE').order_by('start_date')
        serializer = AssignmentListSerializer(assignments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue assignments"""
        from django.utils import timezone
        today = timezone.now().date()
        
        assignments = self.get_queryset().filter(
            start_date__lt=today,
            status__in=['PENDING', 'APPROVED']
        ).order_by('start_date')
        
        serializer = AssignmentListSerializer(assignments, many=True, context={'request': request})
        return Response(serializer.data)


# Additional Assignment Management API Views

class BulkAssignmentView(generics.GenericAPIView):
    """Handle bulk assignment operations"""
    permission_classes = [EventManagementPermission]
    serializer_class = AssignmentBulkSerializer
    
    def post(self, request):
        """
        Perform bulk operations on assignments.
        
        Supports creating multiple assignments, status updates, and notifications.
        """
        operation = request.data.get('operation', 'status_update')
        
        if operation == 'create_multiple':
            return self._create_multiple_assignments(request)
        elif operation == 'status_update':
            return self._bulk_status_update(request)
        elif operation == 'send_notifications':
            return self._send_bulk_notifications(request)
        else:
            return Response({
                'error': 'Invalid operation. Supported: create_multiple, status_update, send_notifications'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _create_multiple_assignments(self, request):
        """Create multiple assignments at once"""
        assignments_data = request.data.get('assignments', [])
        
        if not assignments_data:
            return Response({
                'error': 'assignments data is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = {
            'total_requested': len(assignments_data),
            'successful': 0,
            'failed': 0,
            'created_assignments': [],
            'errors': []
        }
        
        for assignment_data in assignments_data:
            try:
                serializer = AssignmentCreateSerializer(
                    data=assignment_data,
                    context={'request': request}
                )
                
                if serializer.is_valid():
                    assignment = serializer.save(assigned_by=request.user)
                    results['successful'] += 1
                    results['created_assignments'].append({
                        'id': str(assignment.id),
                        'volunteer_name': assignment.volunteer.get_full_name(),
                        'role_name': assignment.role.name,
                        'event_name': assignment.event.name
                    })
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'data': assignment_data,
                        'errors': serializer.errors
                    })
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'data': assignment_data,
                    'error': str(e)
                })
        
        # Log bulk creation
        audit_service.log_event_management_operation(
            operation='ASSIGNMENT_BULK_CREATE',
            user=request.user,
            details={
                'total_requested': results['total_requested'],
                'successful': results['successful'],
                'failed': results['failed'],
                'via_api': True
            }
        )
        
        return Response(results)
    
    def _bulk_status_update(self, request):
        """Update status for multiple assignments"""
        assignment_ids = request.data.get('assignment_ids', [])
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if not assignment_ids or not new_status:
            return Response({
                'error': 'assignment_ids and status are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        assignments = Assignment.objects.filter(id__in=assignment_ids)
        
        results = {
            'total_requested': len(assignment_ids),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for assignment in assignments:
            try:
                assignment.change_status(
                    new_status,
                    changed_by=request.user,
                    reason=reason
                )
                results['successful'] += 1
                
            except ValidationError as e:
                results['failed'] += 1
                results['errors'].append({
                    'assignment_id': str(assignment.id),
                    'volunteer_name': assignment.volunteer.get_full_name(),
                    'error': str(e)
                })
        
        return Response(results)
    
    def _send_bulk_notifications(self, request):
        """Send notifications to multiple assignments"""
        assignment_ids = request.data.get('assignment_ids', [])
        message = request.data.get('message', '')
        notification_type = request.data.get('notification_type', 'general')
        
        if not assignment_ids:
            return Response({
                'error': 'assignment_ids are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        assignments = Assignment.objects.filter(id__in=assignment_ids)
        
        results = {
            'total_requested': len(assignment_ids),
            'notifications_sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for assignment in assignments:
            try:
                # Would integrate with notification system
                # For now, just update last_notification_sent
                assignment.last_notification_sent = timezone.now()
                assignment.reminder_count += 1
                assignment.save()
                
                results['notifications_sent'] += 1
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'assignment_id': str(assignment.id),
                    'volunteer_name': assignment.volunteer.get_full_name(),
                    'error': str(e)
                })
        
        return Response(results)


class AssignmentOverrideView(generics.GenericAPIView):
    """Handle admin overrides for assignments"""
    permission_classes = [EventManagementPermission]
    
    def post(self, request, assignment_id):
        """
        Create admin override for assignment.
        
        Allows bypassing normal assignment rules with proper justification.
        """
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({
                'error': 'Assignment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        override_type = request.data.get('override_type')
        justification = request.data.get('justification')
        
        if not override_type or not justification:
            return Response({
                'error': 'override_type and justification are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate override type
        valid_overrides = [
            'age_requirement', 'credential_requirement', 'capacity_override'
        ]
        
        if override_type not in valid_overrides:
            return Response({
                'error': f'Invalid override_type. Valid options: {valid_overrides}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Apply override
        assignment.is_admin_override = True
        assignment.admin_override_reason = f"{override_type}: {justification}"
        assignment.admin_override_by = request.user
        assignment.admin_override_date = timezone.now()
        assignment.override_justification = justification
        
        if override_type == 'age_requirement':
            assignment.age_requirement_override = True
        elif override_type == 'credential_requirement':
            assignment.credential_requirement_override = True
        elif override_type == 'capacity_override':
            assignment.capacity_override = True
        
        assignment.save()
        
        # Log override
        audit_service.log_event_management_operation(
            operation='ASSIGNMENT_ADMIN_OVERRIDE',
            user=request.user,
            event=assignment.event,
            details={
                'assignment_id': str(assignment.id),
                'volunteer_name': assignment.volunteer.get_full_name(),
                'role_name': assignment.role.name,
                'event_name': assignment.event.name,
                'override_type': override_type,
                'justification': justification,
                'via_api': True
            }
        )
        
        return Response({
            'success': True,
            'message': f'Admin override applied: {override_type}',
            'assignment_id': str(assignment.id),
            'override_details': {
                'type': override_type,
                'justification': justification,
                'applied_by': request.user.get_full_name(),
                'applied_at': assignment.admin_override_date
            }
        })


class AssignmentStatsView(generics.GenericAPIView):
    """Get assignment statistics and analytics"""
    permission_classes = [EventManagementPermission]
    serializer_class = AssignmentStatsSerializer  # Add serializer class to fix schema generation
    
    def get(self, request):
        """
        Get comprehensive assignment statistics.
        
        Provides counts by status, event, role, and time periods.
        """
        # Get query parameters for filtering
        event_id = request.query_params.get('event_id')
        role_id = request.query_params.get('role_id')
        volunteer_id = request.query_params.get('volunteer_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Base queryset
        queryset = Assignment.objects.all()
        
        # Apply filters
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        if role_id:
            queryset = queryset.filter(role_id=role_id)
        if volunteer_id:
            queryset = queryset.filter(volunteer_id=volunteer_id)
        if date_from:
            queryset = queryset.filter(assigned_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(assigned_date__lte=date_to)
        
        # Calculate statistics
        total_assignments = queryset.count()
        
        # Status breakdown
        status_counts = {}
        for status_choice in Assignment.AssignmentStatus.choices:
            status_code = status_choice[0]
            status_counts[status_code] = queryset.filter(status=status_code).count()
        
        # Assignment type breakdown
        type_counts = {}
        for type_choice in Assignment.AssignmentType.choices:
            type_code = type_choice[0]
            type_counts[type_code] = queryset.filter(assignment_type=type_code).count()
        
        # Priority breakdown
        priority_counts = {}
        for priority_choice in Assignment.PriorityLevel.choices:
            priority_code = priority_choice[0]
            priority_counts[priority_code] = queryset.filter(priority_level=priority_code).count()
        
        # Admin overrides
        admin_overrides = queryset.filter(is_admin_override=True).count()
        
        # Performance metrics
        completed_assignments = queryset.filter(status='COMPLETED')
        avg_performance_rating = completed_assignments.aggregate(
            avg_rating=Avg('performance_rating')
        )['avg_rating']
        
        # Time-based metrics
        from django.utils import timezone
        today = timezone.now().date()
        
        overdue_assignments = queryset.filter(
            start_date__lt=today,
            status__in=['PENDING', 'APPROVED']
        ).count()
        
        upcoming_assignments = queryset.filter(
            start_date__gte=today,
            status__in=['APPROVED', 'CONFIRMED', 'ACTIVE']
        ).count()
        
        return Response({
            'summary': {
                'total_assignments': total_assignments,
                'admin_overrides': admin_overrides,
                'overdue_assignments': overdue_assignments,
                'upcoming_assignments': upcoming_assignments,
                'average_performance_rating': round(avg_performance_rating, 2) if avg_performance_rating else None
            },
            'status_breakdown': status_counts,
            'type_breakdown': type_counts,
            'priority_breakdown': priority_counts,
            'filters_applied': {
                'event_id': event_id,
                'role_id': role_id,
                'volunteer_id': volunteer_id,
                'date_from': date_from,
                'date_to': date_to
            }
        })

