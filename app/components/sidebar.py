from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from ..icons import ICONS, SvgIcon
class Sidebar(QWidget):
    def __init__(self, theme,parent=None):
        super().__init__(parent)
        self.theme = theme
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