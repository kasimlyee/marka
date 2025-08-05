import os
import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSplitter, QProgressBar, QGridLayout
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor
from datetime import datetime
from .services.data_service import DataService
from .components.button import Button
from .icons import ICONS, SvgIcon

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import setup_logging

logger = setup_logging(__name__)
class Dashboard(QWidget):
    """Advanced dashboard with real-time updates and interactive widgets"""
    
    def __init__(self, data_service: DataService, theme, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.theme = theme
        self.setup_ui()
        
        # Connect to data updates
        self.data_service.data_updated.connect(self.refresh_metrics)
        
        # Setup auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_metrics)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def setup_ui(self):
        """Setup the dashboard UI"""
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(24, 24, 24, 24)
            layout.setSpacing(24)
            
            # Header with welcome message and quick actions
            self.create_header(layout)
            
            # Key metrics cards
            self.create_metrics_section(layout)
            
            # Main content area with charts and lists
            self.create_main_content(layout)
            
            self.setLayout(layout)
            self.refresh_metrics()
            
        except Exception as e:
            logger.error(f"Error setting up dashboard: {e}")
    
    def create_header(self, parent_layout):
        """Create dashboard header"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Welcome section
        welcome_layout = QVBoxLayout()
        
        welcome_title = QLabel("Good Morning, Administrator")
        welcome_title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 600;
            color: {self.theme.primary.name()};
            margin-bottom: 4px;
        """)
        
        welcome_subtitle = QLabel(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}")
        welcome_subtitle.setStyleSheet("font-size: 16px; color: #6B7280;")
        
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(welcome_subtitle)
        
        # Quick action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        
        quick_actions = [
            {"text": "Generate Reports", "icon": "FileText", "primary": True},
            {"text": "Add Student", "icon": "Plus", "primary": False},
            {"text": "Export Data", "icon": "Download", "primary": False},
        ]
        
        for action in quick_actions:
            btn = Button(action["text"], action["icon"])
            btn.setFixedHeight(40)
            
            if action["primary"]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.theme.secondary.name()};
                        color: white;
                        border: none;
                        border-radius: 8px;
                        padding: 0 20px;
                        font-size: 14px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: {self.theme.secondary.darker(110).name()};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: white;
                        color: {self.theme.primary.name()};
                        border: 1px solid #E5E7EB;
                        border-radius: 8px;
                        padding: 0 20px;
                        font-size: 14px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: #F9FAFB;
                        border-color: {self.theme.secondary.name()};
                    }}
                """)
            
            actions_layout.addWidget(btn)
        
        header_layout.addLayout(welcome_layout)
        header_layout.addStretch()
        header_layout.addLayout(actions_layout)
        
        header_widget.setLayout(header_layout)
        parent_layout.addWidget(header_widget)
    
    def create_metrics_section(self, parent_layout):
        """Create metrics cards section"""
        metrics_widget = QWidget()
        metrics_layout = QHBoxLayout()
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(20)
        
        # Get metrics from data service
        #metrics = self.data_service.get_metrics()
        
        metric_configs = [
            {
                "title": "Total Students",
                "value": "100",
                "trend": "+12%",
                "trend_positive": True,
                "icon": "Users",
                "color": self.theme.secondary,
                "description": "Active enrollments"
            },
            {
                "title": "Active Classes",
                "value": "6",
                "trend": "+2%",
                "trend_positive": True,
                "icon": "GraduationCap",
                "color": self.theme.accent,
                "description": "Running classes"
            },
            {
                "title": "Average Performance",
                "value": "62.7%",
                "trend": "+5.2%",
                "trend_positive": True,
                "icon": "TrendingUp",
                "color": self.theme.success,
                "description": "Overall grade average"
            },
            {
                "title": "High Performers",
                "value": "123",
                "trend": "+18%",
                "trend_positive": True,
                "icon": "Award",
                "color": QColor("#8B5CF6"),
                "description": "A & B+ grades"
            }
        ]
        
        self.metric_cards = []
        for config in metric_configs:
            card = self.create_metric_card(config)
            self.metric_cards.append(card)
            metrics_layout.addWidget(card)
        
        metrics_widget.setLayout(metrics_layout)
        parent_layout.addWidget(metrics_widget)
    
    def create_metric_card(self, config):
        """Create an individual metric card"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 24px;
            }
            QFrame:hover {
                border-color: #D1D5DB;
            }
        """)
        card.setFixedHeight(140)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Header with icon and trend
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side - title and description
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title = QLabel(config["title"])
        title.setStyleSheet("font-size: 14px; color: #6B7280; font-weight: 500;")
        
        description = QLabel(config["description"])
        description.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        
        text_layout.addWidget(title)
        text_layout.addWidget(description)
        
        # Right side - icon
        icon_widget = SvgIcon(ICONS[config["icon"]], config["color"], QSize(24, 24))
        
        header_layout.addLayout(text_layout)
        header_layout.addStretch()
        header_layout.addWidget(icon_widget)
        
        # Value and trend
        value_layout = QHBoxLayout()
        value_layout.setContentsMargins(0, 0, 0, 0)
        
        value = QLabel(config["value"])
        value.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 700;
            color: {self.theme.primary.name()};
            line-height: 1;
        """)
        
        trend = QLabel(config["trend"])
        trend_color = "#10B981" if config["trend_positive"] else "#EF4444"
        trend.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {trend_color};
            background-color: {trend_color}20;
            padding: 4px 8px;
            border-radius: 12px;
        """)
        trend.setFixedHeight(24)
        
        value_layout.addWidget(value)
        value_layout.addStretch()
        value_layout.addWidget(trend)
        
        layout.addLayout(header_layout)
        layout.addStretch()
        layout.addLayout(value_layout)
        
        card.setLayout(layout)
        return card
    
    def create_main_content(self, parent_layout):
        """Create main dashboard content"""
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #E5E7EB; width: 2px; }")
        
        # Left panel - Charts and analytics
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Activity and quick info
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set proportional sizes
        splitter.setSizes([700, 300])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        parent_layout.addWidget(splitter)
    
    def create_left_panel(self):
        """Create left panel with charts and class performance"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # Performance overview chart
        chart_widget = QWidget()
        chart_widget.setStyleSheet("""
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 24px;
        """)
        
        chart_layout = QVBoxLayout()
        
        chart_header = QHBoxLayout()
        chart_title = QLabel("Class Performance Overview")
        chart_title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {self.theme.primary.name()};
        """)
        
        chart_subtitle = QLabel("Academic performance across all classes")
        chart_subtitle.setStyleSheet("font-size: 14px; color: #6B7280;")
        
        chart_text_layout = QVBoxLayout()
        chart_text_layout.addWidget(chart_title)
        chart_text_layout.addWidget(chart_subtitle)
        
        chart_header.addLayout(chart_text_layout)
        chart_header.addStretch()
        
        # Chart placeholder (in a real app, this would be a proper chart)
        chart_placeholder = QWidget()
        chart_placeholder.setFixedHeight(300)
        chart_placeholder.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #EEF2FF, stop:1 #E0E7FF);
            border-radius: 8px;
            border: 2px dashed #C7D2FE;
        """)
        
        placeholder_layout = QVBoxLayout()
        placeholder_label = QLabel("📊 Interactive Performance Chart")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("font-size: 16px; color: #6366F1; font-weight: 500;")
        
        placeholder_desc = QLabel("Real-time analytics dashboard\nwould be displayed here")
        placeholder_desc.setAlignment(Qt.AlignCenter)
        placeholder_desc.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        
        placeholder_layout.addStretch()
        placeholder_layout.addWidget(placeholder_label)
        placeholder_layout.addWidget(placeholder_desc)
        placeholder_layout.addStretch()
        
        chart_placeholder.setLayout(placeholder_layout)
        
        chart_layout.addLayout(chart_header)
        chart_layout.addWidget(chart_placeholder)
        chart_widget.setLayout(chart_layout)
        
        # Class performance list
        class_widget = self.create_class_performance_widget()
        
        layout.addWidget(chart_widget)
        layout.addWidget(class_widget)
        
        panel.setLayout(layout)
        return panel
    
    def create_class_performance_widget(self):
        """Create class performance widget"""
        widget = QWidget()
        widget.setStyleSheet("""
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 24px;
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Class Performance Breakdown")
        header.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {self.theme.primary.name()};
        """)
        layout.addWidget(header)
        
        # Class list
        classes_data = [
            {"name": "Primary 7", "students": 45, "average": 87.2, "grade": "A"},
            {"name": "Primary 6", "students": 38, "average": 82.1, "grade": "B+"},
            {"name": "Primary 5", "students": 42, "average": 79.8, "grade": "B"},
            {"name": "Secondary 4", "students": 35, "average": 91.5, "grade": "A"},
            {"name": "Secondary 3", "students": 40, "average": 85.3, "grade": "A"},
        ]
        
        for class_data in classes_data:
            class_item = self.create_class_item(class_data)
            layout.addWidget(class_item)
        
        widget.setLayout(layout)
        return widget
    
    def create_class_item(self, class_data):
        """Create individual class performance item"""
        item = QWidget()
        item.setStyleSheet("""
            background-color: #F9FAFB;
            border-radius: 8px;
            padding: 16px;
        """)
        item.setFixedHeight(70)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Class info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        class_name = QLabel(class_data["name"])
        class_name.setStyleSheet("font-size: 16px; font-weight: 600; color: #111827;")
        
        student_count = QLabel(f"{class_data['students']} students")
        student_count.setStyleSheet("font-size: 12px; color: #6B7280;")
        
        info_layout.addWidget(class_name)
        info_layout.addWidget(student_count)
        
        # Performance bar
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        
        progress_label = QLabel(f"Average: {class_data['average']:.1f}%")
        progress_label.setStyleSheet("font-size: 12px; color: #374151;")
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(class_data['average']))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(6)
        
        # Color based on performance
        if class_data['average'] >= 85:
            color = "#10B981"
        elif class_data['average'] >= 70:
            color = "#F59E0B"
        else:
            color = "#EF4444"
        
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: #E5E7EB;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {color};
            }}
        """)
        
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(progress_bar)
        
        # Grade badge
        grade_badge = QLabel(class_data["grade"])
        grade_badge.setAlignment(Qt.AlignCenter)
        grade_badge.setFixedSize(36, 36)
        grade_badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            border-radius: 18px;
            font-size: 14px;
            font-weight: 700;
        """)
        
        layout.addLayout(info_layout)
        layout.addLayout(progress_layout)
        layout.addStretch()
        layout.addWidget(grade_badge)
        
        item.setLayout(layout)
        return item
    
    def create_right_panel(self):
        """Create right panel with activity and notifications"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # Recent activities
        activity_widget = self.create_activity_widget()
        layout.addWidget(activity_widget)
        
        # System notifications
        notification_widget = self.create_notifications_widget()
        layout.addWidget(notification_widget)
        
        # Quick stats
        stats_widget = self.create_quick_stats_widget()
        layout.addWidget(stats_widget)
        
        panel.setLayout(layout)
        return panel
    
    def create_activity_widget(self):
        """Create recent activity widget"""
        widget = QWidget()
        widget.setStyleSheet("""
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 20px;
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Recent Activity")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {self.theme.primary.name()};
        """)
        
        view_all = QLabel("View All")
        view_all.setStyleSheet("""
            font-size: 12px;
            color: #6366F1;
            font-weight: 500;
        """)
        view_all.setCursor(Qt.PointingHandCursor)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(view_all)
        
        layout.addLayout(header_layout)
        
        # Activity items
        activities = [
            {
                "action": "Report generated for Class P7",
                "user": "Admin",
                "time": "2 hours ago",
                "type": "success",
                "icon": "FileText"
            },
            {
                "action": "New student enrolled",
                "user": "Nakamya Sarah",
                "time": "4 hours ago",
                "type": "info",
                "icon": "Users"
            },
            {
                "action": "Grades updated",
                "user": "Teacher Mary",
                "time": "6 hours ago",
                "type": "warning",
                "icon": "Edit"
            },
            {
                "action": "System backup completed",
                "user": "System",
                "time": "1 day ago",
                "type": "success",
                "icon": "Database"
            }
        ]
        
        for activity in activities:
            activity_item = self.create_activity_item(activity)
            layout.addWidget(activity_item)
        
        widget.setLayout(layout)
        return widget
    
    def create_activity_item(self, activity):
        """Create individual activity item"""
        item = QWidget()
        item.setFixedHeight(50)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Icon with status color
        status_colors = {
            "success": "#10B981",
            "info": "#3B82F6",
            "warning": "#F59E0B",
            "error": "#EF4444"
        }
        
        icon_container = QWidget()
        icon_container.setFixedSize(32, 32)
        icon_container.setStyleSheet(f"""
            background-color: {status_colors[activity['type']]}20;
            border-radius: 16px;
        """)
        
        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon = SvgIcon(ICONS[activity["icon"]], QColor(status_colors[activity['type']]), QSize(16, 16))
        icon_layout.addWidget(icon)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        icon_container.setLayout(icon_layout)
        
        # Activity details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(2)
        
        action_label = QLabel(activity["action"])
        action_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #111827;")
        
        meta_info = QLabel(f"by {activity['user']} • {activity['time']}")
        meta_info.setStyleSheet("font-size: 11px; color: #6B7280;")
        
        details_layout.addWidget(action_label)
        details_layout.addWidget(meta_info)
        
        layout.addWidget(icon_container)
        layout.addLayout(details_layout)
        layout.addStretch()
        
        item.setLayout(layout)
        return item
    
    def create_notifications_widget(self):
        """Create system notifications widget"""
        widget = QWidget()
        widget.setStyleSheet("""
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 20px;
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Header
        title = QLabel("System Alerts")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {self.theme.primary.name()};
        """)
        layout.addWidget(title)
        
        # Notifications
        notifications = [
            {
                "message": "License expires in 45 days",
                "type": "warning",
                "action": "Renew License"
            },
            {
                "message": "Database backup recommended",
                "type": "info",
                "action": "Backup Now"
            },
            {
                "message": "5 pending student approvals",
                "type": "info",
                "action": "Review"
            }
        ]
        
        for notification in notifications:
            notif_item = self.create_notification_item(notification)
            layout.addWidget(notif_item)
        
        widget.setLayout(layout)
        return widget
    
    def create_notification_item(self, notification):
        """Create individual notification item"""
        item = QWidget()
        item.setStyleSheet("""
            background-color: #F9FAFB;
            border-radius: 8px;
            padding: 12px;
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Status indicator
        indicator = QLabel()
        indicator.setFixedSize(8, 8)
        indicator_color = "#F59E0B" if notification["type"] == "warning" else "#3B82F6"
        indicator.setStyleSheet(f"""
            background-color: {indicator_color};
            border-radius: 4px;
        """)
        
        # Message
        message = QLabel(notification["message"])
        message.setStyleSheet("font-size: 12px; color: #374151;")
        
        # Action button
        action_btn = QPushButton(notification["action"])
        action_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                color: #6B7280;
            }
            QPushButton:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
        """)
        action_btn.setCursor(Qt.PointingHandCursor)
        
        layout.addWidget(indicator)
        layout.addWidget(message)
        layout.addStretch()
        layout.addWidget(action_btn)
        
        item.setLayout(layout)
        return item
    
    def create_quick_stats_widget(self):
        """Create quick statistics widget"""
        widget = QWidget()
        widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #667EEA, stop:1 #764BA2);
            border-radius: 12px;
            padding: 20px;
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header
        title = QLabel("Quick Stats")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: white;")
        layout.addWidget(title)
        
        # Stats grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        
        stats = [
            {"label": "Reports Generated", "value": "1,247", "period": "This Month"},
            {"label": "Average Grade", "value": "B+", "period": "Current Term"},
            {"label": "Attendance Rate", "value": "94.2%", "period": "This Week"},
            {"label": "Active Teachers", "value": "28", "period": "Online Now"}
        ]
        
        for i, stat in enumerate(stats):
            stat_widget = QWidget()
            stat_layout = QVBoxLayout()
            stat_layout.setSpacing(4)
            
            value_label = QLabel(stat["value"])
            value_label.setStyleSheet("font-size: 20px; font-weight: 700; color: white;")
            
            label_text = QLabel(stat["label"])
            label_text.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.8);")
            
            period_text = QLabel(stat["period"])
            period_text.setStyleSheet("font-size: 9px; color: rgba(255, 255, 255, 0.6);")
            
            stat_layout.addWidget(value_label)
            stat_layout.addWidget(label_text)
            stat_layout.addWidget(period_text)
            
            stat_widget.setLayout(stat_layout)
            stats_grid.addWidget(stat_widget, i // 2, i % 2)
        
        layout.addLayout(stats_grid)
        widget.setLayout(layout)
        return widget
    
    def refresh_metrics(self):
        """Refresh dashboard metrics"""
        try:
            # This would typically fetch fresh data from the database
            # For now, we'll just update the display
            metrics = self.data_service.get_metrics()
            logger.info("Dashboard metrics refreshed")
        except Exception as e:
            logger.error(f"Error refreshing metrics: {e}")

