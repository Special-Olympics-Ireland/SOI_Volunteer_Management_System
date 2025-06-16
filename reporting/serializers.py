from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from .models import Report, ReportTemplate, ReportSchedule, ReportMetrics, ReportShare
from volunteers.models import VolunteerProfile
from events.models import Event, Assignment
from tasks.models import TaskCompletion

User = get_user_model()


class ReportListSerializer(serializers.ModelSerializer):
    """Serializer for report list view with essential information"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    download_url = serializers.CharField(source='get_download_url', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    # Computed fields
    generation_duration = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'report_type_display',
            'status', 'status_display', 'export_format', 'export_format_display',
            'progress_percentage', 'total_records', 'file_size', 'file_size_display',
            'created_by', 'created_by_name', 'created_at', 'completed_at',
            'expires_at', 'download_url', 'is_expired', 'generation_duration',
            'days_until_expiry'
        ]
    
    def get_generation_duration(self, obj):
        """Get generation duration in seconds"""
        if obj.generation_time:
            return obj.generation_time.total_seconds()
        return None
    
    def get_days_until_expiry(self, obj):
        """Get days until expiry"""
        if obj.expires_at:
            delta = obj.expires_at - timezone.now()
            return max(0, delta.days)
        return None


class ReportDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed report view with all information"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    download_url = serializers.CharField(source='get_download_url', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    # Related data
    metrics = serializers.SerializerMethodField()
    shares = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'report_type_display',
            'parameters', 'export_format', 'export_format_display',
            'status', 'status_display', 'progress_percentage', 'total_records',
            'file_path', 'file_size', 'file_size_display', 'generation_time',
            'error_message', 'created_by', 'created_by_name', 'created_at',
            'started_at', 'completed_at', 'expires_at', 'download_url',
            'is_expired', 'metrics', 'shares'
        ]
    
    def get_metrics(self, obj):
        """Get report metrics if available"""
        try:
            metrics = obj.metrics
            return {
                'query_time': metrics.query_time.total_seconds() if metrics.query_time else None,
                'processing_time': metrics.processing_time.total_seconds() if metrics.processing_time else None,
                'export_time': metrics.export_time.total_seconds() if metrics.export_time else None,
                'memory_usage_mb': metrics.memory_usage_mb,
                'cpu_usage_percent': metrics.cpu_usage_percent,
                'rows_processed': metrics.rows_processed,
                'columns_included': metrics.columns_included,
                'data_completeness_percent': metrics.data_completeness_percent,
                'error_count': metrics.error_count,
                'warning_count': metrics.warning_count,
                'download_count': metrics.download_count,
                'last_downloaded': metrics.last_downloaded
            }
        except ReportMetrics.DoesNotExist:
            return None
    
    def get_shares(self, obj):
        """Get active report shares"""
        shares = obj.shares.filter(status='ACTIVE')
        return [{
            'id': str(share.id),
            'share_type': share.share_type,
            'expires_at': share.expires_at,
            'access_count': share.access_count,
            'download_count': share.download_count,
            'can_download': share.can_download,
            'can_view_metrics': share.can_view_metrics
        } for share in shares]


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new reports"""
    
    class Meta:
        model = Report
        fields = [
            'name', 'description', 'report_type', 'parameters', 'export_format'
        ]
    
    def validate_parameters(self, value):
        """Validate report parameters based on report type"""
        report_type = self.initial_data.get('report_type')
        
        # Define required parameters for each report type
        required_params = {
            'VOLUNTEER_SUMMARY': [],
            'VOLUNTEER_DETAILED': [],
            'EVENT_SUMMARY': [],
            'EVENT_DETAILED': ['event_id'],
            'VENUE_UTILIZATION': [],
            'ROLE_ASSIGNMENT': [],
            'TRAINING_STATUS': [],
            'BACKGROUND_CHECK': [],
            'JUSTGO_SYNC': [],
            'EOI_ANALYTICS': [],
            'PERFORMANCE_METRICS': [],
            'ATTENDANCE_TRACKING': ['event_id'],
            'CUSTOM': ['query', 'columns']
        }
        
        if report_type in required_params:
            for param in required_params[report_type]:
                if param not in value:
                    raise serializers.ValidationError(
                        f"Parameter '{param}' is required for {report_type} reports"
                    )
        
        return value
    
    def create(self, validated_data):
        """Create report with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for report templates"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    default_export_format_display = serializers.CharField(source='get_default_export_format_display', read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type', 'report_type_display',
            'default_parameters', 'default_export_format', 'default_export_format_display',
            'is_active', 'is_public', 'created_by', 'created_by_name',
            'usage_count', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = ['usage_count', 'last_used', 'created_by']
    
    def create(self, validated_data):
        """Create template with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for report schedules"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    report_template_name = serializers.CharField(source='report_template.name', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'name', 'description', 'report_template', 'report_template_name',
            'frequency', 'frequency_display', 'start_date', 'end_date',
            'run_time', 'timezone', 'status', 'status_display',
            'email_recipients', 'created_by', 'created_by_name',
            'last_run', 'next_run', 'run_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_run', 'next_run', 'run_count', 'created_by']
    
    def create(self, validated_data):
        """Create schedule with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        schedule = super().create(validated_data)
        schedule.calculate_next_run()
        return schedule


class ReportShareSerializer(serializers.ModelSerializer):
    """Serializer for report shares"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    share_type_display = serializers.CharField(source='get_share_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    share_url = serializers.CharField(source='get_share_url', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ReportShare
        fields = [
            'id', 'report', 'share_type', 'share_type_display',
            'share_token', 'password_protected', 'can_download',
            'can_view_metrics', 'expires_at', 'max_downloads',
            'status', 'status_display', 'access_count', 'download_count',
            'last_accessed', 'created_by', 'created_by_name',
            'share_url', 'is_valid', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'share_token', 'access_count', 'download_count',
            'last_accessed', 'created_by'
        ]
    
    def create(self, validated_data):
        """Create share with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AnalyticsSerializer(serializers.Serializer):
    """Serializer for analytics data"""
    
    metric_name = serializers.CharField()
    metric_value = serializers.FloatField()
    metric_type = serializers.CharField()
    period = serializers.CharField()
    timestamp = serializers.DateTimeField()
    metadata = serializers.DictField(required=False)


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    
    volunteers = serializers.DictField()
    events = serializers.DictField()
    assignments = serializers.DictField()
    tasks = serializers.DictField()
    reports = serializers.DictField()
    system = serializers.DictField()


class ReportTypeInfoSerializer(serializers.Serializer):
    """Serializer for report type information"""
    
    report_type = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    required_parameters = serializers.ListField(child=serializers.CharField())
    optional_parameters = serializers.ListField(child=serializers.CharField())
    supported_formats = serializers.ListField(child=serializers.CharField())
    estimated_generation_time = serializers.CharField()


class BulkReportOperationSerializer(serializers.Serializer):
    """Serializer for bulk report operations"""
    
    BULK_ACTIONS = [
        ('delete', 'Delete'),
        ('regenerate', 'Regenerate'),
        ('share', 'Share'),
        ('export', 'Export'),
        ('archive', 'Archive')
    ]
    
    report_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of report IDs to perform action on"
    )
    action = serializers.ChoiceField(choices=BULK_ACTIONS)
    parameters = serializers.DictField(required=False, default=dict)
    
    def validate(self, data):
        """Validate bulk operation data"""
        if not data.get('report_ids'):
            raise serializers.ValidationError({
                'report_ids': 'At least one report ID is required'
            })
        
        # Validate action-specific requirements
        action = data['action']
        parameters = data.get('parameters', {})
        
        if action == 'share' and not parameters.get('share_type'):
            raise serializers.ValidationError({
                'parameters': 'share_type is required for share action'
            })
        
        if action == 'export' and not parameters.get('format'):
            raise serializers.ValidationError({
                'parameters': 'format is required for export action'
            })
        
        return data


class ReportGenerationRequestSerializer(serializers.Serializer):
    """Serializer for report generation requests"""
    
    report_type = serializers.ChoiceField(choices=Report.ReportType.choices)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    parameters = serializers.DictField(default=dict)
    export_format = serializers.ChoiceField(
        choices=Report.ExportFormat.choices,
        default=Report.ExportFormat.CSV
    )
    template_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validate report generation request"""
        # If template is provided, merge its parameters
        if data.get('template_id'):
            try:
                template = ReportTemplate.objects.get(id=data['template_id'])
                # Merge template parameters with provided parameters
                merged_params = template.default_parameters.copy()
                merged_params.update(data.get('parameters', {}))
                data['parameters'] = merged_params
                
                # Use template defaults if not provided
                if not data.get('export_format'):
                    data['export_format'] = template.default_export_format
                
            except ReportTemplate.DoesNotExist:
                raise serializers.ValidationError({
                    'template_id': 'Template not found'
                })
        
        return data


class ReportProgressSerializer(serializers.Serializer):
    """Serializer for report generation progress"""
    
    report_id = serializers.UUIDField()
    status = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    current_step = serializers.CharField()
    estimated_completion = serializers.DateTimeField(required=False, allow_null=True)
    error_message = serializers.CharField(required=False, allow_blank=True)


class ReportExportSerializer(serializers.Serializer):
    """Serializer for report export requests"""
    
    format = serializers.ChoiceField(choices=Report.ExportFormat.choices)
    include_metadata = serializers.BooleanField(default=False)
    compress = serializers.BooleanField(default=False)
    password_protect = serializers.BooleanField(default=False)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    def validate(self, data):
        """Validate export request"""
        if data.get('password_protect') and not data.get('password'):
            raise serializers.ValidationError({
                'password': 'Password is required when password protection is enabled'
            })
        
        return data 