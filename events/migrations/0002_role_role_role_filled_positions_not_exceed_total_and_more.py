# Generated by Django 5.0.14 on 2025-06-13 09:10

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Role name (e.g., "Swimming Official", "Registration Volunteer")', max_length=200)),
                ('slug', models.SlugField(help_text='URL-friendly role identifier', max_length=200)),
                ('short_name', models.CharField(blank=True, help_text='Short name for display (e.g., "Swim Official")', max_length=50)),
                ('role_type', models.CharField(choices=[('SPORT_OFFICIAL', 'Sport Official'), ('REFEREE', 'Referee'), ('JUDGE', 'Judge'), ('TIMEKEEPER', 'Timekeeper'), ('SCORER', 'Scorer'), ('TECHNICAL_DELEGATE', 'Technical Delegate'), ('VENUE_MANAGER', 'Venue Manager'), ('VENUE_COORDINATOR', 'Venue Coordinator'), ('VENUE_ASSISTANT', 'Venue Assistant'), ('SETUP_CREW', 'Setup Crew'), ('BREAKDOWN_CREW', 'Breakdown Crew'), ('ATHLETE_ESCORT', 'Athlete Escort'), ('ATHLETE_LIAISON', 'Athlete Liaison'), ('WARM_UP_ASSISTANT', 'Warm-up Assistant'), ('EQUIPMENT_MANAGER', 'Equipment Manager'), ('MEDICAL_OFFICER', 'Medical Officer'), ('FIRST_AID', 'First Aid'), ('SAFETY_OFFICER', 'Safety Officer'), ('SECURITY', 'Security'), ('DRIVER', 'Driver'), ('TRANSPORT_COORDINATOR', 'Transport Coordinator'), ('LOGISTICS_ASSISTANT', 'Logistics Assistant'), ('PHOTOGRAPHER', 'Photographer'), ('VIDEOGRAPHER', 'Videographer'), ('MEDIA_LIAISON', 'Media Liaison'), ('SOCIAL_MEDIA', 'Social Media'), ('COMMENTATOR', 'Commentator'), ('IT_SUPPORT', 'IT Support'), ('RESULTS_SYSTEM', 'Results System Operator'), ('TIMING_SYSTEM', 'Timing System Operator'), ('REGISTRATION', 'Registration'), ('INFORMATION_DESK', 'Information Desk'), ('HOSPITALITY', 'Hospitality'), ('PROTOCOL', 'Protocol'), ('GENERAL_VOLUNTEER', 'General Volunteer'), ('TEAM_LEADER', 'Team Leader'), ('SUPERVISOR', 'Supervisor'), ('COORDINATOR', 'Coordinator'), ('OTHER', 'Other')], default='GENERAL_VOLUNTEER', help_text='Type of role', max_length=30)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ACTIVE', 'Active'), ('FULL', 'Full - No More Volunteers Needed'), ('SUSPENDED', 'Suspended'), ('CANCELLED', 'Cancelled'), ('COMPLETED', 'Completed')], default='DRAFT', help_text='Current role status', max_length=20)),
                ('description', models.TextField(help_text='Detailed role description and responsibilities')),
                ('summary', models.CharField(blank=True, help_text='Brief role summary for listings', max_length=500)),
                ('minimum_age', models.PositiveIntegerField(default=15, help_text='Minimum age requirement', validators=[django.core.validators.MinValueValidator(13), django.core.validators.MaxValueValidator(80)])),
                ('maximum_age', models.PositiveIntegerField(blank=True, help_text='Maximum age requirement (optional)', null=True, validators=[django.core.validators.MinValueValidator(16), django.core.validators.MaxValueValidator(100)])),
                ('skill_level_required', models.CharField(choices=[('BEGINNER', 'Beginner'), ('INTERMEDIATE', 'Intermediate'), ('ADVANCED', 'Advanced'), ('EXPERT', 'Expert'), ('ANY', 'Any Level')], default='ANY', help_text='Required skill level', max_length=20)),
                ('physical_requirements', models.JSONField(blank=True, default=list, help_text='Physical requirements (e.g., standing, lifting, walking)')),
                ('language_requirements', models.JSONField(blank=True, default=list, help_text='Language requirements')),
                ('required_credentials', models.JSONField(blank=True, default=list, help_text='Required credentials/certifications')),
                ('preferred_credentials', models.JSONField(blank=True, default=list, help_text='Preferred credentials/certifications')),
                ('justgo_credentials_required', models.JSONField(blank=True, default=list, help_text='JustGo credentials required for this role')),
                ('requires_garda_vetting', models.BooleanField(default=False, help_text='Requires Garda vetting (background check)')),
                ('requires_child_protection', models.BooleanField(default=False, help_text='Requires child protection training')),
                ('requires_security_clearance', models.BooleanField(default=False, help_text='Requires security clearance')),
                ('total_positions', models.PositiveIntegerField(default=1, help_text='Total number of positions available', validators=[django.core.validators.MinValueValidator(1)])),
                ('filled_positions', models.PositiveIntegerField(default=0, help_text='Number of positions currently filled', validators=[django.core.validators.MinValueValidator(0)])),
                ('minimum_volunteers', models.PositiveIntegerField(default=1, help_text='Minimum number of volunteers needed', validators=[django.core.validators.MinValueValidator(1)])),
                ('commitment_level', models.CharField(choices=[('SINGLE_SESSION', 'Single Session'), ('DAILY', 'Daily'), ('MULTI_DAY', 'Multi-Day'), ('FULL_EVENT', 'Full Event'), ('FLEXIBLE', 'Flexible')], default='FLEXIBLE', help_text='Expected time commitment level', max_length=20)),
                ('estimated_hours_per_day', models.DecimalField(blank=True, decimal_places=1, help_text='Estimated hours per day', max_digits=4, null=True, validators=[django.core.validators.MinValueValidator(0.5), django.core.validators.MaxValueValidator(24.0)])),
                ('total_estimated_hours', models.DecimalField(blank=True, decimal_places=1, help_text='Total estimated hours for the role', max_digits=6, null=True, validators=[django.core.validators.MinValueValidator(0.5)])),
                ('schedule_requirements', models.JSONField(blank=True, default=dict, help_text='Specific scheduling requirements and constraints')),
                ('availability_windows', models.JSONField(blank=True, default=list, help_text='Available time windows for this role')),
                ('training_required', models.BooleanField(default=False, help_text='Whether training is required for this role')),
                ('training_duration_hours', models.DecimalField(blank=True, decimal_places=1, help_text='Training duration in hours', max_digits=4, null=True, validators=[django.core.validators.MinValueValidator(0.5), django.core.validators.MaxValueValidator(40.0)])),
                ('training_materials', models.JSONField(blank=True, default=list, help_text='Training materials and resources')),
                ('uniform_required', models.BooleanField(default=False, help_text='Whether uniform is required')),
                ('uniform_details', models.JSONField(blank=True, default=dict, help_text='Uniform requirements and details')),
                ('equipment_provided', models.JSONField(blank=True, default=list, help_text='Equipment provided to volunteers')),
                ('equipment_required', models.JSONField(blank=True, default=list, help_text='Equipment volunteers must bring')),
                ('benefits', models.JSONField(blank=True, default=list, help_text='Benefits provided to volunteers in this role')),
                ('meal_provided', models.BooleanField(default=False, help_text='Whether meals are provided')),
                ('transport_provided', models.BooleanField(default=False, help_text='Whether transport is provided')),
                ('accommodation_provided', models.BooleanField(default=False, help_text='Whether accommodation is provided')),
                ('role_configuration', models.JSONField(blank=True, default=dict, help_text='Role-specific configuration settings')),
                ('custom_fields', models.JSONField(blank=True, default=dict, help_text='Custom fields for role-specific data')),
                ('contact_person', models.CharField(blank=True, help_text='Contact person for this role', max_length=200)),
                ('contact_email', models.EmailField(blank=True, help_text='Contact email for role inquiries', max_length=254)),
                ('contact_phone', models.CharField(blank=True, help_text='Contact phone for role inquiries', max_length=20)),
                ('priority_level', models.PositiveIntegerField(default=5, help_text='Priority level (1=highest, 10=lowest)', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)])),
                ('is_featured', models.BooleanField(default=False, help_text='Whether this role should be featured')),
                ('is_urgent', models.BooleanField(default=False, help_text='Whether this role needs urgent filling')),
                ('is_public', models.BooleanField(default=True, help_text='Whether this role is publicly visible')),
                ('application_deadline', models.DateTimeField(blank=True, help_text='Application deadline for this role', null=True)),
                ('selection_criteria', models.JSONField(blank=True, default=list, help_text='Selection criteria for this role')),
                ('application_process', models.TextField(blank=True, help_text='Special application process instructions')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status_changed_at', models.DateTimeField(blank=True, help_text='When status was last changed', null=True)),
                ('notes', models.TextField(blank=True, help_text='Internal notes about this role')),
                ('external_references', models.JSONField(blank=True, default=dict, help_text='External system references')),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this role', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_roles', to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(help_text='Event this role belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='events.event')),
                ('role_coordinators', models.ManyToManyField(blank=True, help_text='Users who coordinate this role', related_name='coordinated_roles', to=settings.AUTH_USER_MODEL)),
                ('role_supervisor', models.ForeignKey(blank=True, help_text='Role supervisor/manager', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supervised_roles', to=settings.AUTH_USER_MODEL)),
                ('status_changed_by', models.ForeignKey(blank=True, help_text='User who last changed the status', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='status_changed_roles', to=settings.AUTH_USER_MODEL)),
                ('venue', models.ForeignKey(blank=True, help_text='Venue this role is associated with (optional)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='events.venue')),
            ],
            options={
                'verbose_name': 'role',
                'verbose_name_plural': 'roles',
                'ordering': ['event', 'venue', 'priority_level', 'name'],
                'indexes': [models.Index(fields=['event'], name='events_role_event_i_792eb0_idx'), models.Index(fields=['venue'], name='events_role_venue_i_e81bb7_idx'), models.Index(fields=['role_type'], name='events_role_role_ty_505b62_idx'), models.Index(fields=['status'], name='events_role_status_b6cdee_idx'), models.Index(fields=['priority_level'], name='events_role_priorit_b85a3a_idx'), models.Index(fields=['is_featured', 'is_urgent'], name='events_role_is_feat_cec12f_idx'), models.Index(fields=['application_deadline'], name='events_role_applica_fe9ed5_idx'), models.Index(fields=['created_at'], name='events_role_created_d05ff1_idx')],
            },
        ),
        migrations.AddConstraint(
            model_name='role',
            constraint=models.CheckConstraint(check=models.Q(('filled_positions__lte', models.F('total_positions'))), name='role_filled_positions_not_exceed_total'),
        ),
        migrations.AddConstraint(
            model_name='role',
            constraint=models.CheckConstraint(check=models.Q(('minimum_volunteers__lte', models.F('total_positions'))), name='role_minimum_not_exceed_total'),
        ),
        migrations.AddConstraint(
            model_name='role',
            constraint=models.CheckConstraint(check=models.Q(('maximum_age__gt', models.F('minimum_age'))), name='role_maximum_age_greater_than_minimum'),
        ),
        migrations.AlterUniqueTogether(
            name='role',
            unique_together={('event', 'slug')},
        ),
    ]
