"""
Serializers for notification API
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .notification_models import (
    NotificationTemplate, Notification, NotificationPreference,
    NotificationChannel, NotificationLog
)

User = get_user_model()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates"""
    
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    default_priority_display = serializers.CharField(source='get_default_priority_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'notification_type', 'notification_type_display', 'name', 'description',
            'title_template', 'message_template', 'default_priority', 'default_priority_display',
            'is_email_enabled', 'is_push_enabled', 'is_in_app_enabled',
            'target_user_types', 'target_roles', 'delay_minutes', 'expires_after_hours',
            'is_active', 'created_at', 'updated_at', 'created_by_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer for notification list view"""
    
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    is_read = serializers.SerializerMethodField()
    time_since_created = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'recipient_username', 'sender_username',
            'status', 'status_display', 'priority', 'priority_display',
            'template_name', 'is_read', 'created_at', 'time_since_created',
            'scheduled_at', 'expires_at'
        ]
    
    def get_is_read(self, obj):
        return obj.status == 'READ'
    
    def get_time_since_created(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return obj.created_at.strftime('%Y-%m-%d')


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Serializer for notification detail view"""
    
    recipient = serializers.StringRelatedField()
    sender = serializers.StringRelatedField()
    template = NotificationTemplateSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    related_object_data = serializers.SerializerMethodField()
    delivery_logs = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'template', 'title', 'message', 'recipient', 'sender',
            'priority', 'priority_display', 'channels', 'status', 'status_display',
            'scheduled_at', 'sent_at', 'delivered_at', 'read_at', 'expires_at',
            'context_data', 'delivery_attempts', 'error_message',
            'created_at', 'updated_at', 'related_object_data', 'delivery_logs'
        ]
        read_only_fields = [
            'id', 'sent_at', 'delivered_at', 'read_at', 'delivery_attempts',
            'error_message', 'created_at', 'updated_at'
        ]
    
    def get_related_object_data(self, obj):
        if obj.related_object:
            try:
                return {
                    'type': obj.content_type.model,
                    'id': obj.object_id,
                    'name': str(obj.related_object),
                    'url': getattr(obj.related_object, 'get_absolute_url', lambda: None)()
                }
            except Exception:
                pass
        return None
    
    def get_delivery_logs(self, obj):
        logs = obj.logs.all()[:10]  # Latest 10 logs
        return NotificationLogSerializer(logs, many=True).data


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications"""
    
    recipient_id = serializers.IntegerField(write_only=True)
    sender_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Notification
        fields = [
            'recipient_id', 'sender_id', 'title', 'message',
            'priority', 'channels', 'scheduled_at', 'expires_at', 'context_data'
        ]
    
    def validate_recipient_id(self, value):
        try:
            User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found")
    
    def create(self, validated_data):
        from .notification_service import notification_service
        
        recipient_id = validated_data.pop('recipient_id')
        sender_id = validated_data.pop('sender_id', None)
        
        recipient = User.objects.get(id=recipient_id)
        sender = User.objects.get(id=sender_id) if sender_id else None
        
        notification = notification_service.create_notification(
            recipient=recipient,
            sender=sender,
            **validated_data
        )
        
        return notification


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'user_username', 'is_enabled', 'email_enabled', 'push_enabled',
            'in_app_enabled', 'sms_enabled', 'volunteer_notifications',
            'event_notifications', 'task_notifications', 'admin_notifications',
            'system_notifications', 'training_notifications', 'quiet_hours_start',
            'quiet_hours_end', 'timezone', 'digest_frequency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user_username', 'created_at', 'updated_at']


class NotificationChannelSerializer(serializers.ModelSerializer):
    """Serializer for notification channels"""
    
    channel_type_display = serializers.CharField(source='get_channel_type_display', read_only=True)
    
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'channel_type', 'channel_type_display', 'is_active',
            'configuration', 'rate_limit_per_minute', 'rate_limit_per_hour',
            'max_retries', 'retry_delay_seconds', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification logs"""
    
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'level', 'level_display', 'message', 'channel_name',
            'channel_type', 'delivery_status', 'response_data',
            'timestamp', 'processing_time_ms'
        ]


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    pending_notifications = serializers.IntegerField()
    sent_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()
    notifications_today = serializers.IntegerField()
    notifications_this_week = serializers.IntegerField()


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notification operations"""
    
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=1000
    )
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    notification_type = serializers.CharField(default='bulk_operation')
    priority = serializers.ChoiceField(
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('URGENT', 'Urgent'),
            ('CRITICAL', 'Critical'),
        ],
        default='MEDIUM'
    )
    
    def validate_recipient_ids(self, value):
        # Check if all recipients exist
        existing_ids = set(User.objects.filter(id__in=value).values_list('id', flat=True))
        invalid_ids = set(value) - existing_ids
        
        if invalid_ids:
            raise serializers.ValidationError(f"Invalid recipient IDs: {list(invalid_ids)}")
        
        return value


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    mark_all = serializers.BooleanField(default=False)
    
    def validate(self, data):
        if not data.get('mark_all') and not data.get('notification_ids'):
            raise serializers.ValidationError(
                "Either 'mark_all' must be True or 'notification_ids' must be provided"
            )
        return data 