import sys
import os

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QPropertyAnimation,QEasingCurve,Qt, QSize
from PySide6.QtGui import QIcon, QColor
from ..icons import ICONS,SvgIcon 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import setup_logging

logger = setup_logging(__name__)
class Button(QPushButton):
    """Button with hover animations and loading states"""
    
    def __init__(self, text: str = "", icon_name: str = "", parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.is_loading = False
        self.original_text = text
        
        # Animation properties
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        
        if icon_name and icon_name in ICONS:
            self.setup_icon()
    
    def setup_icon(self):
        """Setup icon for the button"""
        try:
            icon_widget = SvgIcon(ICONS[self.icon_name], QColor("#FFFFFF"), QSize(16, 16))
            icon = QIcon(icon_widget.get_pixmap(QSize(16, 16)))
            self.setIcon(icon)
            self.setIconSize(QSize(16, 16))
        except Exception as e:
            logger.error(f"Error setting up button icon: {e}")
    
    def set_loading(self, loading: bool):
        """Set loading state"""
        self.is_loading = loading
        if loading:
            self.setText("Loading...")
            self.setEnabled(False)
        else:
            self.setText(self.original_text)
            self.setEnabled(True)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        if not self.is_loading:
            self.setStyleSheet(self.styleSheet() + "background-color: rgba(255, 255, 255, 0.1);")
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        if not self.is_loading:
            # Reset to original style
            current_style = self.styleSheet()
            self.setStyleSheet(current_style.replace("background-color: rgba(255, 255, 255, 0.1);", ""))
        super().leaveEvent(event)