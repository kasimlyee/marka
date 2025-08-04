import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QLineEdit,
    QComboBox, QFormLayout, QDialog, QFileDialog, QMessageBox, QScrollArea,
    QFrame, QProgressBar, QToolButton, QSizePolicy, QSpacerItem, QSplitter
)
from PySide6.QtGui import (
    QIcon, QPixmap, QColor, QFont, QPainter, QLinearGradient, QBrush,
    QPalette, QStandardItemModel, QStandardItem
)
from PySide6.QtCore import (
    Qt, QSize, QTimer, Signal, QObject, QThread, QPropertyAnimation,
    QEasingCurve, QRect, QPoint
)
from PySide6.QtSvg import QSvgRenderer
from qt_material import apply_stylesheet

# Icons from Lucide (converted to SVG)
ICONS = {
    "book_open": """
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
    </svg>
    """,
    "users": """
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
        <circle cx="9" cy="7" r="4"></circle>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
    </svg>
    """,
    # Add all other icons from the React component here...
}

class SvgIcon(QWidget):
    def __init__(self, svg_string, color=None, parent=None):
        super().__init__(parent)
        self.renderer = QSvgRenderer()
        self.svg_string = svg_string
        self.color = color or QColor("#000000")
        self.renderer.load(svg_string.encode('utf-8'))
        self.setFixedSize(24, 24)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.renderer.render(painter)
        
        if self.color:
            # Recolor the icon
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(self.rect(), self.color)

class NotificationManager(QObject):
    show_notification = Signal(str, str)  # message, type
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications = []
        self.current_notification = None
        
    def show(self, message, type="success", duration=3000):
        self.show_notification.emit(message, type)
        QTimer.singleShot(duration, self.hide_current)
        
    def hide_current(self):
        pass  # Implemented in MainWindow

class Theme:
    def __init__(self):
        self.primary = QColor("#1D3557")
        self.secondary = QColor("#2A9D8F")
        self.accent = QColor("#F4A261")
        self.background = QColor("#F1FAEE")
        self.error = QColor("#E63946")
        self.success = QColor("#10B981")
        self.warning = QColor("#F59E0B")
        
    def apply_to_widget(self, widget):
        palette = widget.palette()
        palette.setColor(QPalette.Window, self.background)
        palette.setColor(QPalette.WindowText, self.primary)
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.AlternateBase, self.background)
        palette.setColor(QPalette.ToolTipBase, self.primary)
        palette.setColor(QPalette.ToolTipText, QColor("#FFFFFF"))
        palette.setColor(QPalette.Text, self.primary)
        palette.setColor(QPalette.Button, self.secondary)
        palette.setColor(QPalette.ButtonText, QColor("#FFFFFF"))
        palette.setColor(QPalette.BrightText, QColor("#FFFFFF"))
        palette.setColor(QPalette.Highlight, self.secondary)
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        widget.setPalette(palette)

class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = Theme()
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedWidth(250)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setStyleSheet(f"background-color: {self.theme.primary.name()};")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        icon = QLabel()
        icon.setFixedSize(40, 40)
        icon.setStyleSheet(f"""
            background-color: {self.theme.secondary.name()};
            border-radius: 8px;
            color: white;
            font-weight: bold;
            font-size: 16px;
            qproperty-alignment: AlignCenter;
        """)
        icon.setText("M")
        
        title = QLabel("Marka")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
        """)
        
        subtitle = QLabel("Report Card System")
        subtitle.setStyleSheet("""
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
        """)
        
        title_layout = QVBoxLayout()
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        header_layout.addWidget(icon)
        header_layout.addLayout(title_layout)
        header.setLayout(header_layout)
        
        layout.addWidget(header)
        
        # Navigation
        nav_widget = QWidget()
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(5)
        
        nav_items = [
            {"id": "dashboard", "icon": "bar_chart_3", "label": "Dashboard"},
            {"id": "students", "icon": "users", "label": "Students"},
            {"id": "subjects", "icon": "book_open", "label": "Subjects"},
            {"id": "reports", "icon": "file_text", "label": "Reports"},
            {"id": "analytics", "icon": "trending_up", "label": "Analytics", "locked": True},
            {"id": "users", "icon": "user_plus", "label": "User Management", "locked": True},
            {"id": "settings", "icon": "settings", "label": "Settings"},
            {"id": "license", "icon": "key", "label": "License"},
        ]
        
        for item in nav_items:
            btn = QPushButton(item["label"])
            btn.setObjectName(item["id"])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 12px 15px;
                    border-radius: 8px;
                    font-size: 14px;
                    color: {self.theme.primary.name()};
                }}
                QPushButton:hover {{
                    background-color: rgba(0, 0, 0, 0.05);
                }}
                QPushButton[pressed="true"] {{
                    background-color: {self.theme.secondary.name()};
                    color: white;
                }}
            """)
            
            icon_widget = SvgIcon(ICONS.get(item["icon"], ""), self.theme.primary)
            
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(icon_widget)
            btn_layout.addWidget(QLabel(item["label"]))
            btn_layout.addStretch()
            
            if item.get("locked"):
                lock_icon = SvgIcon(ICONS.get("lock", ""), QColor("#999999"))
                btn_layout.addWidget(lock_icon)
            
            btn.setLayout(btn_layout)
            nav_layout.addWidget(btn)
        
        nav_layout.addStretch()
        nav_widget.setLayout(nav_layout)
        
        # License info
        license_widget = QWidget()
        license_widget.setStyleSheet(f"""
            background-color: rgba(0, 0, 0, 0.05);
            border-radius: 8px;
            padding: 12px;
        """)
        license_layout = QVBoxLayout()
        
        license_header = QHBoxLayout()
        shield_icon = SvgIcon(ICONS.get("shield", ""), self.theme.secondary)
        license_header.addWidget(shield_icon)
        
        license_title = QLabel("Standard License")
        license_title.setStyleSheet(f"""
            font-weight: bold;
            font-size: 13px;
            color: {self.theme.primary.name()};
        """)
        license_header.addWidget(license_title)
        license_header.addStretch()
        
        license_layout.addLayout(license_header)
        
        license_expiry = QLabel("Expires: N/A")
        license_expiry.setStyleSheet("font-size: 11px; color: #666;")
        license_layout.addWidget(license_expiry)
        
        status_layout = QHBoxLayout()
        status_dot = QLabel()
        status_dot.setFixedSize(8, 8)
        status_dot.setStyleSheet("""
            background-color: #10B981;
            border-radius: 4px;
        """)
        status_layout.addWidget(status_dot)
        status_layout.addWidget(QLabel("Active"))
        status_layout.addStretch()
        
        license_layout.addLayout(status_layout)
        license_widget.setLayout(license_layout)
        
        nav_layout.addWidget(license_widget)
        layout.addWidget(nav_widget)
        
        self.setLayout(layout)

class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = Theme()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout()
        
        title = QLabel("Welcome to Marka")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {self.theme.primary.name()};
        """)
        
        subtitle = QLabel("Comprehensive school management dashboard")
        subtitle.setStyleSheet("font-size: 14px; color: #666;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header.setLayout(header_layout)
        
        layout.addWidget(header)
        
        # Stats cards
        stats_widget = QWidget()
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(15)
        
        stats = [
            {"label": "Total Students", "value": "0", "icon": "users", "color": self.theme.secondary, "trend": "+12%"},
            {"label": "Active Classes", "value": "0", "icon": "graduation_cap", "color": self.theme.accent, "trend": "+2%"},
            {"label": "Average Performance", "value": "0%", "icon": "trending_up", "color": self.theme.primary, "trend": "+5%"},
            {"label": "High Performers", "value": "0", "icon": "award", "color": self.theme.success, "trend": "+18%"},
        ]
        
        for stat in stats:
            card = QWidget()
            card.setStyleSheet(f"""
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                border-left: 4px solid {stat["color"].name()};
            """)
            
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(10)
            
            # Top row with text and icon
            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.setSpacing(0)
            
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(5)
            
            label = QLabel(stat["label"])
            label.setStyleSheet("font-size: 13px; color: #666;")
            
            value = QLabel(stat["value"])
            value.setStyleSheet(f"""
                font-size: 24px;
                font-weight: bold;
                color: {self.theme.primary.name()};
            """)
            
            text_layout.addWidget(label)
            text_layout.addWidget(value)
            top_row.addLayout(text_layout)
            top_row.addStretch()
            
            icon = SvgIcon(ICONS.get(stat["icon"], ""), stat["color"])
            top_row.addWidget(icon)
            
            card_layout.addLayout(top_row)
            
            # Trend indicator
            trend_layout = QHBoxLayout()
            trend_layout.setContentsMargins(0, 0, 0, 0)
            trend_layout.setSpacing(5)
            
            trend_label = QLabel(stat["trend"])
            trend_label.setStyleSheet(f"""
                font-size: 11px;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: {stat["color"].name()}20;
                color: {stat["color"].name()};
            """)
            
            trend_text = QLabel("vs last term")
            trend_text.setStyleSheet("font-size: 11px; color: #999;")
            
            trend_layout.addWidget(trend_label)
            trend_layout.addWidget(trend_text)
            trend_layout.addStretch()
            
            card_layout.addLayout(trend_layout)
            
            card.setLayout(card_layout)
            stats_layout.addWidget(card)
        
        stats_widget.setLayout(stats_layout)
        layout.addWidget(stats_widget)
        
        # Main content
        content_splitter = QSplitter(Qt.Vertical)
        
        # Recent activity and quick actions
        top_content = QWidget()
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)
        
        # Recent activity
        recent_activity = QWidget()
        recent_activity.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 20px;
        """)
        
        recent_layout = QVBoxLayout()
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(15)
        
        recent_title = QLabel("Recent Activity")
        recent_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.primary.name()};
        """)
        
        recent_layout.addWidget(recent_title)
        
        activities = [
            {"action": "Report generated", "student": "Nakamya Sarah", "time": "2 hours ago", "type": "success"},
            {"action": "New student added", "student": "Musoke David", "time": "5 hours ago", "type": "info"},
            {"action": "Grades updated", "student": "Class P7", "time": "1 day ago", "type": "warning"},
            {"action": "System backup completed", "student": "", "time": "2 days ago", "type": "success"},
        ]
        
        for activity in activities:
            item = QWidget()
            item.setStyleSheet("""
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 12px;
            """)
            
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(10)
            
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"""
                background-color: {"#10B981" if activity["type"] == "success" else 
                                  "#F59E0B" if activity["type"] == "warning" else "#3B82F6"};
                border-radius: 6px;
            """)
            
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(3)
            
            action = QLabel(activity["action"])
            action.setStyleSheet("font-weight: 500;")
            
            if activity["student"]:
                student = QLabel(activity["student"])
                student.setStyleSheet("font-size: 13px; color: #666;")
                text_layout.addWidget(student)
            
            text_layout.addWidget(action)
            
            time = QLabel(activity["time"])
            time.setStyleSheet("font-size: 12px; color: #999;")
            
            item_layout.addWidget(dot)
            item_layout.addLayout(text_layout)
            item_layout.addWidget(time)
            item_layout.addStretch()
            
            item.setLayout(item_layout)
            recent_layout.addWidget(item)
        
        recent_activity.setLayout(recent_layout)
        top_layout.addWidget(recent_activity, 2)
        
        # Quick actions
        quick_actions = QWidget()
        quick_actions.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 20px;
        """)
        
        quick_layout = QVBoxLayout()
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(15)
        
        quick_title = QLabel("Quick Actions")
        quick_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.primary.name()};
        """)
        
        quick_layout.addWidget(quick_title)
        
        actions = [
            {"label": "Add Student", "icon": "user_plus"},
            {"label": "Generate Reports", "icon": "file_text"},
            {"label": "Export Data", "icon": "download"},
            {"label": "System Backup", "icon": "database"},
        ]
        
        for action in actions:
            btn = QPushButton(action["label"])
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    font-size: 14px;
                    color: {self.theme.primary.name()};
                }}
                QPushButton:hover {{
                    background-color: #f8f9fa;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
            """)
            
            icon = SvgIcon(ICONS.get(action["icon"], ""), self.theme.secondary)
            
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(icon)
            btn_layout.addWidget(QLabel(action["label"]))
            btn_layout.addStretch()
            
            btn.setLayout(btn_layout)
            quick_layout.addWidget(btn)
        
        quick_actions.setLayout(quick_layout)
        top_layout.addWidget(quick_actions, 1)
        
        top_content.setLayout(top_layout)
        content_splitter.addWidget(top_content)
        
        # Class performance and system status
        bottom_content = QWidget()
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(15)
        
        # Class performance
        class_performance = QWidget()
        class_performance.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 20px;
        """)
        
        class_layout = QVBoxLayout()
        class_layout.setContentsMargins(0, 0, 0, 0)
        class_layout.setSpacing(15)
        
        class_title = QLabel("Class Performance Overview")
        class_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.primary.name()};
        """)
        
        class_layout.addWidget(class_title)
        
        classes = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "S1", "S2", "S3", "S4"]
        
        for class_name in classes:
            item = QWidget()
            item.setStyleSheet("""
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 12px;
            """)
            
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(10)
            
            class_label = QLabel(f"Class {class_name}")
            class_label.setStyleSheet("font-weight: 500;")
            
            student_count = QLabel("(25 students)")
            student_count.setStyleSheet("font-size: 13px; color: #666;")
            
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(75)  # Example value
            progress.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    height: 8px;
                    border-radius: 4px;
                    background-color: #e9ecef;
                }}
                QProgressBar::chunk {{
                    border-radius: 4px;
                    background-color: {self.theme.success.name()};
                }}
            """)
            
            percent = QLabel("75%")
            percent.setStyleSheet("font-size: 13px; font-weight: 500;")
            
            item_layout.addWidget(class_label)
            item_layout.addWidget(student_count)
            item_layout.addWidget(progress)
            item_layout.addWidget(percent)
            
            item.setLayout(item_layout)
            class_layout.addWidget(item)
        
        class_performance.setLayout(class_layout)
        bottom_layout.addWidget(class_performance, 1)
        
        # System status
        system_status = QWidget()
        system_status.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 20px;
        """)
        
        system_layout = QVBoxLayout()
        system_layout.setContentsMargins(0, 0, 0, 0)
        system_layout.setSpacing(15)
        
        system_title = QLabel("System Status")
        system_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.primary.name()};
        """)
        
        system_layout.addWidget(system_title)
        
        status_items = [
            {"label": "Database Connection", "status": "Connected", "icon": "database", "color": "#10B981"},
            {"label": "License Status", "status": "Active", "icon": "shield", "color": "#10B981"},
            {"label": "Cloud Sync", "status": "Disabled", "icon": "cloud", "color": "#F59E0B"},
            {"label": "Local Storage", "status": "Healthy", "icon": "hard_drive", "color": "#10B981"},
            {"label": "Last Backup", "status": "2 days ago", "icon": "refresh_cw", "color": "#F4A261"},
        ]
        
        for item in status_items:
            status_item = QWidget()
            status_item.setStyleSheet("""
                border: 1px solid #eee;
                border-radius: 8px;
                padding: 12px;
            """)
            
            status_layout = QHBoxLayout()
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setSpacing(10)
            
            icon = SvgIcon(ICONS.get(item["icon"], ""), QColor(item["color"]))
            
            label = QLabel(item["label"])
            label.setStyleSheet("font-weight: 500;")
            
            status = QLabel(item["status"])
            status.setStyleSheet(f"color: {item['color']};")
            
            status_layout.addWidget(icon)
            status_layout.addWidget(label)
            status_layout.addStretch()
            status_layout.addWidget(status)
            
            status_item.setLayout(status_layout)
            system_layout.addWidget(status_item)
        
        system_status.setLayout(system_layout)
        bottom_layout.addWidget(system_status, 1)
        
        bottom_content.setLayout(bottom_layout)
        content_splitter.addWidget(bottom_content)
        
        layout.addWidget(content_splitter)
        self.setLayout(layout)

class StudentsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = Theme()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)
        
        title = QLabel("Students Management")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {self.theme.primary.name()};
        """)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Action buttons
        import_btn = QPushButton("Import")
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 16px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                color: {self.theme.primary.name()};
            }}
            QPushButton:hover {{
                background-color: #f8f9fa;
            }}
        """)
        
        export_btn = QPushButton("Export")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 16px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                color: {self.theme.primary.name()};
            }}
            QPushButton:hover {{
                background-color: #f8f9fa;
            }}
        """)
        
        add_btn = QPushButton("Add Student")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
                color: white;
                background-color: {self.theme.secondary.name()};
            }}
            QPushButton:hover {{
                background-color: {self.theme.secondary.darker(110).name()};
            }}
        """)
        
        header_layout.addWidget(import_btn)
        header_layout.addWidget(export_btn)
        header_layout.addWidget(add_btn)
        header.setLayout(header_layout)
        
        layout.addWidget(header)
        
        # Search and filter
        filter_widget = QWidget()
        filter_widget.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 15px;
        """)
        
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(15)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search by name or student ID...")
        search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px 10px 35px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
            }
        """)
        
        # Add search icon
        search_icon = QLabel()
        search_icon.setPixmap(SvgIcon(ICONS.get("search", ""), self.theme.primary).pixmap(QSize(16, 16)))
        search_icon.setStyleSheet("margin-left: 10px;")
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(search_icon)
        search_layout.addWidget(search_input)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        search_widget = QWidget()
        search_widget.setLayout(search_layout)
        
        class_filter = QComboBox()
        class_filter.addItems(["All Classes", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "S1", "S2", "S3", "S4"])
        class_filter.setStyleSheet("""
            QComboBox {
                padding: 10px 15px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
            }
        """)
        
        filter_layout.addWidget(search_widget, 1)
        filter_layout.addWidget(class_filter)
        filter_widget.setLayout(filter_layout)
        
        layout.addWidget(filter_widget)
        
        # Students table
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border-radius: 8px;
                border: none;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 12px;
                font-size: 13px;
                font-weight: 500;
                color: #666;
                border: none;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #eee;
            }
        """)
        
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Student", "Class", "Performance", "Attendance", "Actions"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Add sample data
        table.setRowCount(10)
        for i in range(10):
            # Student column
            student_widget = QWidget()
            student_layout = QHBoxLayout()
            student_layout.setContentsMargins(0, 0, 0, 0)
            student_layout.setSpacing(10)
            
            avatar = QLabel()
            avatar.setFixedSize(40, 40)
            avatar.setStyleSheet(f"""
                background-color: {self.theme.secondary.name()};
                border-radius: 20px;
                color: white;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
            """)
            avatar.setText("NS" if i % 2 == 0 else "MD")
            
            name = QLabel("Nakamya Sarah" if i % 2 == 0 else "Musoke David")
            name.setStyleSheet("font-weight: 500;")
            
            id_label = QLabel(f"ID: {1000 + i}")
            id_label.setStyleSheet("font-size: 12px; color: #666;")
            
            text_layout = QVBoxLayout()
            text_layout.addWidget(name)
            text_layout.addWidget(id_label)
            
            student_layout.addWidget(avatar)
            student_layout.addLayout(text_layout)
            student_layout.addStretch()
            
            student_widget.setLayout(student_layout)
            table.setCellWidget(i, 0, student_widget)
            
            # Class column
            class_item = QTableWidgetItem(f"P{7 - (i % 3)}" if i < 7 else f"S{4 - (i % 3)}")
            table.setItem(i, 1, class_item)
            
            # Performance column
            performance_widget = QLabel()
            performance_widget.setAlignment(Qt.AlignCenter)
            performance_widget.setStyleSheet("""
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
                color: white;
                background-color: #10B981;
            """)
            performance_widget.setText("A" if i % 3 == 0 else "B" if i % 3 == 1 else "C")
            table.setCellWidget(i, 2, performance_widget)
            
            # Attendance column
            attendance_widget = QWidget()
            attendance_layout = QHBoxLayout()
            attendance_layout.setContentsMargins(0, 0, 0, 0)
            attendance_layout.setSpacing(5)
            
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(90 - (i * 2))
            progress.setStyleSheet("""
                QProgressBar {
                    border: none;
                    height: 6px;
                    border-radius: 3px;
                    background-color: #e9ecef;
                }
                QProgressBar::chunk {
                    border-radius: 3px;
                    background-color: #10B981;
                }
            """)
            
            percent = QLabel(f"{90 - (i * 2)}%")
            percent.setStyleSheet("font-size: 12px;")
            
            attendance_layout.addWidget(progress)
            attendance_layout.addWidget(percent)
            attendance_layout.addStretch()
            
            attendance_widget.setLayout(attendance_layout)
            table.setCellWidget(i, 3, attendance_widget)
            
            # Actions column
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(5)
            
            edit_btn = QToolButton()
            edit_btn.setIcon(QIcon(SvgIcon(ICONS.get("edit", ""), self.theme.primary).pixmap(QSize(16, 16))))
            edit_btn.setStyleSheet("border: none;")
            edit_btn.setToolTip("Edit student")
            
            report_btn = QToolButton()
            report_btn.setIcon(QIcon(SvgIcon(ICONS.get("file_text", ""), QColor("#10B981")).pixmap(QSize(16, 16))))
            report_btn.setStyleSheet("border: none;")
            report_btn.setToolTip("Generate report")
            
            view_btn = QToolButton()
            view_btn.setIcon(QIcon(SvgIcon(ICONS.get("eye", ""), QColor("#8B5CF6")).pixmap(QSize(16, 16))))
            view_btn.setStyleSheet("border: none;")
            view_btn.setToolTip("View details")
            
            delete_btn = QToolButton()
            delete_btn.setIcon(QIcon(SvgIcon(ICONS.get("trash_2", ""), QColor("#EF4444")).pixmap(QSize(16, 16))))
            delete_btn.setStyleSheet("border: none;")
            delete_btn.setToolTip("Delete student")
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(report_btn)
            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()
            
            actions_widget.setLayout(actions_layout)
            table.setCellWidget(i, 4, actions_widget)
        
        layout.addWidget(table)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme = Theme()
        self.notification_manager = NotificationManager(self)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Marka - School Management System")
        self.setMinimumSize(1200, 800)
        
        # Apply theme
        self.theme.apply_to_widget(self)
        
        # Main layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Main content
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Header
        self.header = QWidget()
        self.header.setStyleSheet("""
            background-color: white;
            border-bottom: 1px solid #eee;
            padding: 15px 20px;
        """)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(20)
        
        # Left side - title and breadcrumb
        title_widget = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(15)
        
        menu_btn = QToolButton()
        menu_btn.setIcon(QIcon(SvgIcon(ICONS.get("menu", ""), self.theme.primary).pixmap(QSize(20, 20))))
        menu_btn.setStyleSheet("border: none;")
        
        title = QLabel("Dashboard")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.primary.name()};
        """)
        
        subtitle = QLabel("Overview of your school management system")
        subtitle.setStyleSheet("font-size: 14px; color: #666;")
        
        title_layout.addWidget(menu_btn)
        
        text_layout = QVBoxLayout()
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        
        title_layout.addLayout(text_layout)
        title_widget.setLayout(title_layout)
        
        header_layout.addWidget(title_widget)
        header_layout.addStretch()
        
        # Right side - user info
        user_widget = QWidget()
        user_layout = QHBoxLayout()
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(10)
        
        school_label = QLabel("Marka Primary School")
        school_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {self.theme.primary.name()};
        """)
        
        license_label = QLabel("Standard License • 250 Students")
        license_label.setStyleSheet("font-size: 12px; color: #666;")
        
        text_layout = QVBoxLayout()
        text_layout.addWidget(school_label)
        text_layout.addWidget(license_label)
        text_layout.setAlignment(Qt.AlignRight)
        
        avatar = QLabel()
        avatar.setFixedSize(32, 32)
        avatar.setStyleSheet(f"""
            background-color: {self.theme.secondary.name()};
            border-radius: 16px;
            color: white;
            qproperty-alignment: AlignCenter;
        """)
        avatar.setText("A")
        
        user_layout.addLayout(text_layout)
        user_layout.addWidget(avatar)
        user_widget.setLayout(user_layout)
        
        header_layout.addWidget(user_widget)
        self.header.setLayout(header_layout)
        
        content_layout.addWidget(self.header)
        
        # Main content area
        self.stacked_widget = QStackedWidget()
        
        # Add views
        self.dashboard_view = DashboardView()
        self.students_view = StudentsView()
        
        self.stacked_widget.addWidget(self.dashboard_view)
        self.stacked_widget.addWidget(self.students_view)
        
        content_layout.addWidget(self.stacked_widget)
        content_widget.setLayout(content_layout)
        
        main_layout.addWidget(content_widget, 1)
        main_widget.setLayout(main_layout)
        
        self.setCentralWidget(main_widget)
        
        # Connect signals
        menu_btn.clicked.connect(self.toggle_sidebar)
        
        # Setup notification system
        self.notification_manager.show_notification.connect(self.show_notification)
        
    def toggle_sidebar(self):
        current_width = self.sidebar.width()
        if current_width > 50:
            self.sidebar.setFixedWidth(50)
        else:
            self.sidebar.setFixedWidth(250)
    
    def show_notification(self, message, type="success"):
        # Create notification widget
        notification = QWidget()
        notification.setStyleSheet(f"""
            background-color: {"#10B981" if type == "success" else 
                              "#EF4444" if type == "error" else 
                              "#F59E0B" if type == "warning" else "#3B82F6"};
            border-radius: 8px;
            padding: 12px 16px;
            color: white;
        """)
        
        notification_layout = QHBoxLayout()
        notification_layout.setContentsMargins(0, 0, 0, 0)
        notification_layout.setSpacing(10)
        
        icon = SvgIcon(ICONS.get("check_circle" if type == "success" else "alert_circle", ""), QColor("#FFFFFF"))
        
        label = QLabel(message)
        label.setStyleSheet("font-size: 14px;")
        
        notification_layout.addWidget(icon)
        notification_layout.addWidget(label)
        notification_layout.addStretch()
        
        notification.setLayout(notification_layout)
        
        # Add to overlay layout
        if not hasattr(self, "notification_overlay"):
            self.notification_overlay = QWidget(self)
            self.notification_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
            overlay_layout = QVBoxLayout()
            overlay_layout.setContentsMargins(20, 20, 20, 20)
            overlay_layout.setSpacing(10)
            overlay_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
            self.notification_overlay.setLayout(overlay_layout)
            self.notification_overlay.setGeometry(0, 0, self.width(), self.height())
        
        self.notification_overlay.layout().addWidget(notification)
        self.notification_overlay.raise_()
        self.notification_overlay.show()
        
        # Animate the notification
        animation = QPropertyAnimation(notification, b"pos")
        animation.setDuration(300)
        animation.setEasingCurve(QEasingCurve.OutQuad)
        animation.setStartValue(QPoint(self.width(), 20))
        animation.setEndValue(QPoint(self.width() - notification.width() - 40, 20))
        animation.start()
        
        # Auto-close after delay
        QTimer.singleShot(3000, lambda: self.close_notification(notification))
    
    def close_notification(self, notification):
        animation = QPropertyAnimation(notification, b"opacity")
        animation.setDuration(300)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.finished.connect(lambda: notification.deleteLater())
        animation.start()
    
    def resizeEvent(self, event):
        if hasattr(self, "notification_overlay"):
            self.notification_overlay.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply material theme
    apply_stylesheet(app, theme='light_blue.xml')
    
    window = MainWindow()
    window.show()
    
    # Show welcome notification
    QTimer.singleShot(1000, lambda: window.notification_manager.show("Welcome to Marka School Management System"))
    
    sys.exit(app.exec())