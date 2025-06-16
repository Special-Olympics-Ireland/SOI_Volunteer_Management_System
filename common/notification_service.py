"""
Notification service for managing real-time notifications
"""

import logging
import json
from datetime import timedelta
from typing import List, Dict, Any, Optional, Union
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import redis

from .notification_models import (
    NotificationTemplate, Notification, NotificationPreference,
    NotificationChannel, NotificationLog
)

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        try:
            self.redis_client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
        except:
            self.redis_client = None
    
    def create_notification(
        self,
        recipient: User,
        title: str,
        message: str,
        notification_type: str = 'custom',
        priority: str = 'MEDIUM',
        sender: Optional[User] = None,
        related_object: Any = None,
        channels: Optional[List[str]] = None,
        context_data: Optional[Dict] = None,
        template: Optional[NotificationTemplate] = None,
        scheduled_at: Optional[timezone.datetime] = None,
        expires_at: Optional[timezone.datetime] = None
    ) -> Notification:
        """Create a new notification"""
        
        try:
            with transaction.atomic():
                # Get or create notification preferences
                preferences, _ = NotificationPreference.objects.get_or_create(
                    user=recipient,
                    defaults={'is_enabled': True}
                )
                
                # Check if notifications are enabled for this user
                if not preferences.is_enabled:
                    logger.info(f"Notifications disabled for user {recipient.username}")
                    return None
                
                # Set default channels if not provided
                if channels is None:
                    channels = ['IN_APP', 'WEBSOCKET']
                    if preferences.email_enabled:
                        channels.append('EMAIL')
                    if preferences.push_enabled:
                        channels.append('PUSH')
                
                # Filter channels based on user preferences
                allowed_channels = []
                for channel in channels:
                    if preferences.is_notification_allowed(notification_type, channel):
                        allowed_channels.append(channel)
                
                if not allowed_channels:
                    logger.info(f"No allowed channels for user {recipient.username}")
                    return None
                
                # Check quiet hours
                if preferences.is_quiet_hours() and priority not in ['URGENT', 'CRITICAL']:
                    # Schedule for after quiet hours
                    scheduled_at = self._calculate_after_quiet_hours(preferences)
                
                # Create notification
                notification = Notification.objects.create(
                    template=template,
                    title=title,
                    message=message,
                    recipient=recipient,
                    sender=sender,
                    priority=priority,
                    channels=allowed_channels,
                    scheduled_at=scheduled_at or timezone.now(),
                    expires_at=expires_at,
                    context_data=context_data or {}
                )
                
                # Set related object if provided
                if related_object:
                    notification.content_type = ContentType.objects.get_for_model(related_object)
                    notification.object_id = str(related_object.pk)
                    notification.save(update_fields=['content_type', 'object_id'])
                
                # Send immediately if not scheduled for later
                if notification.scheduled_at <= timezone.now():
                    self.send_notification(notification)
                
                logger.info(f"Created notification {notification.id} for {recipient.username}")
                return notification
                
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            return None
    
    def create_from_template(
        self,
        template_type: str,
        recipient: User,
        context: Dict[str, Any],
        sender: Optional[User] = None,
        related_object: Any = None,
        priority_override: Optional[str] = None
    ) -> Optional[Notification]:
        """Create notification from template"""
        
        try:
            template = NotificationTemplate.objects.get(
                notification_type=template_type,
                is_active=True
            )
            
            # Render template
            title = template.render_title(context)
            message = template.render_message(context)
            
            # Determine channels
            channels = []
            if template.is_in_app_enabled:
                channels.extend(['IN_APP', 'WEBSOCKET'])
            if template.is_email_enabled:
                channels.append('EMAIL')
            if template.is_push_enabled:
                channels.append('PUSH')
            
            # Calculate expiry
            expires_at = None
            if template.expires_after_hours > 0:
                expires_at = timezone.now() + timedelta(hours=template.expires_after_hours)
            
            # Calculate scheduled time
            scheduled_at = None
            if template.delay_minutes > 0:
                scheduled_at = timezone.now() + timedelta(minutes=template.delay_minutes)
            
            return self.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=template_type,
                priority=priority_override or template.default_priority,
                sender=sender,
                related_object=related_object,
                channels=channels,
                context_data=context,
                template=template,
                scheduled_at=scheduled_at,
                expires_at=expires_at
            )
            
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_type}")
            return None
        except Exception as e:
            logger.error(f"Failed to create notification from template: {str(e)}")
            return None
    
    def send_notification(self, notification: Notification) -> bool:
        """Send notification through configured channels"""
        
        try:
            success = False
            
            for channel in notification.channels:
                try:
                    if channel == 'WEBSOCKET':
                        success |= self._send_websocket(notification)
                    elif channel == 'IN_APP':
                        success |= self._send_in_app(notification)
                    elif channel == 'EMAIL':
                        success |= self._send_email(notification)
                    elif channel == 'PUSH':
                        success |= self._send_push(notification)
                    
                    self._log_delivery(notification, channel, 'SUCCESS', 'Sent successfully')
                    
                except Exception as e:
                    self._log_delivery(notification, channel, 'FAILED', str(e))
                    logger.error(f"Failed to send via {channel}: {str(e)}")
            
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed("All channels failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {str(e)}")
            notification.mark_as_failed(str(e))
            return False
    
    def _send_websocket(self, notification: Notification) -> bool:
        """Send notification via WebSocket"""
        try:
            if not self.channel_layer:
                return False
            
            # Send to user's personal channel
            user_channel = f"user_{notification.recipient.id}"
            
            message_data = {
                'type': 'notification_message',
                'notification': {
                    'id': str(notification.id),
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'created_at': notification.created_at.isoformat(),
                    'related_object': self._get_related_object_data(notification),
                    'sender': notification.sender.username if notification.sender else None,
                }
            }
            
            async_to_sync(self.channel_layer.group_send)(user_channel, message_data)
            
            # Also send to user type groups
            user_type_channel = f"user_type_{notification.recipient.user_type}"
            async_to_sync(self.channel_layer.group_send)(user_type_channel, message_data)
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket send failed: {str(e)}")
            return False
    
    def _send_in_app(self, notification: Notification) -> bool:
        """Mark notification as in-app (already stored in database)"""
        try:
            # Update cache for real-time unread count
            cache_key = f"unread_notifications_{notification.recipient.id}"
            cache.delete(cache_key)
            
            # Store in Redis for real-time updates
            if self.redis_client:
                redis_key = f"notifications:user:{notification.recipient.id}"
                notification_data = {
                    'id': str(notification.id),
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'created_at': notification.created_at.isoformat(),
                    'is_read': False
                }
                
                self.redis_client.lpush(redis_key, json.dumps(notification_data))
                self.redis_client.ltrim(redis_key, 0, 99)  # Keep only latest 100
                self.redis_client.expire(redis_key, 86400 * 7)  # 7 days
            
            return True
            
        except Exception as e:
            logger.error(f"In-app send failed: {str(e)}")
            return False
    
    def _send_email(self, notification: Notification) -> bool:
        """Send notification via email"""
        try:
            from django.core.mail import send_mail
            
            # Check if user has email
            if not notification.recipient.email:
                return False
            
            # Simple email for now
            send_mail(
                subject=f"[SOI] {notification.title}",
                message=notification.message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@soi.ie'),
                recipient_list=[notification.recipient.email],
                fail_silently=False
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            return False
    
    def _send_push(self, notification: Notification) -> bool:
        """Send push notification (placeholder for future implementation)"""
        try:
            # TODO: Implement push notification service
            logger.info(f"Push notification would be sent: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Push send failed: {str(e)}")
            return False
    
    def bulk_notify(
        self,
        recipients: List[User],
        title: str,
        message: str,
        notification_type: str = 'bulk_operation',
        priority: str = 'MEDIUM',
        sender: Optional[User] = None,
        related_object: Any = None,
        context_data: Optional[Dict] = None
    ) -> List[Notification]:
        """Send notification to multiple recipients"""
        
        notifications = []
        
        try:
            with transaction.atomic():
                for recipient in recipients:
                    notification = self.create_notification(
                        recipient=recipient,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        priority=priority,
                        sender=sender,
                        related_object=related_object,
                        context_data=context_data
                    )
                    
                    if notification:
                        notifications.append(notification)
                
                logger.info(f"Created {len(notifications)} bulk notifications")
                return notifications
                
        except Exception as e:
            logger.error(f"Bulk notification failed: {str(e)}")
            return notifications
    
    def notify_user_type(
        self,
        user_type: str,
        title: str,
        message: str,
        notification_type: str = 'system_alert',
        priority: str = 'MEDIUM',
        sender: Optional[User] = None,
        exclude_users: Optional[List[User]] = None
    ) -> List[Notification]:
        """Send notification to all users of a specific type"""
        
        try:
            recipients = User.objects.filter(user_type=user_type, is_active=True)
            
            if exclude_users:
                recipients = recipients.exclude(id__in=[u.id for u in exclude_users])
            
            return self.bulk_notify(
                recipients=list(recipients),
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                sender=sender
            )
            
        except Exception as e:
            logger.error(f"User type notification failed: {str(e)}")
            return []
    
    def mark_as_read(self, notification_id: str, user: User) -> bool:
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            
            notification.mark_as_read()
            
            # Update Redis cache
            if self.redis_client:
                redis_key = f"notifications:user:{user.id}"
                notifications_data = self.redis_client.lrange(redis_key, 0, -1)
                
                updated_notifications = []
                for data in notifications_data:
                    notif_data = json.loads(data)
                    if notif_data['id'] == str(notification_id):
                        notif_data['is_read'] = True
                    updated_notifications.append(json.dumps(notif_data))
                
                if updated_notifications:
                    self.redis_client.delete(redis_key)
                    for notif_data in updated_notifications:
                        self.redis_client.rpush(redis_key, notif_data)
                    self.redis_client.expire(redis_key, 86400 * 7)
            
            # Clear unread count cache
            cache_key = f"unread_notifications_{user.id}"
            cache.delete(cache_key)
            
            # Send WebSocket update
            if self.channel_layer:
                user_channel = f"user_{user.id}"
                async_to_sync(self.channel_layer.group_send)(user_channel, {
                    'type': 'notification_read',
                    'notification_id': str(notification_id)
                })
            
            return True
            
        except Notification.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {str(e)}")
            return False
    
    def mark_all_as_read(self, user: User) -> int:
        """Mark all notifications as read for a user"""
        try:
            count = Notification.objects.filter(
                recipient=user,
                status__in=['PENDING', 'SENT', 'DELIVERED']
            ).update(
                status='READ',
                read_at=timezone.now()
            )
            
            # Clear Redis cache
            redis_key = f"notifications:user:{user.id}"
            self.redis_client.delete(redis_key)
            
            # Clear unread count cache
            cache_key = f"unread_notifications_{user.id}"
            cache.delete(cache_key)
            
            # Send WebSocket update
            if self.channel_layer:
                user_channel = f"user_{user.id}"
                async_to_sync(self.channel_layer.group_send)(user_channel, {
                    'type': 'notifications_all_read'
                })
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {str(e)}")
            return 0
    
    def get_unread_count(self, user: User) -> int:
        """Get unread notification count for user"""
        cache_key = f"unread_notifications_{user.id}"
        count = cache.get(cache_key)
        
        if count is None:
            count = Notification.objects.filter(
                recipient=user,
                status__in=['PENDING', 'SENT', 'DELIVERED']
            ).count()
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        
        return count
    
    def get_recent_notifications(self, user: User, limit: int = 20) -> List[Dict]:
        """Get recent notifications for user"""
        try:
            # Try Redis first
            if self.redis_client:
                redis_key = f"notifications:user:{user.id}"
                cached_data = self.redis_client.lrange(redis_key, 0, limit - 1)
                
                if cached_data:
                    return [json.loads(data) for data in cached_data]
            
            # Fallback to database
            notifications = Notification.objects.filter(
                recipient=user
            ).order_by('-created_at')[:limit]
            
            result = []
            for notification in notifications:
                result.append({
                    'id': str(notification.id),
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'status': notification.status,
                    'created_at': notification.created_at.isoformat(),
                    'is_read': notification.status == 'READ',
                    'related_object': self._get_related_object_data(notification),
                    'sender': notification.sender.username if notification.sender else None,
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get recent notifications: {str(e)}")
            return []
    
    def cleanup_expired_notifications(self) -> int:
        """Clean up expired notifications"""
        try:
            count = Notification.objects.filter(
                expires_at__lt=timezone.now(),
                status__in=['PENDING', 'SENT', 'DELIVERED']
            ).update(status='EXPIRED')
            
            logger.info(f"Marked {count} notifications as expired")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired notifications: {str(e)}")
            return 0
    
    def _calculate_after_quiet_hours(self, preferences: NotificationPreference) -> timezone.datetime:
        """Calculate when to send notification after quiet hours"""
        import pytz
        
        user_tz = pytz.timezone(preferences.timezone)
        now = timezone.now().astimezone(user_tz)
        
        if preferences.quiet_hours_end:
            # Schedule for end of quiet hours
            end_time = now.replace(
                hour=preferences.quiet_hours_end.hour,
                minute=preferences.quiet_hours_end.minute,
                second=0,
                microsecond=0
            )
            
            if end_time <= now:
                # Next day
                end_time += timedelta(days=1)
            
            return end_time.astimezone(timezone.utc)
        
        return timezone.now()
    
    def _get_related_object_data(self, notification: Notification) -> Optional[Dict]:
        """Get related object data for notification"""
        if notification.related_object:
            try:
                return {
                    'type': notification.content_type.model,
                    'id': notification.object_id,
                    'name': str(notification.related_object)
                }
            except Exception:
                pass
        return None
    
    def _log_delivery(self, notification: Notification, channel: str, status: str, message: str):
        """Log notification delivery attempt"""
        try:
            NotificationLog.objects.create(
                notification=notification,
                level='INFO' if status == 'SUCCESS' else 'ERROR',
                message=message,
                channel_type=channel,
                delivery_status=status
            )
        except Exception as e:
            logger.error(f"Failed to log delivery: {str(e)}")


# Global notification service instance
notification_service = NotificationService() 