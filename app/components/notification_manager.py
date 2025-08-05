import sys
import os
from PySide6.QtCore import QObject, Signal

from ..models.data_models import NotificationType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import setup_logging

logger = setup_logging(__name__)
class NotificationManager(QObject):
    """Enhanced notification system with queuing and animations"""
    
    show_notification = Signal(str, str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications = []
        self.max_notifications = 3
        self.notification_widgets = []
        
    def show(self, message: str, type: NotificationType = NotificationType.SUCCESS, duration: int = 3000):
        """Show a notification"""
        try:
            self.show_notification.emit(message, type.value, duration)
            logger.info(f"Notification: {type.value} - {message}")
        except Exception as e:
            logger.error(f"Error showing notification: {e}")