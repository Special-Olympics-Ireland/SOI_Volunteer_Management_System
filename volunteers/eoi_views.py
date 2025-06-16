"""
Expression of Interest (EOI) Views for ISG 2026 Volunteer Management System

This module contains views for handling the three-part EOI form system:
1. Profile Information (personal details, contact, demographics)
2. Recruitment Preferences (venue preferences, sports, skills, roles)
3. Games Information (photo upload, t-shirt, dietary, availability)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db import transaction
import json
import logging

from .eoi_models import (
    EOISubmission, 
    EOIProfileInformation, 
    EOIRecruitmentPreferences, 
    EOIGamesInformation,
    CorporateVolunteerGroup
)
from .eoi_forms import (
    EOISubmissionForm,
    EOIProfileInformationForm,
    EOIRecruitmentPreferencesForm,
    EOIGamesInformationForm,
    CorporateVolunteerGroupForm
)
from .models import VolunteerProfile
from .eoi_workflow import get_workflow_router, get_justgo_router
from .eoi_file_handlers import process_volunteer_photo
from common.audit import log_audit_event

User = get_user_model()
logger = logging.getLogger(__name__)


def eoi_start(request):
    """
    Start the EOI process - volunteer type selection
    """
    if request.method == 'POST':
        form = EOISubmissionForm(request.POST)
        if form.is_valid():
            # Create new EOI submission
            eoi_submission = form.save(commit=False)
            
            # Associate with user if logged in
            if request.user.is_authenticated:
                eoi_submission.user = request.user
            else:
                # Store session key for anonymous users
                eoi_submission.session_key = request.session.session_key or request.session.create()
            
            eoi_submission.save()
            
            # Log audit event
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='EOI_STARTED',
                model_name='EOISubmission',
                object_id=str(eoi_submission.id),
                details={
                    'volunteer_type': eoi_submission.volunteer_type,
                    'session_key': eoi_submission.session_key if not request.user.is_authenticated else None
                }
            )
            
            # Redirect based on volunteer type
            if eoi_submission.volunteer_type == 'CORPORATE':
                return redirect('volunteers:eoi_corporate_group', submission_id=eoi_submission.id)
            else:
                return redirect('volunteers:eoi_profile', submission_id=eoi_submission.id)
    else:
        form = EOISubmissionForm()
    
    context = {
        'form': form,
        'title': _('Volunteer Expression of Interest'),
        'step': 0,
        'total_steps': 3
    }
    return render(request, 'volunteers/eoi/start.html', context)


def eoi_profile(request, submission_id):
    """
    Profile Information section (Part 1 of 3)
    """
    # Get EOI submission
    eoi_submission = get_object_or_404(EOISubmission, id=submission_id)
    
    # Verify access (user or session)
    if not _verify_eoi_access(request, eoi_submission):
        messages.error(request, _('You do not have permission to access this EOI submission.'))
        return redirect('volunteers:eoi_start')
    
    # Get workflow router for this volunteer type
    workflow_router = get_workflow_router(request, eoi_submission)
    
    # Get or create profile information
    try:
        profile_info = eoi_submission.profile_information
    except EOIProfileInformation.DoesNotExist:
        profile_info = None
    
    # Pre-fill data based on volunteer type and existing information
    initial_data = workflow_router.pre_fill_data('profile')
    
    # For returning volunteers, also check JustGo integration
    if eoi_submission.volunteer_type == 'RETURNING' and request.user.is_authenticated:
        justgo_router = get_justgo_router(request, eoi_submission)
        justgo_data = justgo_router.pre_fill_from_justgo(request.user.email)
        initial_data.update(justgo_data)
    
    if request.method == 'POST':
        form = EOIProfileInformationForm(request.POST, instance=profile_info)
        if form.is_valid():
            # Save profile information
            profile_info = form.save(commit=False)
            profile_info.eoi_submission = eoi_submission
            profile_info.save()
            
            # Mark profile section as complete
            eoi_submission.profile_section_complete = True
            eoi_submission.save()
            
            # Log audit event
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='EOI_PROFILE_COMPLETED',
                model_name='EOISubmission',
                object_id=str(eoi_submission.id),
                details={'profile_completed': True}
            )
            
            messages.success(request, _('Profile information saved successfully!'))
            
            # Determine next step based on workflow
            next_step = workflow_router.get_next_step('profile')
            if next_step == 'recruitment':
                return redirect('volunteers:eoi_recruitment', submission_id=eoi_submission.id)
            elif next_step == 'games':
                return redirect('volunteers:eoi_games', submission_id=eoi_submission.id)
            elif next_step == 'review':
                return redirect('volunteers:eoi_review', submission_id=eoi_submission.id)
            else:
                return redirect('volunteers:eoi_recruitment', submission_id=eoi_submission.id)
    else:
        # Create form with initial data (pre-filled for returning volunteers)
        if profile_info:
            form = EOIProfileInformationForm(instance=profile_info)
        else:
            form = EOIProfileInformationForm(initial=initial_data)
    
    context = {
        'form': form,
        'eoi_submission': eoi_submission,
        'title': _('Profile Information'),
        'step': 1,
        'total_steps': 3,
        'progress_percentage': 33
    }
    return render(request, 'volunteers/eoi/profile.html', context)


def eoi_recruitment(request, submission_id):
    """
    Recruitment Preferences section (Part 2 of 3)
    """
    # Get EOI submission
    eoi_submission = get_object_or_404(EOISubmission, id=submission_id)
    
    # Verify access
    if not _verify_eoi_access(request, eoi_submission):
        messages.error(request, _('You do not have permission to access this EOI submission.'))
        return redirect('volunteers:eoi_start')
    
    # Get workflow router
    workflow_router = get_workflow_router(request, eoi_submission)
    
    # Check if profile section is complete
    if not eoi_submission.profile_section_complete:
        messages.warning(request, _('Please complete the profile information section first.'))
        return redirect('volunteers:eoi_profile', submission_id=eoi_submission.id)
    
    # Get or create recruitment preferences
    try:
        recruitment_prefs = eoi_submission.recruitment_preferences
    except EOIRecruitmentPreferences.DoesNotExist:
        recruitment_prefs = None
    
    # Pre-fill data for returning volunteers
    initial_data = workflow_router.pre_fill_data('recruitment')
    
    if request.method == 'POST':
        form = EOIRecruitmentPreferencesForm(request.POST, instance=recruitment_prefs)
        if form.is_valid():
            # Save recruitment preferences
            recruitment_prefs = form.save(commit=False)
            recruitment_prefs.eoi_submission = eoi_submission
            recruitment_prefs.save()
            
            # Mark recruitment section as complete
            eoi_submission.recruitment_section_complete = True
            eoi_submission.save()
            
            # Log audit event
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='EOI_RECRUITMENT_COMPLETED',
                model_name='EOISubmission',
                object_id=str(eoi_submission.id),
                details={'recruitment_completed': True}
            )
            
            messages.success(request, _('Recruitment preferences saved successfully!'))
            
            # Determine next step based on workflow
            next_step = workflow_router.get_next_step('recruitment')
            if next_step == 'games':
                return redirect('volunteers:eoi_games', submission_id=eoi_submission.id)
            elif next_step == 'review':
                return redirect('volunteers:eoi_review', submission_id=eoi_submission.id)
            else:
                return redirect('volunteers:eoi_games', submission_id=eoi_submission.id)
    else:
        # Create form with initial data for returning volunteers
        if recruitment_prefs:
            form = EOIRecruitmentPreferencesForm(instance=recruitment_prefs)
        else:
            form = EOIRecruitmentPreferencesForm(initial=initial_data)
    
    # Get dynamic form data based on volunteer type
    dynamic_context = _get_dynamic_form_context(eoi_submission.volunteer_type)
    
    context = {
        'form': form,
        'eoi_submission': eoi_submission,
        'title': _('Recruitment Preferences'),
        'step': 2,
        'total_steps': 3,
        'progress_percentage': 66,
        **dynamic_context
    }
    return render(request, 'volunteers/eoi/recruitment.html', context)


def eoi_games(request, submission_id):
    """
    Games Information section (Part 3 of 3)
    """
    # Get EOI submission
    eoi_submission = get_object_or_404(EOISubmission, id=submission_id)
    
    # Verify access
    if not _verify_eoi_access(request, eoi_submission):
        messages.error(request, _('You do not have permission to access this EOI submission.'))
        return redirect('volunteers:eoi_start')
    
    # Check if previous sections are complete
    if not eoi_submission.recruitment_section_complete:
        messages.warning(request, _('Please complete the recruitment preferences section first.'))
        return redirect('volunteers:eoi_recruitment', submission_id=eoi_submission.id)
    
    # Get or create games information
    try:
        games_info = eoi_submission.games_information
    except EOIGamesInformation.DoesNotExist:
        games_info = None
    
    if request.method == 'POST':
        form = EOIGamesInformationForm(request.POST, request.FILES, instance=games_info)
        if form.is_valid():
            # Process photo upload if present
            photo_data = None
            if 'volunteer_photo' in request.FILES:
                try:
                    user_id = request.user.id if request.user.is_authenticated else None
                    photo_data = process_volunteer_photo(
                        request.FILES['volunteer_photo'],
                        user_id=user_id,
                        eoi_submission_id=str(eoi_submission.id)
                    )
                    logger.info(f"Photo processed successfully for EOI {eoi_submission.id}")
                except ValidationError as e:
                    form.add_error('volunteer_photo', e)
                    photo_data = None
                except Exception as e:
                    logger.error(f"Error processing photo for EOI {eoi_submission.id}: {e}")
                    form.add_error('volunteer_photo', _('Error processing photo. Please try again.'))
                    photo_data = None
            
            # Only save if no photo processing errors
            if not form.errors:
                # Save games information
                games_info = form.save(commit=False)
                games_info.eoi_submission = eoi_submission
                
                # Update photo path if photo was processed
                if photo_data:
                    games_info.volunteer_photo = photo_data['main_path']
                
                games_info.save()
            
            # Mark games section as complete
            eoi_submission.games_section_complete = True
            eoi_submission.save()
            
            # Log audit event
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='EOI_GAMES_COMPLETED',
                model_name='EOISubmission',
                object_id=str(eoi_submission.id),
                details={'games_completed': True}
            )
            
            messages.success(request, _('Games information saved successfully!'))
            
            # Redirect to review/submit page
            return redirect('volunteers:eoi_review', submission_id=eoi_submission.id)
    else:
        form = EOIGamesInformationForm(instance=games_info)
    
    # Get corporate groups for dropdown
    corporate_groups = CorporateVolunteerGroup.objects.filter(status='ACTIVE').order_by('name')
    
    context = {
        'form': form,
        'eoi_submission': eoi_submission,
        'corporate_groups': corporate_groups,
        'title': _('Games Information'),
        'step': 3,
        'total_steps': 3,
        'progress_percentage': 100
    }
    return render(request, 'volunteers/eoi/games.html', context)


def eoi_review(request, submission_id):
    """
    Review and submit EOI
    """
    # Get EOI submission
    eoi_submission = get_object_or_404(EOISubmission, id=submission_id)
    
    # Verify access
    if not _verify_eoi_access(request, eoi_submission):
        messages.error(request, _('You do not have permission to access this EOI submission.'))
        return redirect('volunteers:eoi_start')
    
    # Check if all sections are complete
    if not eoi_submission.is_complete():
        messages.warning(request, _('Please complete all sections before submitting.'))
        next_section = eoi_submission.get_next_section()
        if next_section == 'profile':
            return redirect('volunteers:eoi_profile', submission_id=eoi_submission.id)
        elif next_section == 'recruitment':
            return redirect('volunteers:eoi_recruitment', submission_id=eoi_submission.id)
        elif next_section == 'games':
            return redirect('volunteers:eoi_games', submission_id=eoi_submission.id)
    
    if request.method == 'POST':
        if 'submit_eoi' in request.POST:
            try:
                with transaction.atomic():
                    # Submit the EOI
                    eoi_submission.submit()
                    
                    # Send confirmation email
                    _send_confirmation_email(eoi_submission)
                    
                    # Create volunteer profile if user is authenticated
                    if request.user.is_authenticated:
                        _create_volunteer_profile(eoi_submission)
                    
                    # Log audit event
                    log_audit_event(
                        user=request.user if request.user.is_authenticated else None,
                        action='EOI_SUBMITTED',
                        model_name='EOISubmission',
                        object_id=str(eoi_submission.id),
                        details={
                            'submitted_at': eoi_submission.submitted_at.isoformat(),
                            'volunteer_type': eoi_submission.volunteer_type
                        }
                    )
                    
                    messages.success(request, _('Your Expression of Interest has been submitted successfully!'))
                    return redirect('volunteers:eoi_confirmation', submission_id=eoi_submission.id)
                    
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.error(f"Error submitting EOI {submission_id}: {str(e)}")
                messages.error(request, _('An error occurred while submitting your EOI. Please try again.'))
    
    context = {
        'eoi_submission': eoi_submission,
        'profile_info': eoi_submission.profile_information,
        'recruitment_prefs': eoi_submission.recruitment_preferences,
        'games_info': eoi_submission.games_information,
        'title': _('Review Your Application'),
        'step': 4,
        'total_steps': 4
    }
    return render(request, 'volunteers/eoi/review.html', context)


def eoi_confirmation(request, submission_id):
    """
    EOI submission confirmation page
    """
    # Get EOI submission
    eoi_submission = get_object_or_404(EOISubmission, id=submission_id)
    
    # Verify access
    if not _verify_eoi_access(request, eoi_submission):
        messages.error(request, _('You do not have permission to access this EOI submission.'))
        return redirect('volunteers:eoi_start')
    
    # Check if EOI is submitted
    if eoi_submission.status not in [EOISubmission.SubmissionStatus.SUBMITTED, 
                                     EOISubmission.SubmissionStatus.UNDER_REVIEW,
                                     EOISubmission.SubmissionStatus.APPROVED]:
        messages.warning(request, _('This EOI has not been submitted yet.'))
        return redirect('volunteers:eoi_review', submission_id=eoi_submission.id)
    
    context = {
        'eoi_submission': eoi_submission,
        'title': _('Application Submitted'),
        'next_steps': _get_next_steps_info(eoi_submission.volunteer_type)
    }
    return render(request, 'volunteers/eoi/confirmation.html', context)


@require_http_methods(["GET"])
def eoi_status(request, submission_id):
    """
    Check EOI submission status (AJAX endpoint)
    """
    try:
        eoi_submission = get_object_or_404(EOISubmission, id=submission_id)
        
        # Verify access
        if not _verify_eoi_access(request, eoi_submission):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        return JsonResponse({
            'status': eoi_submission.status,
            'status_display': eoi_submission.get_status_display(),
            'completion_percentage': eoi_submission.completion_percentage,
            'profile_complete': eoi_submission.profile_section_complete,
            'recruitment_complete': eoi_submission.recruitment_section_complete,
            'games_complete': eoi_submission.games_section_complete,
            'submitted_at': eoi_submission.submitted_at.isoformat() if eoi_submission.submitted_at else None,
            'next_section': eoi_submission.get_next_section()
        })
    except Exception as e:
        logger.error(f"Error getting EOI status {submission_id}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def eoi_corporate_group(request, submission_id):
    """
    Corporate Group Selection section (for corporate volunteers)
    """
    # Get EOI submission
    eoi_submission = get_object_or_404(EOISubmission, id=submission_id)
    
    # Verify access
    if not _verify_eoi_access(request, eoi_submission):
        messages.error(request, _('You do not have permission to access this EOI submission.'))
        return redirect('volunteers:eoi_start')
    
    # Verify this is a corporate volunteer
    if eoi_submission.volunteer_type != 'CORPORATE':
        messages.error(request, _('This section is only for corporate volunteers.'))
        return redirect('volunteers:eoi_profile', submission_id=eoi_submission.id)
    
    # Get workflow router
    workflow_router = get_workflow_router(request, eoi_submission)
    
    # Get active corporate groups
    corporate_groups = CorporateVolunteerGroup.objects.filter(status='ACTIVE')
    
    if request.method == 'POST':
        group_id = request.POST.get('corporate_group_id')
        if group_id:
            try:
                selected_group = CorporateVolunteerGroup.objects.get(id=group_id, status='ACTIVE')
                
                # Update the EOI submission with corporate group info
                if hasattr(eoi_submission, 'games_information') and eoi_submission.games_information:
                    games_info = eoi_submission.games_information
                    games_info.is_part_of_group = True
                    games_info.group_name = selected_group.name
                    games_info.save()
                
                # Log audit event
                log_audit_event(
                    user=request.user if request.user.is_authenticated else None,
                    action='EOI_CORPORATE_GROUP_SELECTED',
                    resource_type='EOISubmission',
                    resource_id=str(eoi_submission.id),
                    details={
                        'group_id': str(selected_group.id),
                        'group_name': selected_group.name
                    }
                )
                
                messages.success(request, _('Corporate group selected successfully!'))
                
                # Determine next step
                next_step = workflow_router.get_next_step('corporate_group')
                if next_step == 'profile':
                    return redirect('volunteers:eoi_profile', submission_id=eoi_submission.id)
                else:
                    return redirect('volunteers:eoi_profile', submission_id=eoi_submission.id)
                    
            except CorporateVolunteerGroup.DoesNotExist:
                messages.error(request, _('Invalid corporate group selected.'))
        else:
            messages.error(request, _('Please select a corporate group.'))
    
    context = {
        'eoi_submission': eoi_submission,
        'corporate_groups': corporate_groups,
        'title': _('Select Corporate Group'),
        'step': 0,
        'total_steps': 4,
        'progress_percentage': 20
    }
    return render(request, 'volunteers/eoi/corporate_group.html', context)


def corporate_group_register(request):
    """
    Corporate group registration
    """
    if request.method == 'POST':
        form = CorporateVolunteerGroupForm(request.POST)
        if form.is_valid():
            corporate_group = form.save()
            
            # Log audit event
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='CORPORATE_GROUP_REGISTERED',
                model_name='CorporateVolunteerGroup',
                object_id=str(corporate_group.id),
                details={
                    'group_name': corporate_group.name,
                    'expected_volunteers': corporate_group.expected_volunteer_count
                }
            )
            
            messages.success(request, _(
                'Corporate group registration submitted successfully! '
                'You will receive confirmation once approved.'
            ))
            return redirect('volunteers:corporate_group_success')
    else:
        form = CorporateVolunteerGroupForm()
    
    context = {
        'form': form,
        'title': _('Corporate Group Registration')
    }
    return render(request, 'volunteers/corporate_group_register.html', context)


def corporate_group_success(request):
    """
    Corporate group registration success page
    """
    context = {
        'title': _('Corporate Group Registration Submitted')
    }
    return render(request, 'volunteers/corporate_group_success.html', context)


@require_http_methods(["GET"])
def get_corporate_groups(request):
    """
    Get active corporate groups (AJAX endpoint)
    """
    try:
        groups = CorporateVolunteerGroup.objects.filter(status='ACTIVE').values(
            'id', 'name', 'description', 'expected_volunteer_count'
        ).order_by('name')
        
        return JsonResponse({
            'groups': list(groups)
        })
    except Exception as e:
        logger.error(f"Error getting corporate groups: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@require_http_methods(["POST"])
def check_justgo_membership(request):
    """
    AJAX endpoint to check JustGo membership and return pre-fill data
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        submission_id = data.get('submission_id')
        
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
        
        if not submission_id:
            return JsonResponse({'error': 'Submission ID is required'}, status=400)
        
        # Get EOI submission
        try:
            eoi_submission = EOISubmission.objects.get(id=submission_id)
        except EOISubmission.DoesNotExist:
            return JsonResponse({'error': 'Invalid submission'}, status=404)
        
        # Verify access
        if not _verify_eoi_access(request, eoi_submission):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Check JustGo membership
        justgo_router = get_justgo_router(request, eoi_submission)
        member_data = justgo_router.check_existing_member(email)
        
        if member_data:
            # Get pre-fill data from JustGo
            pre_fill_data = justgo_router.pre_fill_from_justgo(email)
            
            # Log the successful lookup
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='JUSTGO_LOOKUP_SUCCESS',
                model_name='EOISubmission',
                object_id=str(eoi_submission.id),
                details={
                    'email': email,
                    'member_found': True,
                    'member_id': member_data.get('member_id'),
                    'membership_type': member_data.get('membership_type')
                }
            )
            
            return JsonResponse({
                'success': True,
                'member_found': True,
                'member_data': {
                    'member_id': member_data.get('member_id'),
                    'membership_type': member_data.get('membership_type'),
                    'membership_status': member_data.get('status'),
                    'last_event': member_data.get('last_event')
                },
                'pre_fill_data': pre_fill_data,
                'message': _('JustGo membership found! Your details have been pre-filled.')
            })
        else:
            # Log the unsuccessful lookup
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='JUSTGO_LOOKUP_NOT_FOUND',
                model_name='EOISubmission',
                object_id=str(eoi_submission.id),
                details={
                    'email': email,
                    'member_found': False
                }
            )
            
            return JsonResponse({
                'success': True,
                'member_found': False,
                'message': _('No JustGo membership found for this email address. You can continue with manual entry.')
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error checking JustGo membership: {e}")
        return JsonResponse({
            'error': _('An error occurred while checking membership. Please try again.')
        }, status=500)


# Helper Functions

def _verify_eoi_access(request, eoi_submission):
    """
    Verify that the user has access to the EOI submission
    """
    if request.user.is_authenticated:
        # Authenticated users can access their own submissions or staff can access any
        return (eoi_submission.user == request.user or 
                request.user.is_staff or 
                request.user.user_type in ['STAFF', 'VMT', 'CVT', 'GOC', 'ADMIN'])
    else:
        # Anonymous users can access via session key
        return (eoi_submission.session_key and 
                eoi_submission.session_key == request.session.session_key)


def _get_dynamic_form_context(volunteer_type):
    """
    Get dynamic form context based on volunteer type
    """
    context = {}
    
    if volunteer_type == 'CORPORATE_VOLUNTEER':
        context.update({
            'show_corporate_fields': True,
            'corporate_help_text': _(
                'As a corporate volunteer, you may have specific group requirements '
                'and preferences. Please coordinate with your group leader.'
            )
        })
    elif volunteer_type == 'STUDENT_VOLUNTEER':
        context.update({
            'show_student_fields': True,
            'student_help_text': _(
                'Student volunteers may be eligible for additional training opportunities '
                'and flexible scheduling options.'
            )
        })
    elif volunteer_type == 'SPECIALIST_VOLUNTEER':
        context.update({
            'show_specialist_fields': True,
            'specialist_help_text': _(
                'Specialist volunteers with professional skills may be matched '
                'with roles that utilize their expertise.'
            )
        })
    elif volunteer_type == 'FAMILY_VOLUNTEER':
        context.update({
            'show_family_fields': True,
            'family_help_text': _(
                'Family volunteers can be assigned to roles that allow them '
                'to work together or in nearby locations.'
            )
        })
    
    return context


def _send_confirmation_email(eoi_submission):
    """
    Send confirmation email to volunteer
    """
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings
        
        profile_info = eoi_submission.profile_information
        if not profile_info or not profile_info.email:
            logger.warning(f"No email address found for EOI {eoi_submission.id}")
            return
        
        # Prepare email context
        volunteer_name = f"{profile_info.first_name} {profile_info.last_name}"
        if profile_info.preferred_name:
            volunteer_name = f"{profile_info.preferred_name} ({profile_info.first_name} {profile_info.last_name})"
        
        context = {
            'volunteer_name': volunteer_name,
            'reference_number': str(eoi_submission.id)[:8].upper(),
            'volunteer_type': eoi_submission.get_volunteer_type_display(),
            'submission_date': eoi_submission.created_at.strftime('%B %d, %Y'),
            'completion_percentage': eoi_submission.completion_percentage,
            'email_address': profile_info.email,
        }
        
        # Render email templates
        subject = f"EOI Confirmation - ISG 2026 Volunteer Application #{context['reference_number']}"
        text_content = render_to_string('emails/volunteers/eoi_confirmation.txt', context)
        html_content = render_to_string('emails/volunteers/eoi_confirmation.html', context)
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'volunteers@isg2026.ie'),
            to=[profile_info.email],
            reply_to=['volunteers@isg2026.ie']
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        # Mark confirmation email as sent
        eoi_submission.confirmation_email_sent = True
        eoi_submission.confirmation_email_sent_at = timezone.now()
        eoi_submission.save(update_fields=['confirmation_email_sent', 'confirmation_email_sent_at'])
        
        logger.info(f"Confirmation email sent to {profile_info.email} for EOI {eoi_submission.id}")
        
    except Exception as e:
        logger.error(f"Error sending confirmation email for EOI {eoi_submission.id}: {str(e)}")
        # Don't raise the exception to avoid breaking the submission process


def _create_volunteer_profile(eoi_submission):
    """
    Create VolunteerProfile from EOI submission for authenticated users
    """
    try:
        if not eoi_submission.user:
            return
        
        # Check if volunteer profile already exists
        if hasattr(eoi_submission.user, 'volunteer_profile'):
            return
        
        profile_info = eoi_submission.profile_information
        recruitment_prefs = eoi_submission.recruitment_preferences
        games_info = eoi_submission.games_information
        
        # Create volunteer profile
        volunteer_profile = VolunteerProfile.objects.create(
            user=eoi_submission.user,
            status=VolunteerProfile.VolunteerStatus.PENDING,
            preferred_name=profile_info.preferred_name,
            emergency_contact_name=profile_info.emergency_contact_name,
            emergency_contact_phone=profile_info.emergency_contact_phone,
            emergency_contact_relationship=profile_info.emergency_contact_relationship,
            medical_conditions=profile_info.medical_conditions,
            dietary_requirements=games_info.dietary_requirements,
            mobility_requirements=profile_info.mobility_requirements,
            experience_level=recruitment_prefs.volunteer_experience_level,
            previous_events=recruitment_prefs.previous_events,
            special_skills=recruitment_prefs.special_skills,
            languages_spoken=profile_info.languages_spoken,
            availability_level=recruitment_prefs.availability_level,
            max_hours_per_day=recruitment_prefs.max_hours_per_day,
            preferred_roles=recruitment_prefs.preferred_roles,
            preferred_venues=recruitment_prefs.preferred_venues,
            preferred_sports=recruitment_prefs.preferred_sports,
            can_lift_heavy_items=recruitment_prefs.can_lift_heavy_items,
            can_stand_long_periods=recruitment_prefs.can_stand_long_periods,
            can_work_outdoors=recruitment_prefs.can_work_outdoors,
            can_work_with_crowds=recruitment_prefs.can_work_with_crowds,
            has_own_transport=recruitment_prefs.has_own_transport,
            transport_method=recruitment_prefs.transport_method,
            t_shirt_size=games_info.t_shirt_size,
            preferred_communication_method=recruitment_prefs.preferred_communication_method,
            motivation=recruitment_prefs.motivation,
            volunteer_goals=recruitment_prefs.volunteer_goals,
            is_corporate_volunteer=games_info.is_part_of_group,
            corporate_group_name=games_info.group_name,
            group_leader_contact=games_info.group_leader_contact,
            social_media_consent=games_info.social_media_consent,
            photo_consent=games_info.photo_consent,
            testimonial_consent=games_info.testimonial_consent
        )
        
        logger.info(f"Volunteer profile created for user {eoi_submission.user.id} from EOI {eoi_submission.id}")
        
    except Exception as e:
        logger.error(f"Error creating volunteer profile from EOI {eoi_submission.id}: {str(e)}")


def _get_next_steps_info(volunteer_type):
    """
    Get next steps information based on volunteer type
    """
    base_steps = [
        _('Your application will be reviewed by our volunteer team'),
        _('You will receive an email confirmation within 2-3 business days'),
        _('If approved, you will be contacted about training opportunities'),
        _('Role assignments will be made closer to the Games dates')
    ]
    
    if volunteer_type == 'CORPORATE_VOLUNTEER':
        base_steps.insert(1, _('Your group coordinator will be contacted about group arrangements'))
    elif volunteer_type == 'SPECIALIST_VOLUNTEER':
        base_steps.insert(2, _('Your professional qualifications will be verified'))
    elif volunteer_type == 'STUDENT_VOLUNTEER':
        base_steps.insert(2, _('You may be eligible for additional training and development opportunities'))
    
    return base_steps 