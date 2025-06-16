"""
Admin Override Service

Provides comprehensive business logic for managing administrative overrides
with proper validation, workflow management, and audit logging.
"""

from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.contrib.auth import get_user_model
from typing import Dict, Any, Optional, List
import logging

from .models import AdminOverride, AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


class AdminOverrideService:
    """
    Service class for managing admin overrides with comprehensive
    validation, workflow management, and audit logging.
    """
    
    @staticmethod
    def create_override(
        title: str,
        override_type: str,
        description: str,
        justification: str,
        target_object: Any,
        requested_by: User,
        risk_level: str = 'MEDIUM',
        impact_level: str = 'LOW',
        is_emergency: bool = False,
        priority_level: int = 5,
        effective_from: Optional[timezone.datetime] = None,
        effective_until: Optional[timezone.datetime] = None,
        override_data: Optional[Dict] = None,
        business_case: str = '',
        **kwargs
    ) -> AdminOverride:
        """
        Create a new admin override with comprehensive validation.
        
        Args:
            title: Brief title for the override
            override_type: Type of override (from AdminOverride.OverrideType)
            description: Detailed description
            justification: Required justification
            target_object: The object being overridden
            requested_by: User requesting the override
            risk_level: Risk assessment level
            impact_level: Impact assessment level
            is_emergency: Whether this is an emergency override
            priority_level: Priority level (1-10)
            effective_from: When override becomes effective
            effective_until: When override expires
            override_data: Additional override data
            business_case: Business case for the override
            **kwargs: Additional fields
            
        Returns:
            AdminOverride: The created override instance
            
        Raises:
            ValidationError: If validation fails
            PermissionDenied: If user lacks permission
        """
        
        # Validate inputs
        if not title or not title.strip():
            raise ValidationError("Title is required")
        
        if not justification or not justification.strip():
            raise ValidationError("Justification is required for all overrides")
        
        if len(justification.strip()) < 20:
            raise ValidationError("Justification must be at least 20 characters")
        
        # Validate override type
        valid_types = [choice[0] for choice in AdminOverride.OverrideType.choices]
        if override_type not in valid_types:
            raise ValidationError(f"Invalid override type: {override_type}")
        
        # Validate risk and impact levels
        valid_risk_levels = [choice[0] for choice in AdminOverride.RiskLevel.choices]
        if risk_level not in valid_risk_levels:
            raise ValidationError(f"Invalid risk level: {risk_level}")
        
        valid_impact_levels = [choice[0] for choice in AdminOverride.ImpactLevel.choices]
        if impact_level not in valid_impact_levels:
            raise ValidationError(f"Invalid impact level: {impact_level}")
        
        # Validate priority level
        if not 1 <= priority_level <= 10:
            raise ValidationError("Priority level must be between 1 and 10")
        
        # Validate effective dates
        if effective_from and effective_until:
            if effective_from >= effective_until:
                raise ValidationError("Effective from date must be before effective until date")
        
        # Emergency overrides require higher justification standards
        if is_emergency:
            if len(justification.strip()) < 50:
                raise ValidationError("Emergency overrides require detailed justification (minimum 50 characters)")
            
            if risk_level not in ['HIGH', 'CRITICAL']:
                raise ValidationError("Emergency overrides must have HIGH or CRITICAL risk level")
            
            priority_level = min(priority_level, 2)  # Emergency overrides get high priority
        
        # High-risk overrides require business case
        if risk_level in ['HIGH', 'CRITICAL'] and not business_case:
            raise ValidationError("High-risk overrides require a business case")
        
        try:
            with transaction.atomic():
                # Get content type for target object
                content_type = ContentType.objects.get_for_model(target_object)
                
                # Create the override
                override = AdminOverride.objects.create(
                    title=title.strip(),
                    override_type=override_type,
                    description=description.strip(),
                    justification=justification.strip(),
                    business_case=business_case.strip(),
                    content_type=content_type,
                    object_id=str(target_object.pk),
                    requested_by=requested_by,
                    risk_level=risk_level,
                    impact_level=impact_level,
                    is_emergency=is_emergency,
                    priority_level=priority_level,
                    effective_from=effective_from,
                    effective_until=effective_until,
                    override_data=override_data or {},
                    **kwargs
                )
                
                # Log the creation
                AuditLog.objects.create(
                    action_type='CREATE',
                    action_description=f'Admin override created: {title}',
                    user=requested_by,
                    content_type=ContentType.objects.get_for_model(AdminOverride),
                    object_id=str(override.id),
                    object_representation=str(override),
                    changes={
                        'override_type': override_type,
                        'risk_level': risk_level,
                        'impact_level': impact_level,
                        'is_emergency': is_emergency
                    }
                )
                
                # Add initial communication log
                override.add_communication_log(
                    f'Override created by {requested_by.username}',
                    requested_by
                )
                
                logger.info(f"Admin override created: {override.id} by {requested_by.username}")
                
                return override
                
        except Exception as e:
            logger.error(f"Failed to create admin override: {str(e)}")
            raise ValidationError(f"Failed to create override: {str(e)}")
    
    @staticmethod
    def approve_override(
        override: AdminOverride,
        approved_by: User,
        approval_notes: str = '',
        auto_activate: bool = False
    ) -> AdminOverride:
        """
        Approve an admin override with proper validation and audit logging.
        
        Args:
            override: The override to approve
            approved_by: User approving the override
            approval_notes: Notes from the approver
            auto_activate: Whether to automatically activate after approval
            
        Returns:
            AdminOverride: The updated override instance
            
        Raises:
            ValidationError: If approval is not valid
            PermissionDenied: If user lacks permission
        """
        
        # Validate current status
        if override.status != 'PENDING':
            raise ValidationError(f"Cannot approve override with status: {override.get_status_display()}")
        
        # Validate approver is different from requester
        if override.requested_by == approved_by:
            raise ValidationError("Cannot approve your own override request")
        
        # High-risk overrides require approval notes
        if override.risk_level in ['HIGH', 'CRITICAL'] and not approval_notes:
            raise ValidationError("High-risk overrides require approval notes")
        
        try:
            with transaction.atomic():
                # Approve the override
                override.approve(approved_by, approval_notes)
                
                # Auto-activate if requested and appropriate
                if auto_activate and override.status == 'APPROVED':
                    override.activate(approved_by)
                
                # Log the approval
                AuditLog.objects.create(
                    action_type='APPROVE',
                    action_description=f'Admin override approved: {override.title}',
                    user=approved_by,
                    content_type=ContentType.objects.get_for_model(AdminOverride),
                    object_id=str(override.id),
                    object_representation=str(override),
                    changes={
                        'status': 'APPROVED',
                        'approved_by': approved_by.username,
                        'approval_notes': approval_notes
                    }
                )
                
                logger.info(f"Admin override approved: {override.id} by {approved_by.username}")
                
                return override
                
        except Exception as e:
            logger.error(f"Failed to approve admin override {override.id}: {str(e)}")
            raise ValidationError(f"Failed to approve override: {str(e)}")
    
    @staticmethod
    def reject_override(
        override: AdminOverride,
        rejected_by: User,
        rejection_reason: str
    ) -> AdminOverride:
        """
        Reject an admin override with proper validation and audit logging.
        
        Args:
            override: The override to reject
            rejected_by: User rejecting the override
            rejection_reason: Reason for rejection
            
        Returns:
            AdminOverride: The updated override instance
            
        Raises:
            ValidationError: If rejection is not valid
        """
        
        # Validate current status
        if override.status != 'PENDING':
            raise ValidationError(f"Cannot reject override with status: {override.get_status_display()}")
        
        # Validate rejection reason
        if not rejection_reason or not rejection_reason.strip():
            raise ValidationError("Rejection reason is required")
        
        if len(rejection_reason.strip()) < 10:
            raise ValidationError("Rejection reason must be at least 10 characters")
        
        try:
            with transaction.atomic():
                # Reject the override
                override.reject(rejected_by, rejection_reason)
                
                # Log the rejection
                AuditLog.objects.create(
                    action_type='REJECT',
                    action_description=f'Admin override rejected: {override.title}',
                    user=rejected_by,
                    content_type=ContentType.objects.get_for_model(AdminOverride),
                    object_id=str(override.id),
                    object_representation=str(override),
                    changes={
                        'status': 'REJECTED',
                        'rejected_by': rejected_by.username,
                        'rejection_reason': rejection_reason
                    }
                )
                
                logger.info(f"Admin override rejected: {override.id} by {rejected_by.username}")
                
                return override
                
        except Exception as e:
            logger.error(f"Failed to reject admin override {override.id}: {str(e)}")
            raise ValidationError(f"Failed to reject override: {str(e)}")
    
    @staticmethod
    def activate_override(
        override: AdminOverride,
        activated_by: User,
        activation_notes: str = ''
    ) -> AdminOverride:
        """
        Activate an approved admin override.
        
        Args:
            override: The override to activate
            activated_by: User activating the override
            activation_notes: Notes about activation
            
        Returns:
            AdminOverride: The updated override instance
            
        Raises:
            ValidationError: If activation is not valid
        """
        
        # Validate current status
        if override.status != 'APPROVED':
            raise ValidationError(f"Cannot activate override with status: {override.get_status_display()}")
        
        # Check if override is within effective period
        now = timezone.now()
        if override.effective_from and override.effective_from > now:
            raise ValidationError(f"Override is not yet effective (starts {override.effective_from})")
        
        if override.effective_until and override.effective_until < now:
            raise ValidationError(f"Override has expired ({override.effective_until})")
        
        try:
            with transaction.atomic():
                # Activate the override
                override.activate(activated_by)
                
                # Add activation notes if provided
                if activation_notes:
                    override.add_communication_log(
                        f'Activation notes: {activation_notes}',
                        activated_by
                    )
                
                # Log the activation
                AuditLog.objects.create(
                    action_type='OVERRIDE',
                    action_description=f'Admin override activated: {override.title}',
                    user=activated_by,
                    content_type=ContentType.objects.get_for_model(AdminOverride),
                    object_id=str(override.id),
                    object_representation=str(override),
                    changes={
                        'status': 'ACTIVE',
                        'activated_by': activated_by.username,
                        'applied_at': override.applied_at.isoformat() if override.applied_at else None
                    }
                )
                
                logger.info(f"Admin override activated: {override.id} by {activated_by.username}")
                
                return override
                
        except Exception as e:
            logger.error(f"Failed to activate admin override {override.id}: {str(e)}")
            raise ValidationError(f"Failed to activate override: {str(e)}")
    
    @staticmethod
    def revoke_override(
        override: AdminOverride,
        revoked_by: User,
        revocation_reason: str
    ) -> AdminOverride:
        """
        Revoke an active admin override.
        
        Args:
            override: The override to revoke
            revoked_by: User revoking the override
            revocation_reason: Reason for revocation
            
        Returns:
            AdminOverride: The updated override instance
            
        Raises:
            ValidationError: If revocation is not valid
        """
        
        # Validate current status
        if override.status != 'ACTIVE':
            raise ValidationError(f"Cannot revoke override with status: {override.get_status_display()}")
        
        # Validate revocation reason
        if not revocation_reason or not revocation_reason.strip():
            raise ValidationError("Revocation reason is required")
        
        try:
            with transaction.atomic():
                # Revoke the override
                override.revoke(revoked_by, revocation_reason)
                
                # Log the revocation
                AuditLog.objects.create(
                    action_type='OVERRIDE',
                    action_description=f'Admin override revoked: {override.title}',
                    user=revoked_by,
                    content_type=ContentType.objects.get_for_model(AdminOverride),
                    object_id=str(override.id),
                    object_representation=str(override),
                    changes={
                        'status': 'REVOKED',
                        'revoked_by': revoked_by.username,
                        'revocation_reason': revocation_reason,
                        'revoked_at': override.revoked_at.isoformat() if override.revoked_at else None
                    }
                )
                
                logger.info(f"Admin override revoked: {override.id} by {revoked_by.username}")
                
                return override
                
        except Exception as e:
            logger.error(f"Failed to revoke admin override {override.id}: {str(e)}")
            raise ValidationError(f"Failed to revoke override: {str(e)}")
    
    @staticmethod
    def get_pending_overrides(user: Optional[User] = None) -> List[AdminOverride]:
        """
        Get all pending overrides, optionally filtered by user.
        
        Args:
            user: Optional user to filter by
            
        Returns:
            List[AdminOverride]: List of pending overrides
        """
        queryset = AdminOverride.objects.filter(status='PENDING')
        
        if user:
            queryset = queryset.filter(requested_by=user)
        
        return list(queryset.select_related('requested_by').order_by('-is_emergency', 'priority_level', 'created_at'))
    
    @staticmethod
    def get_active_overrides(target_object: Optional[Any] = None) -> List[AdminOverride]:
        """
        Get all active overrides, optionally filtered by target object.
        
        Args:
            target_object: Optional target object to filter by
            
        Returns:
            List[AdminOverride]: List of active overrides
        """
        queryset = AdminOverride.objects.filter(status='ACTIVE')
        
        if target_object:
            content_type = ContentType.objects.get_for_model(target_object)
            queryset = queryset.filter(
                content_type=content_type,
                object_id=str(target_object.pk)
            )
        
        return list(queryset.select_related('requested_by', 'approved_by').order_by('-is_emergency', 'priority_level'))
    
    @staticmethod
    def get_expiring_overrides(days_ahead: int = 7) -> List[AdminOverride]:
        """
        Get overrides that will expire within the specified number of days.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List[AdminOverride]: List of expiring overrides
        """
        from datetime import timedelta
        
        cutoff_date = timezone.now() + timedelta(days=days_ahead)
        
        return list(
            AdminOverride.objects.filter(
                status='ACTIVE',
                effective_until__lte=cutoff_date,
                effective_until__gte=timezone.now()
            ).select_related('requested_by', 'approved_by').order_by('effective_until')
        )
    
    @staticmethod
    def update_monitoring(
        override: AdminOverride,
        monitored_by: User,
        monitoring_notes: str = ''
    ) -> AdminOverride:
        """
        Update monitoring information for an override.
        
        Args:
            override: The override to update
            monitored_by: User performing the monitoring
            monitoring_notes: Notes from monitoring
            
        Returns:
            AdminOverride: The updated override instance
        """
        
        try:
            with transaction.atomic():
                # Update monitoring
                override.update_monitoring(monitoring_notes, monitored_by)
                
                # Log the monitoring update
                AuditLog.objects.create(
                    action_type='UPDATE',
                    action_description=f'Admin override monitoring updated: {override.title}',
                    user=monitored_by,
                    content_type=ContentType.objects.get_for_model(AdminOverride),
                    object_id=str(override.id),
                    object_representation=str(override),
                    changes={
                        'last_monitored_at': override.last_monitored_at.isoformat() if override.last_monitored_at else None,
                        'monitoring_notes': monitoring_notes
                    }
                )
                
                return override
                
        except Exception as e:
            logger.error(f"Failed to update monitoring for admin override {override.id}: {str(e)}")
            raise ValidationError(f"Failed to update monitoring: {str(e)}")


class OverrideValidator:
    """
    Utility class for validating override requests and business rules.
    """
    
    @staticmethod
    def validate_justification_quality(justification: str, override_type: str, risk_level: str) -> List[str]:
        """
        Validate the quality and completeness of justification.
        
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        if not justification or not justification.strip():
            errors.append("Justification is required")
            return errors
        
        justification = justification.strip()
        
        # Minimum length requirements
        min_lengths = {
            'LOW': 20,
            'MEDIUM': 30,
            'HIGH': 50,
            'CRITICAL': 100
        }
        
        min_length = min_lengths.get(risk_level, 20)
        if len(justification) < min_length:
            errors.append(f"Justification must be at least {min_length} characters for {risk_level} risk overrides")
        
        # Check for specific keywords based on override type
        required_keywords = {
            'AGE_REQUIREMENT': ['age', 'requirement', 'exception'],
            'CREDENTIAL_REQUIREMENT': ['credential', 'qualification', 'experience'],
            'CAPACITY_LIMIT': ['capacity', 'limit', 'exceed'],
            'EMERGENCY_ACCESS': ['emergency', 'urgent', 'immediate'],
            'SYSTEM_RULE': ['system', 'rule', 'policy']
        }
        
        if override_type in required_keywords:
            keywords = required_keywords[override_type]
            found_keywords = [kw for kw in keywords if kw.lower() in justification.lower()]
            
            if len(found_keywords) < 2:
                errors.append(f"Justification should include relevant terms: {', '.join(keywords)}")
        
        return errors
    
    @staticmethod
    def check_override_conflicts(target_object: Any, override_type: str) -> List[str]:
        """
        Check for conflicting active overrides on the same object.
        
        Returns:
            List[str]: List of conflict warnings
        """
        warnings = []
        
        try:
            content_type = ContentType.objects.get_for_model(target_object)
            
            # Check for existing active overrides
            existing_overrides = AdminOverride.objects.filter(
                content_type=content_type,
                object_id=str(target_object.pk),
                status='ACTIVE'
            )
            
            if existing_overrides.exists():
                warnings.append(f"There are {existing_overrides.count()} active override(s) on this object")
            
            # Check for same type overrides
            same_type_overrides = existing_overrides.filter(override_type=override_type)
            if same_type_overrides.exists():
                warnings.append(f"There is already an active {override_type} override on this object")
            
        except Exception:
            # If we can't check, just continue
            pass
        
        return warnings 