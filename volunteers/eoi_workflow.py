"""
Volunteer Type Workflow Routing for ISG 2026 Volunteer Management System

This module handles different workflows based on volunteer types:
- NEW: First-time volunteers (full EOI process)
- RETURNING: Previous volunteers (simplified process with pre-filled data)
- CORPORATE: Corporate group volunteers (group-based workflow)
"""

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models import Q
import logging

from .eoi_models import EOISubmission, EOIProfileInformation
from .models import VolunteerProfile
from integrations.justgo import JustGoAPIClient
from common.audit import log_audit_event

User = get_user_model()
logger = logging.getLogger(__name__)


class VolunteerWorkflowRouter:
    """
    Routes volunteers through appropriate workflows based on their type and history
    """
    
    def __init__(self, request, eoi_submission):
        self.request = request
        self.eoi_submission = eoi_submission
        self.user = request.user if request.user.is_authenticated else None
        self.volunteer_type = eoi_submission.volunteer_type
        
    def get_workflow_steps(self):
        """
        Returns the appropriate workflow steps for the volunteer type
        """
        workflows = {
            'NEW': self._get_new_volunteer_workflow(),
            'RETURNING': self._get_returning_volunteer_workflow(),
            'CORPORATE': self._get_corporate_volunteer_workflow()
        }
        
        return workflows.get(self.volunteer_type, workflows['NEW'])
    
    def get_next_step(self, current_step):
        """
        Determines the next step in the workflow based on current step and volunteer type
        """
        workflow_steps = self.get_workflow_steps()
        
        try:
            current_index = workflow_steps.index(current_step)
            if current_index + 1 < len(workflow_steps):
                return workflow_steps[current_index + 1]
            else:
                return 'complete'
        except ValueError:
            # Current step not found, return first step
            return workflow_steps[0] if workflow_steps else 'profile'
    
    def should_skip_step(self, step):
        """
        Determines if a step should be skipped based on volunteer type and existing data
        """
        if self.volunteer_type == 'RETURNING':
            return self._should_skip_step_returning(step)
        elif self.volunteer_type == 'CORPORATE':
            return self._should_skip_step_corporate(step)
        
        return False
    
    def pre_fill_data(self, step):
        """
        Pre-fills form data based on volunteer type and existing information
        """
        if self.volunteer_type == 'RETURNING':
            return self._pre_fill_returning_data(step)
        elif self.volunteer_type == 'CORPORATE':
            return self._pre_fill_corporate_data(step)
        
        return {}
    
    def validate_workflow_transition(self, from_step, to_step):
        """
        Validates if the workflow transition is allowed
        """
        workflow_steps = self.get_workflow_steps()
        
        # Check if both steps are in the workflow
        if from_step not in workflow_steps or to_step not in workflow_steps:
            return False
        
        from_index = workflow_steps.index(from_step)
        to_index = workflow_steps.index(to_step)
        
        # Allow moving forward or backward within workflow
        return abs(to_index - from_index) <= 1
    
    def _get_new_volunteer_workflow(self):
        """
        Full workflow for new volunteers
        """
        return ['profile', 'recruitment', 'games', 'review', 'confirmation']
    
    def _get_returning_volunteer_workflow(self):
        """
        Simplified workflow for returning volunteers with data pre-filling
        """
        steps = ['profile', 'recruitment', 'games', 'review', 'confirmation']
        
        # Check if we can skip certain steps based on existing data
        if self._has_recent_profile_data():
            # Still include profile step but with pre-filled data
            pass
        
        if self._has_recent_recruitment_data():
            # Include recruitment step with pre-filled preferences
            pass
        
        return steps
    
    def _get_corporate_volunteer_workflow(self):
        """
        Corporate volunteer workflow with group-specific steps
        """
        return ['corporate_group', 'profile', 'recruitment', 'games', 'review', 'confirmation']
    
    def _should_skip_step_returning(self, step):
        """
        Determine if returning volunteers should skip certain steps
        """
        # For now, don't skip any steps but pre-fill data instead
        # This ensures data accuracy while improving user experience
        return False
    
    def _should_skip_step_corporate(self, step):
        """
        Determine if corporate volunteers should skip certain steps
        """
        # Corporate volunteers might skip individual group selection
        # if they're already part of a registered corporate group
        if step == 'corporate_group' and self._has_corporate_group_assignment():
            return True
        
        return False
    
    def _pre_fill_returning_data(self, step):
        """
        Pre-fill data for returning volunteers based on previous submissions or profiles
        """
        pre_fill_data = {}
        
        if step == 'profile':
            pre_fill_data.update(self._get_previous_profile_data())
        elif step == 'recruitment':
            pre_fill_data.update(self._get_previous_recruitment_data())
        elif step == 'games':
            pre_fill_data.update(self._get_previous_games_data())
        
        return pre_fill_data
    
    def _pre_fill_corporate_data(self, step):
        """
        Pre-fill data for corporate volunteers
        """
        pre_fill_data = {}
        
        if step == 'corporate_group':
            pre_fill_data.update(self._get_corporate_group_data())
        
        # Corporate volunteers can also benefit from previous data
        pre_fill_data.update(self._pre_fill_returning_data(step))
        
        return pre_fill_data
    
    def _has_recent_profile_data(self):
        """
        Check if user has recent profile data (within last 2 years)
        """
        if not self.user:
            return False
        
        from datetime import datetime, timedelta
        two_years_ago = datetime.now() - timedelta(days=730)
        
        # Check for recent EOI submissions
        recent_eoi = EOISubmission.objects.filter(
            user=self.user,
            profile_information__isnull=False,
            created_at__gte=two_years_ago
        ).exists()
        
        # Check for existing volunteer profile
        volunteer_profile = VolunteerProfile.objects.filter(user=self.user).exists()
        
        return recent_eoi or volunteer_profile
    
    def _has_recent_recruitment_data(self):
        """
        Check if user has recent recruitment preference data
        """
        if not self.user:
            return False
        
        from datetime import datetime, timedelta
        two_years_ago = datetime.now() - timedelta(days=730)
        
        return EOISubmission.objects.filter(
            user=self.user,
            recruitment_preferences__isnull=False,
            created_at__gte=two_years_ago
        ).exists()
    
    def _has_corporate_group_assignment(self):
        """
        Check if user is already assigned to a corporate group
        """
        # Check if there's an existing corporate group assignment
        # This could be from a previous registration or admin assignment
        return False  # Implement based on your corporate group logic
    
    def _get_previous_profile_data(self):
        """
        Get previous profile data for pre-filling
        """
        if not self.user:
            return {}
        
        # Try to get the most recent profile information
        try:
            recent_eoi = EOISubmission.objects.filter(
                user=self.user,
                profile_information__isnull=False
            ).order_by('-created_at').first()
            
            if recent_eoi and recent_eoi.profile_information:
                profile_info = recent_eoi.profile_information
                return {
                    'first_name': profile_info.first_name,
                    'last_name': profile_info.last_name,
                    'preferred_name': profile_info.preferred_name,
                    'email': profile_info.email,
                    'phone_number': profile_info.phone_number,
                    'address_line_1': profile_info.address_line_1,
                    'address_line_2': profile_info.address_line_2,
                    'city': profile_info.city,
                    'state_province': profile_info.state_province,
                    'postal_code': profile_info.postal_code,
                    'country': profile_info.country,
                    'emergency_contact_name': profile_info.emergency_contact_name,
                    'emergency_contact_phone': profile_info.emergency_contact_phone,
                    'emergency_contact_relationship': profile_info.emergency_contact_relationship,
                    'education_level': profile_info.education_level,
                    'employment_status': profile_info.employment_status,
                    'occupation': profile_info.occupation,
                    'languages_spoken': profile_info.languages_spoken,
                    'nationality': profile_info.nationality,
                }
        except Exception as e:
            logger.warning(f"Error retrieving previous profile data: {e}")
        
        # Try to get data from existing volunteer profile
        try:
            volunteer_profile = VolunteerProfile.objects.get(user=self.user)
            return {
                'first_name': volunteer_profile.user.first_name,
                'last_name': volunteer_profile.user.last_name,
                'email': volunteer_profile.user.email,
                'phone_number': volunteer_profile.phone_number,
                'emergency_contact_name': volunteer_profile.emergency_contact_name,
                'emergency_contact_phone': volunteer_profile.emergency_contact_phone,
            }
        except VolunteerProfile.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"Error retrieving volunteer profile data: {e}")
        
        return {}
    
    def _get_previous_recruitment_data(self):
        """
        Get previous recruitment preference data for pre-filling
        """
        if not self.user:
            return {}
        
        try:
            recent_eoi = EOISubmission.objects.filter(
                user=self.user,
                recruitment_preferences__isnull=False
            ).order_by('-created_at').first()
            
            if recent_eoi and recent_eoi.recruitment_preferences:
                recruitment_prefs = recent_eoi.recruitment_preferences
                return {
                    'volunteer_experience_level': recruitment_prefs.volunteer_experience_level,
                    'previous_events': recruitment_prefs.previous_events,
                    'special_skills': recruitment_prefs.special_skills,
                    'preferred_sports': recruitment_prefs.preferred_sports,
                    'preferred_venues': recruitment_prefs.preferred_venues,
                    'preferred_roles': recruitment_prefs.preferred_roles,
                    'availability_level': recruitment_prefs.availability_level,
                    'preferred_time_slots': recruitment_prefs.preferred_time_slots,
                    'max_hours_per_day': recruitment_prefs.max_hours_per_day,
                    'can_lift_heavy_items': recruitment_prefs.can_lift_heavy_items,
                    'can_stand_long_periods': recruitment_prefs.can_stand_long_periods,
                    'can_work_outdoors': recruitment_prefs.can_work_outdoors,
                    'can_work_with_crowds': recruitment_prefs.can_work_with_crowds,
                    'has_own_transport': recruitment_prefs.has_own_transport,
                    'transport_method': recruitment_prefs.transport_method,
                    'preferred_communication_method': recruitment_prefs.preferred_communication_method,
                    'training_interests': recruitment_prefs.training_interests,
                    'leadership_interest': recruitment_prefs.leadership_interest,
                }
        except Exception as e:
            logger.warning(f"Error retrieving previous recruitment data: {e}")
        
        return {}
    
    def _get_previous_games_data(self):
        """
        Get previous games information data for pre-filling
        """
        if not self.user:
            return {}
        
        try:
            recent_eoi = EOISubmission.objects.filter(
                user=self.user,
                games_information__isnull=False
            ).order_by('-created_at').first()
            
            if recent_eoi and recent_eoi.games_information:
                games_info = recent_eoi.games_information
                return {
                    't_shirt_size': games_info.t_shirt_size,
                    'dietary_requirements': games_info.dietary_requirements,
                    'has_food_allergies': games_info.has_food_allergies,
                    'food_allergy_details': games_info.food_allergy_details,
                    'requires_accommodation': games_info.requires_accommodation,
                    'accommodation_preferences': games_info.accommodation_preferences,
                    'preferred_shifts': games_info.preferred_shifts,
                    'how_did_you_hear': games_info.how_did_you_hear,
                }
        except Exception as e:
            logger.warning(f"Error retrieving previous games data: {e}")
        
        return {}
    
    def _get_corporate_group_data(self):
        """
        Get corporate group data for pre-filling
        """
        # This would be implemented based on how corporate groups are managed
        # For now, return empty dict
        return {}


class JustGoIntegrationRouter:
    """
    Handles JustGo integration for returning volunteers
    """
    
    def __init__(self, request, eoi_submission):
        self.request = request
        self.eoi_submission = eoi_submission
        self.user = request.user if request.user.is_authenticated else None
        self.justgo_client = JustGoAPIClient()
    
    def check_existing_member(self, email):
        """
        Check if volunteer exists in JustGo system
        """
        try:
            member_data = self.justgo_client.lookup_member_by_email(email)
            if member_data:
                log_audit_event(
                    user=self.user,
                    action='JUSTGO_MEMBER_FOUND',
                    resource_type='EOISubmission',
                    resource_id=str(self.eoi_submission.id),
                    details={
                        'email': email,
                        'member_id': member_data.get('member_id'),
                        'membership_type': member_data.get('membership_type')
                    }
                )
                return member_data
        except Exception as e:
            logger.warning(f"Error checking JustGo member: {e}")
        
        return None
    
    def pre_fill_from_justgo(self, email):
        """
        Pre-fill EOI data from JustGo member information
        """
        member_data = self.check_existing_member(email)
        if not member_data:
            return {}
        
        # Map JustGo data to EOI fields
        pre_fill_data = {}
        
        # Profile information mapping
        if 'personal_details' in member_data:
            personal = member_data['personal_details']
            pre_fill_data.update({
                'first_name': personal.get('first_name'),
                'last_name': personal.get('last_name'),
                'date_of_birth': personal.get('date_of_birth'),
                'phone_number': personal.get('phone'),
                'address_line_1': personal.get('address_line_1'),
                'city': personal.get('city'),
                'state_province': personal.get('state'),
                'postal_code': personal.get('postal_code'),
            })
        
        # Emergency contact mapping
        if 'emergency_contact' in member_data:
            emergency = member_data['emergency_contact']
            pre_fill_data.update({
                'emergency_contact_name': emergency.get('name'),
                'emergency_contact_phone': emergency.get('phone'),
                'emergency_contact_relationship': emergency.get('relationship'),
            })
        
        return pre_fill_data
    
    def validate_credentials(self, role_requirements):
        """
        Validate volunteer credentials against role requirements
        """
        if not self.user or not self.user.email:
            return False
        
        try:
            credentials = self.justgo_client.get_member_credentials(self.user.email)
            if credentials:
                # Implement credential validation logic
                # This would check if the volunteer has required certifications
                return self.justgo_client.validate_credentials_for_role(
                    credentials, role_requirements
                )
        except Exception as e:
            logger.warning(f"Error validating credentials: {e}")
        
        return False


def get_workflow_router(request, eoi_submission):
    """
    Factory function to get the appropriate workflow router
    """
    return VolunteerWorkflowRouter(request, eoi_submission)


def get_justgo_router(request, eoi_submission):
    """
    Factory function to get the JustGo integration router
    """
    return JustGoIntegrationRouter(request, eoi_submission) 