"""
WebSocket consumers for real-time notifications
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .notification_service import notification_service

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get user from scope (set by auth middleware)
            self.user = self.scope.get('user')
            
            if not self.user or isinstance(self.user, AnonymousUser):
                logger.warning("Unauthenticated WebSocket connection attempt")
                await self.close()
                return
            
            # Join user-specific group
            self.user_group_name = f"user_{self.user.id}"
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            
            # Join user type group for broadcast messages
            self.user_type_group_name = f"user_type_{self.user.user_type}"
            await self.channel_layer.group_add(
                self.user_type_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send initial data
            await self.send_initial_data()
            
            logger.info(f"WebSocket connected for user {self.user.username}")
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'user_group_name'):
                await self.channel_layer.group_discard(
                    self.user_group_name,
                    self.channel_name
                )
            
            if hasattr(self, 'user_type_group_name'):
                await self.channel_layer.group_discard(
                    self.user_type_group_name,
                    self.channel_name
                )
            
            logger.info(f"WebSocket disconnected for user {getattr(self.user, 'username', 'unknown')}")
            
        except Exception as e:
            logger.error(f"WebSocket disconnect error: {str(e)}")
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_read':
                await self.handle_mark_read(data)
            elif message_type == 'mark_all_read':
                await self.handle_mark_all_read()
            elif message_type == 'get_notifications':
                await self.handle_get_notifications(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"WebSocket receive error: {str(e)}")
    
    async def send_initial_data(self):
        """Send initial notification data to client"""
        try:
            # Get unread count
            unread_count = await database_sync_to_async(
                notification_service.get_unread_count
            )(self.user)
            
            # Get recent notifications
            recent_notifications = await database_sync_to_async(
                notification_service.get_recent_notifications
            )(self.user, 10)
            
            await self.send(text_data=json.dumps({
                'type': 'initial_data',
                'unread_count': unread_count,
                'notifications': recent_notifications
            }))
            
        except Exception as e:
            logger.error(f"Failed to send initial data: {str(e)}")
    
    async def handle_mark_read(self, data):
        """Handle mark notification as read"""
        try:
            notification_id = data.get('notification_id')
            if not notification_id:
                return
            
            success = await database_sync_to_async(
                notification_service.mark_as_read
            )(notification_id, self.user)
            
            if success:
                # Get updated unread count
                unread_count = await database_sync_to_async(
                    notification_service.get_unread_count
                )(self.user)
                
                await self.send(text_data=json.dumps({
                    'type': 'notification_marked_read',
                    'notification_id': notification_id,
                    'unread_count': unread_count
                }))
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {str(e)}")
    
    async def handle_mark_all_read(self):
        """Handle mark all notifications as read"""
        try:
            count = await database_sync_to_async(
                notification_service.mark_all_as_read
            )(self.user)
            
            await self.send(text_data=json.dumps({
                'type': 'all_notifications_marked_read',
                'count': count,
                'unread_count': 0
            }))
            
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {str(e)}")
    
    async def handle_get_notifications(self, data):
        """Handle get notifications request"""
        try:
            limit = data.get('limit', 20)
            notifications = await database_sync_to_async(
                notification_service.get_recent_notifications
            )(self.user, limit)
            
            await self.send(text_data=json.dumps({
                'type': 'notifications_list',
                'notifications': notifications
            }))
            
        except Exception as e:
            logger.error(f"Failed to get notifications: {str(e)}")
    
    # Group message handlers
    async def notification_message(self, event):
        """Handle new notification message"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'new_notification',
                'notification': event['notification']
            }))
            
        except Exception as e:
            logger.error(f"Failed to send notification message: {str(e)}")
    
    async def notification_read(self, event):
        """Handle notification read event"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'notification_read',
                'notification_id': event['notification_id']
            }))
            
        except Exception as e:
            logger.error(f"Failed to send notification read event: {str(e)}")
    
    async def notifications_all_read(self, event):
        """Handle all notifications read event"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'all_notifications_read'
            }))
            
        except Exception as e:
            logger.error(f"Failed to send all notifications read event: {str(e)}")


class SystemNotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for system-wide notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get user from scope
            self.user = self.scope.get('user')
            
            if not self.user or isinstance(self.user, AnonymousUser):
                await self.close()
                return
            
            # Only allow staff users for system notifications
            if not self.user.is_staff:
                await self.close()
                return
            
            # Join system notifications group
            self.group_name = "system_notifications"
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
            logger.info(f"System WebSocket connected for user {self.user.username}")
            
        except Exception as e:
            logger.error(f"System WebSocket connection error: {str(e)}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
            
            logger.info(f"System WebSocket disconnected for user {getattr(self.user, 'username', 'unknown')}")
            
        except Exception as e:
            logger.error(f"System WebSocket disconnect error: {str(e)}")
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                logger.warning(f"Unknown system message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"System WebSocket receive error: {str(e)}")
    
    # Group message handlers
    async def system_alert(self, event):
        """Handle system alert"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'system_alert',
                'alert': event['alert']
            }))
            
        except Exception as e:
            logger.error(f"Failed to send system alert: {str(e)}")
    
    async def system_status(self, event):
        """Handle system status update"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'system_status',
                'status': event['status']
            }))
            
        except Exception as e:
            logger.error(f"Failed to send system status: {str(e)}") 