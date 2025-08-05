import sys
import os
from datetime import datetime


from PySide6.QtWidgets import ( QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QLineEdit,
    QComboBox, QMessageBox, QScrollArea,
    QFrame, QProgressBar, QToolButton,  QSplitter,
    QHeaderView, QAbstractItemView,QCheckBox,
    QMenu, 
    QButtonGroup, QGridLayout,QWidgetAction
)
from PySide6.QtGui import (
    QIcon, QColor, QAction, QShortcut,
    QKeySequence, 
)
from PySide6.QtCore import (
    Qt, QSize, QTimer, Signal, QPropertyAnimation,
    QEasingCurve, QSettings, Qt
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from .models.data_models import (
    Student, UserRole, NotificationType, LicenseType
)
from .icons import ICONS, SvgIcon
from utils.logger import setup_logging
from .theme import Theme
from .components.notification_manager import NotificationManager
from .components.button import Button
from .components.sidebar import Sidebar
from .services.data_service import DataService
from .dashboard import Dashboard
from .components.student_view import StudentsView

logger = setup_logging(__name__)


class MainWindow(QMainWindow):
    
    def __init__(self):
        """
        Initialize the MainWindow instance.

        This constructor sets up the essential services and UI components 
        for the Marka Report Card System application, including the 
        data service, notification manager, theme, and settings. It also 
        initializes the UI, shortcuts, status bar, and restores the previous 
        window state. Finally, it connects necessary signals and logs the 
        successful initialization of the application.
        """

        super().__init__()
        
        # Initialize core services
        self.data_service = DataService()
        self.notification_manager = NotificationManager(self)
        self.theme = Theme()
        
        # Settings
        self.settings = QSettings("Marka", "ReportCardSystem")
        
        
        # Initialize UI
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_status_bar()
        self.restore_window_state()
        
        # Connect signals
        self.connect_signals()
        
        logger.info("Marka Report Card System initialized successfully")
    
    
    def setup_ui(self):
        """Setup the main UI"""
        try:
            self.setWindowTitle("Marka | Report Card Generator")
            self.setMinimumSize(1400, 900)
            
            # Apply theme
            self.theme.apply_to_widget(self)
            
            # Set window icon
            if "Shield" in ICONS:
                icon_widget = SvgIcon(ICONS["Shield"], self.theme.secondary, QSize(32, 32))
                self.setWindowIcon(QIcon(icon_widget.get_pixmap(QSize(32, 32))))
            
            # Create central widget
            central_widget = QWidget()
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            # Create sidebar
            self.sidebar = Sidebar(self.theme, self)
            main_layout.addWidget(self.sidebar)
            
            # Create main content area
            self.content_area = QWidget()
            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(0)
            
            # Create top bar
            self.top_bar = self.create_top_bar()
            content_layout.addWidget(self.top_bar)
            
            # Create main content stack
            self.content_stack = QStackedWidget()
            self.content_stack.setStyleSheet("background-color: #F8FAFC;")
            
            # Create views
            self.dashboard_view = Dashboard(self.data_service, self.theme, self)
            self.students_view = StudentsView(self.data_service, self.theme, self)
            
            # Add views to stack
            self.content_stack.addWidget(self.dashboard_view)
            self.content_stack.addWidget(self.students_view)
            
            # Create placeholder views for other sections
            self.create_placeholder_views()
            
            content_layout.addWidget(self.content_stack)
            self.content_area.setLayout(content_layout)
            
            main_layout.addWidget(self.content_area, 1)
            central_widget.setLayout(main_layout)
            self.setCentralWidget(central_widget)
            
            # Create notification overlay
            self.notification_overlay = self.create_notification_overlay()
            
        except Exception as e:
            logger.error(f"Error setting up UI: {e}")
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize UI: {e}")
    
    def create_top_bar(self):
        """Create the top navigation bar"""
        top_bar = QWidget()
        top_bar.setFixedHeight(70)
        top_bar.setStyleSheet("""
            QWidget {
                background-color: white;
                border-bottom: 1px solid #E5E7EB;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(20)
        
        # Left section - menu toggle and breadcrumb
        left_section = QWidget()
        left_layout = QHBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        # Menu toggle button
        self.menu_toggle = QToolButton()
        self.menu_toggle.setFixedSize(40, 40)
        self.menu_toggle.setStyleSheet("""
            QToolButton {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                background-color: white;
            }
            QToolButton:hover {
                background-color: #F9FAFB;
                border-color: #D1D5DB;
            }
            QToolButton:pressed {
                background-color: #F3F4F6;
            }
        """)
        menu_icon = SvgIcon(ICONS["Menu"], self.theme.primary, QSize(20, 20))
        self.menu_toggle.setIcon(QIcon(menu_icon.get_pixmap(QSize(20, 20))))
        self.menu_toggle.clicked.connect(self.toggle_sidebar)
        
        # Breadcrumb
        self.breadcrumb = QLabel("Dashboard")
        self.breadcrumb.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {self.theme.primary.name()};
        """)
        
        left_layout.addWidget(self.menu_toggle)
        left_layout.addWidget(self.breadcrumb)
        left_section.setLayout(left_layout)
        
        # Center section - search bar
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("Search students, reports, or navigate...")
        self.global_search.setFixedWidth(400)
        self.global_search.setFixedHeight(40)
        self.global_search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DB;
                border-radius: 20px;
                padding: 0 16px 0 40px;
                font-size: 14px;
                background-color: #F9FAFB;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: white;
                outline: none;
            }
        """)
        
        # Add search icon to search bar
        search_icon_label = QLabel()
        search_icon = SvgIcon(ICONS["Search"], QColor("#9CA3AF"), QSize(18, 18))
        search_icon_label.setPixmap(search_icon.get_pixmap(QSize(18, 18)))
        search_icon_label.setParent(self.global_search)
        search_icon_label.move(12, 11)
        
        # Right section - user menu and notifications
        right_section = QWidget()
        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        # Notifications button
        self.notifications_btn = QToolButton()
        self.notifications_btn.setFixedSize(40, 40)
        self.notifications_btn.setStyleSheet("""
            QToolButton {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                background-color: white;
            }
            QToolButton:hover {
                background-color: #F9FAFB;
                border-color: #D1D5DB;
            }
        """)
        bell_icon = SvgIcon(ICONS["Bell"], self.theme.primary, QSize(20, 20))
        self.notifications_btn.setIcon(QIcon(bell_icon.get_pixmap(QSize(20, 20))))
        self.notifications_btn.setToolTip("Notifications")
        
        # Add notification badge
        self.notification_badge = QLabel("3")
        self.notification_badge.setParent(self.notifications_btn)
        self.notification_badge.setFixedSize(18, 18)
        self.notification_badge.setStyleSheet("""
            background-color: #EF4444;
            color: white;
            border-radius: 9px;
            font-size: 10px;
            font-weight: 600;
            qproperty-alignment: AlignCenter;
        """)
        self.notification_badge.move(26, 2)
        
        # User menu button
        self.user_menu_btn = QToolButton()
        self.user_menu_btn.setFixedSize(160, 40)
        self.user_menu_btn.setStyleSheet("""
            QToolButton {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                background-color: white;
                text-align: left;
                padding: 0 12px;
            }
            QToolButton:hover {
                background-color: #F9FAFB;
                border-color: #D1D5DB;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        # User menu layout
        user_menu_widget = QWidget()
        user_menu_layout = QHBoxLayout()
        user_menu_layout.setContentsMargins(0, 0, 0, 0)
        user_menu_layout.setSpacing(8)
        
        # User avatar
        user_avatar = QLabel()
        user_avatar.setFixedSize(28, 28)
        user_avatar.setStyleSheet(f"""
            background-color: {self.theme.secondary.name()};
            color: white;
            border-radius: 14px;
            font-weight: 600;
            font-size: 12px;
            qproperty-alignment: AlignCenter;
        """)
        user_avatar.setText("AD")
        
        # User info
        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(0)
        
        user_name = QLabel("Administrator")
        user_name.setStyleSheet("font-size: 13px; font-weight: 500; color: #111827;")
        
        user_role = QLabel("System Admin")
        user_role.setStyleSheet("font-size: 11px; color: #6B7280;")
        
        user_info_layout.addWidget(user_name)
        user_info_layout.addWidget(user_role)
        
        user_menu_layout.addWidget(user_avatar)
        user_menu_layout.addLayout(user_info_layout)
        user_menu_layout.addStretch()
        
        user_menu_widget.setLayout(user_menu_layout)
        action = QWidgetAction(user_menu_widget)
        action.setDefaultWidget(self.user_menu_btn)
        
        # Create user menu
        self.create_user_menu()
        
        right_layout.addWidget(self.notifications_btn)
        right_layout.addWidget(self.user_menu_btn)
        right_section.setLayout(right_layout)
        
        layout.addWidget(left_section)
        layout.addStretch()
        layout.addWidget(self.global_search)
        layout.addStretch()
        layout.addWidget(right_section)
        
        top_bar.setLayout(layout)
        return top_bar
    
    def create_user_menu(self):
        """Create user dropdown menu"""
        user_menu = QMenu(self)
        user_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 8px 0;
                min-width: 200px;
            }
            QMenu::item {
                padding: 8px 16px;
                font-size: 14px;
                color: #374151;
            }
            QMenu::item:selected {
                background-color: #F3F4F6;
                color: #111827;
            }
            QMenu::separator {
                height: 1px;
                background-color: #E5E7EB;
                margin: 4px 0;
            }
        """)
        
        # Menu items
        profile_action = QAction("👤 Profile Settings", self)
        profile_action.triggered.connect(self.show_profile_settings)
        
        preferences_action = QAction("⚙️ Preferences", self)
        preferences_action.triggered.connect(self.show_preferences)
        
        help_action = QAction("❓ Help & Support", self)
        help_action.triggered.connect(self.show_help)
        
        about_action = QAction("ℹ️ About Marka", self)
        about_action.triggered.connect(self.show_about)
        
        logout_action = QAction("🚪 Sign Out", self)
        logout_action.triggered.connect(self.logout)
        
        user_menu.addAction(profile_action)
        user_menu.addAction(preferences_action)
        user_menu.addSeparator()
        user_menu.addAction(help_action)
        user_menu.addAction(about_action)
        user_menu.addSeparator()
        user_menu.addAction(logout_action)
        
        self.user_menu_btn.setMenu(user_menu)
        self.user_menu_btn.setPopupMode(QToolButton.InstantPopup)
    
    def create_placeholder_views(self):
        """Create placeholder views for sections not yet implemented"""
        placeholder_sections = [
            "teachers", "subjects", "classes", "reports", "templates",
            "bulk_reports", "analytics", "users", "settings", "backup", "license"
        ]
        
        for section in placeholder_sections:
            placeholder = self.create_placeholder_view(section)
            self.content_stack.addWidget(placeholder)
    
    def create_placeholder_view(self, section_name: str):
        """Create a placeholder view for unimplemented sections"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # Icon
        section_icons = {
            "teachers": "GraduationCap",
            "subjects": "BookOpen",
            "classes": "Users",
            "reports": "FileText",
            "templates": "FileText",
            "bulk_reports": "FileText",
            "analytics": "BarChart3",
            "users": "User",
            "settings": "Settings",
            "backup": "Database",
            "license": "Key"
        }
        
        icon_name = section_icons.get(section_name, "Settings")
        icon_widget = SvgIcon(ICONS[icon_name], QColor("#9CA3AF"), QSize(64, 64))
        
        icon_label = QLabel()
        icon_label.setPixmap(icon_widget.get_pixmap(QSize(64, 64)))
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Title
        title = QLabel(f"{section_name.replace('_', ' ').title()} Module")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: 600;
            color: #374151;
        """)
        title.setAlignment(Qt.AlignCenter)
        
        # Description
        description = QLabel("This feature is coming soon in a future update.")
        description.setStyleSheet("""
            font-size: 16px;
            color: #6B7280;
        """)
        description.setAlignment(Qt.AlignCenter)
        
        # Status badge
        status_badge = QLabel("🚧 Under Development")
        status_badge.setStyleSheet("""
            background-color: #FEF3C7;
            color: #92400E;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        """)
        status_badge.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(status_badge)
        
        widget.setLayout(layout)
        return widget
    
    def create_notification_overlay(self):
        """Create notification overlay system"""
        overlay = QWidget(self)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        overlay.setStyleSheet("background-color: transparent;")
        
        overlay_layout = QVBoxLayout()
        overlay_layout.setContentsMargins(20, 20, 20, 20)
        overlay_layout.setSpacing(10)
        overlay_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
        
        overlay.setLayout(overlay_layout)
        overlay.hide()
        
        return overlay
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        try:
            # Global shortcuts
            shortcuts = [
                (QKeySequence("Ctrl+N"), self.new_student),
                (QKeySequence("Ctrl+F"), self.focus_search),
                (QKeySequence("Ctrl+R"), self.refresh_data),
                (QKeySequence("Ctrl+Q"), self.close),
                (QKeySequence("F1"), self.show_help),
                (QKeySequence("F5"), self.refresh_data),
                (QKeySequence("Ctrl+,"), self.show_preferences),
            ]
            
            for key_sequence, slot in shortcuts:
                shortcut = QShortcut(key_sequence, self)
                shortcut.activated.connect(slot)
            
        except Exception as e:
            logger.error(f"Error setting up shortcuts: {e}")
    
    def setup_status_bar(self):
        """Setup status bar"""
        try:
            status_bar = self.statusBar()
            status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #F9FAFB;
                    border-top: 1px solid #E5E7EB;
                    color: #6B7280;
                    font-size: 12px;
                }
            """)
            
            # Status indicators
            self.connection_status = QLabel("🟢 Connected")
            self.license_status = QLabel("🛡️ Licensed")
            self.version_label = QLabel("v2.0.1 Enterprise")
            
            status_bar.addWidget(self.connection_status)
            status_bar.addWidget(self.license_status)
            status_bar.addPermanentWidget(self.version_label)
            
        except Exception as e:
            logger.error(f"Error setting up status bar: {e}")
    
    def connect_signals(self):
        """Connect application signals"""
        try:
            # Sidebar navigation
            self.sidebar.navigation_changed.connect(self.navigate_to_section)
            
            # Notification manager
            self.notification_manager.show_notification.connect(self.display_notification)
            
            # Data service updates
            self.data_service.data_updated.connect(self.on_data_updated)
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
    
    def navigate_to_section(self, section_id: str):
        """Navigate to a specific section"""
        try:
            # Map section IDs to stack indices
            section_mapping = {
                "dashboard": 0,
                "students": 1,
                "teachers": 2,
                "subjects": 3,
                "classes": 4,
                "reports": 5,
                "templates": 6,
                "bulk_reports": 7,
                "analytics": 8,
                "users": 9,
                "settings": 10,
                "backup": 11,
                "license": 12
            }
            
            if section_id in section_mapping:
                index = section_mapping[section_id]
                self.content_stack.setCurrentIndex(index)
                
                # Update breadcrumb
                section_titles = {
                    "dashboard": "Dashboard",
                    "students": "Students Management",
                    "teachers": "Teachers Management",
                    "subjects": "Subjects Management",
                    "classes": "Classes Management",
                    "reports": "Generate Reports",
                    "templates": "Report Templates",
                    "bulk_reports": "Bulk Reports",
                    "analytics": "Analytics",
                    "users": "User Management",
                    "settings": "Settings",
                    "backup": "Backup & Restore",
                    "license": "License Management"
                }
                
                self.breadcrumb.setText(section_titles.get(section_id, section_id.title()))
                
                logger.info(f"Navigated to section: {section_id}")
            else:
                logger.warning(f"Unknown section: {section_id}")
                
        except Exception as e:
            logger.error(f"Error navigating to section {section_id}: {e}")
    
    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        try:
            self.sidebar.toggle_collapse()
        except Exception as e:
            logger.error(f"Error toggling sidebar: {e}")
    
    def display_notification(self, message: str, type_str: str, duration: int):
        """Display a notification"""
        try:
            # Create notification widget
            notification = self.create_notification_widget(message, type_str)
            
            # Add to overlay
            self.notification_overlay.layout().addWidget(notification)
            self.notification_overlay.show()
            self.notification_overlay.raise_()
            
            # Auto-remove after duration
            QTimer.singleShot(duration, lambda: self.remove_notification(notification))
            
        except Exception as e:
            logger.error(f"Error displaying notification: {e}")
    
    def create_notification_widget(self, message: str, type_str: str):
        """Create a notification widget"""
        notification = QFrame()
        notification.setFixedWidth(350)
        notification.setFrameStyle(QFrame.Box)
        
        # Styling based on type
        type_styles = {
            "success": {"bg": "#10B981", "icon": "CheckCircle"},
            "error": {"bg": "#EF4444", "icon": "AlertCircle"},
            "warning": {"bg": "#F59E0B", "icon": "AlertCircle"},
            "info": {"bg": "#3B82F6", "icon": "AlertCircle"}
        }
        
        style_config = type_styles.get(type_str, type_styles["info"])
        
        notification.setStyleSheet(f"""
            QFrame {{
                background-color: {style_config["bg"]};
                border: none;
                border-radius: 8px;
                padding: 16px;
                color: white;
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Icon
        icon_widget = SvgIcon(ICONS[style_config["icon"]], QColor("white"), QSize(20, 20))
        layout.addWidget(icon_widget)
        
        # Message
        message_label = QLabel(message)
        message_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: white;
        """)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Close button
        close_btn = QToolButton()
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 10px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        close_icon = SvgIcon(ICONS["X"], QColor("white"), QSize(14, 14))
        close_btn.setIcon(QIcon(close_icon.get_pixmap(QSize(14, 14))))
        close_btn.clicked.connect(lambda: self.remove_notification(notification))
        
        layout.addWidget(close_btn)
        notification.setLayout(layout)
        
        return notification
    
    def remove_notification(self, notification):
        """Remove a notification with animation"""
        try:
            # Create fade out animation
            fade_animation = QPropertyAnimation(notification, b"windowOpacity")
            fade_animation.setDuration(300)
            fade_animation.setStartValue(1.0)
            fade_animation.setEndValue(0.0)
            fade_animation.finished.connect(lambda: self.cleanup_notification(notification))
            fade_animation.start()
            
        except Exception as e:
            logger.error(f"Error removing notification: {e}")
            self.cleanup_notification(notification)
    
    def cleanup_notification(self, notification):
        """Clean up notification widget"""
        try:
            notification.deleteLater()
            
            # Hide overlay if no more notifications
            if self.notification_overlay.layout().count() == 0:
                self.notification_overlay.hide()
                
        except Exception as e:
            logger.error(f"Error cleaning up notification: {e}")
    
    def restore_window_state(self):
        """Restore window state from settings"""
        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
            
            window_state = self.settings.value("windowState")
            if window_state:
                self.restoreState(window_state)
            
        except Exception as e:
            logger.error(f"Error restoring window state: {e}")
    
    def save_window_state(self):
        """Save window state to settings"""
        try:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
            
        except Exception as e:
            logger.error(f"Error saving window state: {e}")
    
    # Event handlers
    def on_data_updated(self, data_type: str):
        """Handle data updates"""
        try:
            if data_type == "students":
                self.notification_manager.show(
                    "Student data updated successfully",
                    NotificationType.SUCCESS
                )
            
        except Exception as e:
            logger.error(f"Error handling data update: {e}")
    
    # Menu actions
    def new_student(self):
        """Create new student"""
        logger.info("New student action triggered")
        # TODO: Implement new student dialog
    
    def focus_search(self):
        """Focus on global search"""
        self.global_search.setFocus()
        self.global_search.selectAll()
    
    def refresh_data(self):
        """Refresh application data"""
        try:
            # Refresh current view
            current_widget = self.content_stack.currentWidget()
            if hasattr(current_widget, 'refresh_data'):
                current_widget.refresh_data()
            
            self.notification_manager.show(
                "Data refreshed successfully",
                NotificationType.SUCCESS
            )
            
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            self.notification_manager.show(
                "Failed to refresh data",
                NotificationType.ERROR
            )
    
    def show_profile_settings(self):
        """Show profile settings dialog"""
        logger.info("Profile settings requested")
        # TODO: Implement profile settings dialog
    
    def show_preferences(self):
        """Show preferences dialog"""
        logger.info("Preferences requested")
        # TODO: Implement preferences dialog
    
    def show_help(self):
        """Show help dialog"""
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("Help & Support")
        help_dialog.setIcon(QMessageBox.Information)
        help_dialog.setText("""
        <h3>Marka Report Card System - Help</h3>
        <p><b>Version:</b> 1.0.0 Enterprise</p>
        <p><b>Support:</b> marka.codewithlyee.com/support</p>
        <p><b>Documentation:</b> docs.marka.codewithlyee.com</p>
        
        <h4>Quick Start:</h4>
        <ul>
        <li>Use the sidebar to navigate between sections</li>
        <li>Add students in the Students Management section</li>
        <li>Generate reports from the Reports section</li>
        <li>Use Ctrl+F to search globally</li>
        </ul>
        
        <h4>Keyboard Shortcuts:</h4>
        <ul>
        <li>Ctrl+N - New Student</li>
        <li>Ctrl+F - Focus Search</li>
        <li>Ctrl+R - Refresh Data</li>
        <li>F1 - Show Help</li>
        </ul>
        """)
        help_dialog.exec()
        
    
    def show_about(self):
        """Show about dialog"""
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("About Marka")
        about_dialog.setIcon(QMessageBox.Information)
        about_dialog.setText("""
        <h2>Marka Report Card System</h2>
        <p><b>Version:</b> 1.0.1 Enterprise Edition</p>
        <p><b>Build:</b> 2025.07.15</p>
        
        <p>report card generation system 
        designed for educational institutions.</p>
        
        <p><b>Features:</b></p>
        <ul>
        <li>Student Management</li>
        <li>Performance Tracking</li>
        <li>Automated Report Generation</li>
        <li>Advanced Analytics</li>
        <li>Multi-user Support</li>
        </ul>
        
        <p><b>© 2025 Kasim Lyee</b></p>
        <p>Licensed under Enterprise Agreement</p>
        """)
        about_dialog.exec()
    
    def logout(self):
        """Handle user logout"""
        reply = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to sign out?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.info("User logged out")
            # TODO: Implement logout logic
            self.close()
    
    def closeEvent(self, event):
        """Handle application close"""
        try:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Are you sure you want to exit Marka?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.save_window_state()
                logger.info("Application closing")
                event.accept()
            else:
                event.ignore()
                
        except Exception as e:
            logger.error(f"Error during application close: {e}")
            event.accept()
    
    def resizeEvent(self, event):
        """Handle window resize"""
        try:
            super().resizeEvent(event)
            
            # Update notification overlay size
            if hasattr(self, 'notification_overlay'):
                self.notification_overlay.setGeometry(0, 0, self.width(), self.height())
                
        except Exception as e:
            logger.error(f"Error handling resize: {e}")
