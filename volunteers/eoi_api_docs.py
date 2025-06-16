"""
EOI API Documentation for ISG 2026 Volunteer Management System

This module provides comprehensive documentation for the EOI REST API endpoints,
including request/response examples and usage guidelines.
"""

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status

# Common examples and schemas
EOI_SUBMISSION_EXAMPLE = {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_email": "volunteer@example.com",
    "volunteer_type": "RETURNING",
    "volunteer_type_display": "Returning Volunteer",
    "status": "SUBMITTED",
    "status_display": "Submitted",
    "completion_percentage": 100,
    "profile_completed": True,
    "recruitment_completed": True,
    "games_completed": True,
    "submitted_at": "2024-06-13T10:30:00Z",
    "created_at": "2024-06-13T10:00:00Z",
    "confirmation_email_sent": True,
    "confirmation_email_sent_at": "2024-06-13T10:31:00Z"
}

PROFILE_INFORMATION_EXAMPLE = {
    "first_name": "John",
    "last_name": "Doe",
    "preferred_name": "Johnny",
    "date_of_birth": "1995-05-15",
    "age": 29,
    "gender": "MALE",
    "email": "john.doe@example.com",
    "phone_number": "+61412345678",
    "address_line_1": "123 Main Street",
    "city": "Melbourne",
    "state_province": "VIC",
    "postal_code": "3000",
    "country": "Australia",
    "emergency_contact_name": "Jane Doe",
    "emergency_contact_phone": "+61487654321",
    "emergency_contact_relationship": "SPOUSE",
    "education_level": "BACHELOR",
    "employment_status": "FULL_TIME",
    "occupation": "Software Developer",
    "languages_spoken": ["English", "Spanish"],
    "nationality": "Australian"
}

RECRUITMENT_PREFERENCES_EXAMPLE = {
    "volunteer_experience_level": "EXPERIENCED",
    "previous_events": ["Commonwealth Games 2018", "Australian Open 2023"],
    "motivation": "I am passionate about sports and want to contribute to making the ISG 2026 a memorable experience for all participants and spectators.",
    "preferred_sports": ["ATHLETICS", "SWIMMING", "BASKETBALL"],
    "preferred_venues": ["MCG", "AQUATIC_CENTRE"],
    "preferred_roles": ["SPECTATOR_SERVICES", "ATHLETE_SERVICES"],
    "availability_level": "HIGH",
    "max_hours_per_day": 8,
    "can_lift_heavy_items": True,
    "can_stand_long_periods": True,
    "can_work_outdoors": True,
    "can_work_with_crowds": True,
    "has_own_transport": True,
    "transport_method": "CAR",
    "training_interests": ["LEADERSHIP", "FIRST_AID"],
    "leadership_interest": True
}

GAMES_INFORMATION_EXAMPLE = {
    "t_shirt_size": "MEDIUM",
    "photo_consent": True,
    "dietary_requirements": "VEGETARIAN",
    "has_food_allergies": False,
    "available_dates": ["2026-03-15", "2026-03-16", "2026-03-17"],
    "preferred_shifts": ["MORNING", "AFTERNOON"],
    "requires_accommodation": False,
    "social_media_consent": True,
    "testimonial_consent": True,
    "is_part_of_group": False,
    "terms_accepted": True,
    "privacy_policy_accepted": True,
    "code_of_conduct_accepted": True
}

CORPORATE_GROUP_EXAMPLE = {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "name": "Tech Solutions Pty Ltd",
    "description": "Leading technology company committed to community engagement",
    "website": "https://techsolutions.com.au",
    "primary_contact_name": "Sarah Johnson",
    "primary_contact_email": "sarah.johnson@techsolutions.com.au",
    "primary_contact_phone": "+61398765432",
    "address_line_1": "456 Collins Street",
    "city": "Melbourne",
    "state_province": "VIC",
    "postal_code": "3000",
    "country": "Australia",
    "expected_volunteer_count": 25,
    "volunteer_count": 18,
    "industry_sector": "TECHNOLOGY",
    "status": "ACTIVE",
    "created_at": "2024-06-01T09:00:00Z"
}

# Schema decorators for API views
eoi_submission_list_create_schema = extend_schema(
    summary="List or create EOI submissions",
    description="""
    **GET**: List all EOI submissions (staff only)
    - Supports filtering by status, volunteer_type, confirmation_email_sent
    - Supports searching by volunteer name and email
    - Supports ordering by created_at, submitted_at, completion_percentage
    - Returns paginated results (20 per page by default)
    
    **POST**: Create a new EOI submission (public)
    - Accepts complete EOI data including profile, recruitment, and games information
    - Automatically sets status to SUBMITTED and sends confirmation email
    - Returns the created submission with all related data
    """,
    parameters=[
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by submission status',
            enum=['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'CONFIRMED', 'CANCELLED', 'WITHDRAWN', 'PENDING_INFO']
        ),
        OpenApiParameter(
            name='volunteer_type',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by volunteer type',
            enum=['NEW', 'RETURNING', 'CORPORATE']
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search by volunteer name or email'
        ),
        OpenApiParameter(
            name='ordering',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Order results by field (prefix with - for descending)',
            enum=['created_at', '-created_at', 'submitted_at', '-submitted_at', 'completion_percentage', '-completion_percentage']
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Page number for pagination'
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of results per page (max 100)'
        ),
    ],
    examples=[
        OpenApiExample(
            name="EOI Submission List Response",
            value={
                "count": 150,
                "next": "http://api.example.com/volunteers/api/eoi/submissions/?page=2",
                "previous": None,
                "results": [EOI_SUBMISSION_EXAMPLE]
            },
            response_only=True,
            status_codes=[status.HTTP_200_OK]
        ),
        OpenApiExample(
            name="Create EOI Submission Request",
            value={
                "volunteer_type": "NEW",
                "profile_information": PROFILE_INFORMATION_EXAMPLE,
                "recruitment_preferences": RECRUITMENT_PREFERENCES_EXAMPLE,
                "games_information": GAMES_INFORMATION_EXAMPLE
            },
            request_only=True
        ),
        OpenApiExample(
            name="Create EOI Submission Response",
            value={
                **EOI_SUBMISSION_EXAMPLE,
                "profile_information": PROFILE_INFORMATION_EXAMPLE,
                "recruitment_preferences": RECRUITMENT_PREFERENCES_EXAMPLE,
                "games_information": GAMES_INFORMATION_EXAMPLE
            },
            response_only=True,
            status_codes=[status.HTTP_201_CREATED]
        )
    ]
)

eoi_submission_detail_schema = extend_schema(
    summary="Retrieve, update or delete an EOI submission",
    description="""
    **GET**: Retrieve submission details
    - Users can access their own submissions
    - Staff can access any submission
    - Returns complete submission data including all sections
    
    **PUT/PATCH**: Update submission (staff only)
    - Allows updating status and reviewer notes
    - Validates status transitions
    - Logs all changes for audit trail
    
    **DELETE**: Delete submission (staff only)
    - Permanently removes submission and all related data
    - Logs deletion for audit trail
    """,
    examples=[
        OpenApiExample(
            name="EOI Submission Detail Response",
            value={
                **EOI_SUBMISSION_EXAMPLE,
                "profile_information": PROFILE_INFORMATION_EXAMPLE,
                "recruitment_preferences": RECRUITMENT_PREFERENCES_EXAMPLE,
                "games_information": GAMES_INFORMATION_EXAMPLE
            },
            response_only=True,
            status_codes=[status.HTTP_200_OK]
        ),
        OpenApiExample(
            name="Update EOI Submission Request",
            value={
                "status": "APPROVED",
                "reviewer_notes": "Application approved after review. Volunteer has excellent experience."
            },
            request_only=True
        )
    ]
)

corporate_group_list_create_schema = extend_schema(
    summary="List or create corporate volunteer groups",
    description="""
    **GET**: List active corporate groups (public)
    - Returns only active groups for public access
    - Staff can see all groups regardless of status
    - Supports filtering and searching
    
    **POST**: Create new corporate group (public)
    - Allows organizations to register as corporate volunteers
    - Sets initial status to PENDING for staff review
    - Sends notification to corporate volunteer team
    """,
    parameters=[
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by group status (staff only)',
            enum=['PENDING', 'ACTIVE', 'INACTIVE']
        ),
        OpenApiParameter(
            name='industry_sector',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by industry sector'
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search by group name, description, or contact name'
        ),
    ],
    examples=[
        OpenApiExample(
            name="Corporate Group List Response",
            value={
                "count": 25,
                "next": None,
                "previous": None,
                "results": [CORPORATE_GROUP_EXAMPLE]
            },
            response_only=True,
            status_codes=[status.HTTP_200_OK]
        ),
        OpenApiExample(
            name="Create Corporate Group Request",
            value={
                "name": "Tech Solutions Pty Ltd",
                "description": "Leading technology company committed to community engagement",
                "website": "https://techsolutions.com.au",
                "primary_contact_name": "Sarah Johnson",
                "primary_contact_email": "sarah.johnson@techsolutions.com.au",
                "primary_contact_phone": "+61398765432",
                "address_line_1": "456 Collins Street",
                "city": "Melbourne",
                "state_province": "VIC",
                "postal_code": "3000",
                "country": "Australia",
                "expected_volunteer_count": 25,
                "industry_sector": "TECHNOLOGY"
            },
            request_only=True
        )
    ]
)

eoi_stats_schema = extend_schema(
    summary="Get EOI statistics",
    description="""
    Returns comprehensive statistics about EOI submissions including:
    - Total submission count
    - Breakdown by status
    - Breakdown by volunteer type
    - Completion rate percentage
    - Recent submissions (last 7 days)
    - Pending review count
    - Approved count
    
    **Staff access only**
    """,
    examples=[
        OpenApiExample(
            name="EOI Statistics Response",
            value={
                "total_submissions": 1250,
                "by_status": {
                    "SUBMITTED": 450,
                    "UNDER_REVIEW": 200,
                    "APPROVED": 400,
                    "REJECTED": 50,
                    "CONFIRMED": 150
                },
                "by_volunteer_type": {
                    "NEW": 800,
                    "RETURNING": 350,
                    "CORPORATE": 100
                },
                "completion_rate": 85.6,
                "recent_submissions": 75,
                "pending_review": 200,
                "approved_count": 400
            },
            response_only=True,
            status_codes=[status.HTTP_200_OK]
        )
    ]
)

bulk_update_status_schema = extend_schema(
    summary="Bulk update EOI submission statuses",
    description="""
    Allows staff to update multiple EOI submission statuses at once.
    Useful for batch processing of applications.
    
    **Staff access only**
    
    Validates status transitions and logs all changes for audit trail.
    """,
    examples=[
        OpenApiExample(
            name="Bulk Update Request",
            value={
                "submission_ids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "456e7890-e89b-12d3-a456-426614174001",
                    "789e0123-e89b-12d3-a456-426614174002"
                ],
                "status": "APPROVED",
                "reviewer_notes": "Batch approval after team review meeting"
            },
            request_only=True
        ),
        OpenApiExample(
            name="Bulk Update Response",
            value={
                "message": "Successfully updated 3 submissions",
                "updated_count": 3
            },
            response_only=True,
            status_codes=[status.HTTP_200_OK]
        )
    ]
)

submission_status_check_schema = extend_schema(
    summary="Check EOI submission status",
    description="""
    Public endpoint to check the status of an EOI submission.
    Returns basic status information without sensitive data.
    
    **Public access** - no authentication required
    """,
    examples=[
        OpenApiExample(
            name="Status Check Response",
            value={
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "UNDER_REVIEW",
                "status_display": "Under Review",
                "completion_percentage": 100,
                "submitted_at": "2024-06-13T10:30:00Z",
                "confirmation_email_sent": True
            },
            response_only=True,
            status_codes=[status.HTTP_200_OK]
        )
    ]
)

resend_confirmation_email_schema = extend_schema(
    summary="Resend confirmation email",
    description="""
    Resends the confirmation email for an EOI submission.
    
    **Access control**:
    - Authenticated users can resend emails for their own submissions
    - Anonymous users can resend emails for submissions created in their session
    - Staff can resend emails for any submission
    """,
    examples=[
        OpenApiExample(
            name="Resend Email Response",
            value={
                "message": "Confirmation email sent successfully",
                "email": "volunteer@example.com"
            },
            response_only=True,
            status_codes=[status.HTTP_200_OK]
        )
    ]
)

# API Endpoint Documentation
API_ENDPOINTS = {
    "submissions": {
        "list_create": {
            "url": "/volunteers/api/eoi/submissions/",
            "methods": ["GET", "POST"],
            "description": "List submissions (staff) or create new submission (public)",
            "permissions": {
                "GET": "Staff only",
                "POST": "Public"
            }
        },
        "detail": {
            "url": "/volunteers/api/eoi/submissions/{id}/",
            "methods": ["GET", "PUT", "PATCH", "DELETE"],
            "description": "Retrieve, update, or delete submission",
            "permissions": {
                "GET": "Owner or staff",
                "PUT/PATCH/DELETE": "Staff only"
            }
        },
        "status_check": {
            "url": "/volunteers/api/eoi/submissions/{id}/status/",
            "methods": ["GET"],
            "description": "Check submission status (public)",
            "permissions": "Public"
        },
        "resend_email": {
            "url": "/volunteers/api/eoi/submissions/{id}/resend-email/",
            "methods": ["POST"],
            "description": "Resend confirmation email",
            "permissions": "Owner or staff"
        }
    },
    "corporate_groups": {
        "list_create": {
            "url": "/volunteers/api/eoi/corporate-groups/",
            "methods": ["GET", "POST"],
            "description": "List active groups or create new group",
            "permissions": "Public"
        },
        "detail": {
            "url": "/volunteers/api/eoi/corporate-groups/{id}/",
            "methods": ["GET", "PUT", "PATCH", "DELETE"],
            "description": "Retrieve, update, or delete corporate group",
            "permissions": {
                "GET": "Public (active groups only)",
                "PUT/PATCH/DELETE": "Staff only"
            }
        }
    },
    "stats": {
        "url": "/volunteers/api/eoi/stats/",
        "methods": ["GET"],
        "description": "Get EOI statistics",
        "permissions": "Staff only"
    },
    "bulk_update": {
        "url": "/volunteers/api/eoi/bulk-update-status/",
        "methods": ["POST"],
        "description": "Bulk update submission statuses",
        "permissions": "Staff only"
    }
} 