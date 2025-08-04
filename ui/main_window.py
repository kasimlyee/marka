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
      "BookOpen": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>""",
    "Users": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>""",
    "FileText": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>""",
    "Settings": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>""",
    "BarChart3": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 20V10"></path><path d="M12 20V4"></path><path d="M6 20v-6"></path></svg>""",
    "Upload": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>""",
    "Download": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>""",
    "Plus": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>""",
    "Search": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>""",
    "Filter": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>""",
    "Edit": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>""",
    "Trash2": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>""",
    "Save": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>""",
    "X": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>""",
    "CheckCircle": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>""",
    "AlertCircle": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>""",
    "Menu": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>""",
    "User": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>""",
    "GraduationCap": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg>""",
    "Key": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>""",
    "Shield": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>""",
    "Database": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>""",
    "Printer": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>""",
    "Eye": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>""",
    "Calendar": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>""",
    "Award": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>""",
    "TrendingUp": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>""",
    "FileCheck": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M9 15l2 2 4-4"></path></svg>""",
    "Copy": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>""",
    "RefreshCw": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>""",
    "Lock": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>""",
    "Unlock": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>""",
    "Cloud": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>""",
    "HardDrive": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="12" x2="2" y2="12"></line><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path><line x1="6" y1="16" x2="6.01" y2="16"></line><line x1="10" y1="16" x2="10.01" y2="16"></line></svg>""",
    "UserPlus": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>""",
    "BookPlus": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path><line x1="12" y1="7" x2="12" y2="13"></line><line x1="15" y1="10" x2="9" y2="10"></line></svg>""",
    "Loader2": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>""",
    
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
    
    def get_pixmap(self, size):
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        self.renderer.render(painter)
        if self.color:
            # Recolor the icon
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), self.color)
        return pixmap

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
        search_icon.setPixmap(SvgIcon(ICONS.get("search", ""), self.theme.primary).get_pixmap(QSize(16, 16)))
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
            edit_btn.setIcon(QIcon(SvgIcon(ICONS.get("edit", ""), self.theme.primary).get_pixmap(QSize(16, 16))))
            edit_btn.setStyleSheet("border: none;")
            edit_btn.setToolTip("Edit student")
            
            report_btn = QToolButton()
            report_btn.setIcon(QIcon(SvgIcon(ICONS.get("file_text", ""), QColor("#10B981")).get_pixmap(QSize(16, 16))))
            report_btn.setStyleSheet("border: none;")
            report_btn.setToolTip("Generate report")
            
            view_btn = QToolButton()
            view_btn.setIcon(QIcon(SvgIcon(ICONS.get("eye", ""), QColor("#8B5CF6")).get_pixmap(QSize(16, 16))))
            view_btn.setStyleSheet("border: none;")
            view_btn.setToolTip("View details")
            
            delete_btn = QToolButton()
            delete_btn.setIcon(QIcon(SvgIcon(ICONS.get("trash_2", ""), QColor("#EF4444")).get_pixmap(QSize(16, 16))))
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
        menu_btn.setIcon(QIcon(SvgIcon(ICONS.get("menu", ""), self.theme.primary).get_pixmap(QSize(20, 20))))
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