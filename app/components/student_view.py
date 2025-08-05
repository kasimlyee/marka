import os
import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout,QLineEdit, QButtonGroup,QProgressBar, QHBoxLayout, QLabel, QAbstractItemView, QTableWidget, QTableWidgetItem, QPushButton, QComboBox, QHeaderView, QCheckBox, QFileDialog, QMessageBox, QSizePolicy, QToolButton
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor, QIcon
from ..services.data_service import DataService
from ..components.button import Button
from ..icons import ICONS, SvgIcon
from ..models.data_models import Student

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import setup_logging

logger = setup_logging(__name__)

class StudentsView(QWidget):
    """Advanced students management view with filtering, sorting, and bulk operations"""
    
    def __init__(self, data_service: DataService, theme, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.theme = theme
        self.selected_students = []
        self.setup_ui()
        
        # Connect to data updates
        self.data_service.data_updated.connect(self.refresh_data)
    
    def setup_ui(self):
        """Setup the students view UI"""
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(24, 24, 24, 24)
            layout.setSpacing(20)
            
            # Header with title and actions
            self.create_header(layout)
            
            # Filters and search
            self.create_filters(layout)
            
            # Students table
            self.create_students_table(layout)
            
            self.setLayout(layout)
            
        except Exception as e:
            logger.error(f"Error setting up students view: {e}")
    
    def create_header(self, parent_layout):
        """Create header section"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title section
        title_layout = QVBoxLayout()
        
        title = QLabel("Students Management")
        title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 600;
            color: {self.theme.primary.name()};
        """)
        
        subtitle = QLabel("Manage student records, performance, and generate reports")
        subtitle.setStyleSheet("font-size: 14px; color: #6B7280;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        
        # Bulk actions (initially hidden)
        self.bulk_actions = QWidget()
        bulk_layout = QHBoxLayout()
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.setSpacing(8)
        
        bulk_delete = Button("Delete Selected", "Trash2")
        bulk_delete.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        
        bulk_export = Button("Export Selected", "Download")
        bulk_export.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        
        bulk_layout.addWidget(bulk_delete)
        bulk_layout.addWidget(bulk_export)
        self.bulk_actions.setLayout(bulk_layout)
        self.bulk_actions.hide()
        
        # Regular actions
        import_btn = Button("Import Students", "Upload")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #F9FAFB;
                border-color: #9CA3AF;
            }
        """)
        
        export_btn = Button("Export All", "Download")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #F9FAFB;
                border-color: #9CA3AF;
            }
        """)
        
        add_btn = Button("Add Student", "Plus")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.secondary.name()};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.theme.secondary.darker(110).name()};
            }}
        """)
        
        actions_layout.addWidget(self.bulk_actions)
        actions_layout.addWidget(import_btn)
        actions_layout.addWidget(export_btn)
        actions_layout.addWidget(add_btn)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(actions_layout)
        
        header_widget.setLayout(header_layout)
        parent_layout.addWidget(header_widget)
    
    def create_filters(self, parent_layout):
        """Create filters and search section"""
        filters_widget = QWidget()
        filters_widget.setStyleSheet("""
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 20px;
        """)
        
        filters_layout = QHBoxLayout()
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(16)
        
        # Search input
        search_container = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)
        
        search_icon = SvgIcon(ICONS["Search"], QColor("#9CA3AF"), QSize(20, 20))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, ID, or class...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 14px;
                min-width: 300px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                outline: none;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        search_container.setLayout(search_layout)
        
        # Class filter
        self.class_filter = QComboBox()
        self.class_filter.addItems([
            "All Classes", "P1", "P2", "P3", "P4", "P5", "P6", "P7",
            "S1", "S2", "S3", "S4", "S5", "S6"
        ])
        self.class_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 14px;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6B7280;
            }
        """)
        self.class_filter.currentTextChanged.connect(self.on_filter_changed)
        
        # Performance filter
        self.performance_filter = QComboBox()
        self.performance_filter.addItems(["All Grades", "A", "B+", "B", "C+", "C", "D+", "D", "F"])
        self.performance_filter.setStyleSheet(self.class_filter.styleSheet())
        self.performance_filter.currentTextChanged.connect(self.on_filter_changed)
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Students", "Active", "Inactive", "Graduated"])
        self.status_filter.setStyleSheet(self.class_filter.styleSheet())
        self.status_filter.currentTextChanged.connect(self.on_filter_changed)
        
        # Clear filters button
        clear_btn = QPushButton("Clear Filters")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6B7280;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F9FAFB;
                color: #374151;
            }
        """)
        clear_btn.clicked.connect(self.clear_filters)
        
        filters_layout.addWidget(search_container)
        filters_layout.addWidget(QLabel("Class:"))
        filters_layout.addWidget(self.class_filter)
        filters_layout.addWidget(QLabel("Grade:"))
        filters_layout.addWidget(self.performance_filter)
        filters_layout.addWidget(QLabel("Status:"))
        filters_layout.addWidget(self.status_filter)
        filters_layout.addWidget(clear_btn)
        filters_layout.addStretch()
        
        filters_widget.setLayout(filters_layout)
        parent_layout.addWidget(filters_widget)
    
    def create_students_table(self, parent_layout):
        """Create the students table"""
        table_container = QWidget()
        table_container.setStyleSheet("""
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
        """)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Table header with selection controls
        table_header = QWidget()
        table_header.setStyleSheet("""
            background-color: #F9FAFB;
            border-bottom: 1px solid #E5E7EB;
            padding: 16px 24px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Selection controls
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: 500;
                color: #374151;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #D1D5DB;
            }
            QCheckBox::indicator:checked {
                background-color: #6366F1;
                border-color: #6366F1;
            }
        """)
        self.select_all_cb.stateChanged.connect(self.on_select_all_changed)
        
        # Results count
        self.results_label = QLabel()
        self.results_label.setStyleSheet("font-size: 14px; color: #6B7280;")
        
        # View options
        view_options = QWidget()
        view_layout = QHBoxLayout()
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(8)
        
        # Table/Grid view toggle
        table_view_btn = QPushButton("Table")
        table_view_btn.setCheckable(True)
        table_view_btn.setChecked(True)
        table_view_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:checked {
                background-color: #6366F1;
            }
            QPushButton:!checked {
                background-color: transparent;
                color: #6B7280;
                border: 1px solid #D1D5DB;
            }
        """)
        
        grid_view_btn = QPushButton("Grid")
        grid_view_btn.setCheckable(True)
        grid_view_btn.setStyleSheet(table_view_btn.styleSheet())
        
        view_group = QButtonGroup()
        view_group.addButton(table_view_btn)
        view_group.addButton(grid_view_btn)
        
        view_layout.addWidget(table_view_btn)
        view_layout.addWidget(grid_view_btn)
        view_options.setLayout(view_layout)
        
        header_layout.addWidget(self.select_all_cb)
        header_layout.addWidget(self.results_label)
        header_layout.addStretch()
        header_layout.addWidget(view_options)
        
        table_header.setLayout(header_layout)
        container_layout.addWidget(table_header)
        
        # Create the actual table
        self.students_table = QTableWidget()
        self.students_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #F3F4F6;
                background-color: white;
                border: none;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #F3F4F6;
            }
            QTableWidget::item:selected {
                background-color: #EEF2FF;
                color: #1E40AF;
            }
            QHeaderView::section {
                background-color: #F9FAFB;
                color: #374151;
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-bottom: 1px solid #E5E7EB;
                padding: 12px 8px;
                text-align: left;
            }
            QScrollBar:vertical {
                background-color: #F3F4F6;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #D1D5DB;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9CA3AF;
            }
        """)
        
        # Setup table structure
        self.students_table.setColumnCount(7)
        headers = ["", "Student", "Class", "Performance", "Attendance", "Last Activity", "Actions"]
        self.students_table.setHorizontalHeaderLabels(headers)
        
        # Configure table behavior
        self.students_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.students_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.students_table.setAlternatingRowColors(False)
        self.students_table.verticalHeader().setVisible(False)
        self.students_table.setSortingEnabled(True)
        
        # Configure column widths
        header = self.students_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Checkbox column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Student column
        header.setSectionResizeMode(2, QHeaderView.Fixed)   # Class column
        header.setSectionResizeMode(3, QHeaderView.Fixed)   # Performance column
        header.setSectionResizeMode(4, QHeaderView.Fixed)   # Attendance column
        header.setSectionResizeMode(5, QHeaderView.Fixed)   # Last Activity column
        
        self.students_table.setColumnWidth(0, 50)   # Checkbox
        self.students_table.setColumnWidth(2, 80)   # Class
        self.students_table.setColumnWidth(3, 100)  # Performance
        self.students_table.setColumnWidth(4, 100)  # Attendance
        self.students_table.setColumnWidth(5, 120)  # Last Activity
        
        container_layout.addWidget(self.students_table)
        
        # Table footer with pagination
        table_footer = QWidget()
        table_footer.setStyleSheet("""
            background-color: #F9FAFB;
            border-top: 1px solid #E5E7EB;
            padding: 12px 24px;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
        """)
        
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Items per page
        per_page_layout = QHBoxLayout()
        per_page_layout.setSpacing(8)
        
        per_page_label = QLabel("Items per page:")
        per_page_label.setStyleSheet("font-size: 13px; color: #6B7280;")
        
        self.per_page_combo = QComboBox()
        self.per_page_combo.addItems(["10", "25", "50", "100"])
        self.per_page_combo.setCurrentText("25")
        self.per_page_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 60px;
            }
        """)
        
        per_page_layout.addWidget(per_page_label)
        per_page_layout.addWidget(self.per_page_combo)
        
        # Pagination info
        self.pagination_info = QLabel()
        self.pagination_info.setStyleSheet("font-size: 13px; color: #6B7280;")
        
        # Pagination controls
        pagination_controls = QWidget()
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 0, 0, 0)
        pagination_layout.setSpacing(4)
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                color: #374151;
            }
            QPushButton:hover:enabled {
                background-color: #F9FAFB;
            }
            QPushButton:disabled {
                color: #9CA3AF;
                border-color: #F3F4F6;
            }
        """)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setStyleSheet(self.prev_btn.styleSheet())
        
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.next_btn)
        pagination_controls.setLayout(pagination_layout)
        
        footer_layout.addLayout(per_page_layout)
        footer_layout.addStretch()
        footer_layout.addWidget(self.pagination_info)
        footer_layout.addWidget(pagination_controls)
        
        table_footer.setLayout(footer_layout)
        container_layout.addWidget(table_footer)
        
        table_container.setLayout(container_layout)
        parent_layout.addWidget(table_container)
        
        # Load initial data
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh the students table data"""
        try:
            # Get filtered students
            search_term = self.search_input.text() if hasattr(self, 'search_input') else ""
            class_filter = self.class_filter.currentText() if hasattr(self, 'class_filter') else "All Classes"
            
            students = self.data_service.get_students()
            
            # Update results count
            if hasattr(self, 'results_label'):
                self.results_label.setText(f"Showing {len(students)} students")
            
            # Update pagination info
            if hasattr(self, 'pagination_info'):
                self.pagination_info.setText(f"1-{min(25, len(students))} of {len(students)}")
            
            # Clear existing rows
            self.students_table.setRowCount(0)
            
            # Add student rows
            for row, student in enumerate(students[:25]):  # Limit to 25 for pagination
                self.add_student_row(row, student)
            
            logger.info(f"Refreshed students table with {len(students)} students")
            
        except Exception as e:
            logger.error(f"Error refreshing students data: {e}")
    
    def add_student_row(self, row: int, student: Student):
        """Add a single student row to the table"""
        try:
            self.students_table.insertRow(row)
            
            # Checkbox column
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout()
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            
            checkbox = QCheckBox()
            checkbox.setObjectName(f"cb_{student.id}")
            checkbox.stateChanged.connect(self.on_student_selection_changed)
            
            checkbox_layout.addWidget(checkbox)
            checkbox_widget.setLayout(checkbox_layout)
            self.students_table.setCellWidget(row, 0, checkbox_widget)
            
            # Student info column
            student_widget = self.create_student_info_widget(student)
            self.students_table.setCellWidget(row, 1, student_widget)
            
            # Class column
            class_item = QTableWidgetItem(student.class_name)
            class_item.setData(Qt.UserRole, student)
            self.students_table.setItem(row, 2, class_item)
            
            # Performance column
            performance_widget = self.create_performance_widget(student)
            self.students_table.setCellWidget(row, 3, performance_widget)
            
            # Attendance column
            attendance_widget = self.create_attendance_widget(student)
            self.students_table.setCellWidget(row, 4, attendance_widget)
            
            # Last activity column
            last_activity = student.registration_date.strftime("%b %d, %Y")
            activity_item = QTableWidgetItem(last_activity)
            self.students_table.setItem(row, 5, activity_item)
            
            # Actions column
            actions_widget = self.create_actions_widget(student)
            self.students_table.setCellWidget(row, 6, actions_widget)
            
        except Exception as e:
            logger.error(f"Error adding student row: {e}")
    
    def create_student_info_widget(self, student: Student):
        """Create student information widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Avatar
        avatar = QLabel()
        avatar.setFixedSize(40, 40)
        avatar.setStyleSheet(f"""
            background-color: {self.theme.secondary.name()};
            color: white;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            qproperty-alignment: AlignCenter;
        """)
        avatar.setText(student.name.split()[0][0] + student.name.split()[-1][0])
        
        # Student details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(2)
        
        name_label = QLabel(student.name)
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #111827;")
        
        id_label = QLabel(f"ID: {student.id}")
        id_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        
        contact_label = QLabel(student.guardian_contact)
        contact_label.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        
        details_layout.addWidget(name_label)
        details_layout.addWidget(id_label)
        details_layout.addWidget(contact_label)
        
        layout.addWidget(avatar)
        layout.addLayout(details_layout)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_performance_widget(self, student: Student):
        """Create performance indicator widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignCenter)
        
        # Grade badge
        grade_badge = QLabel(student.performance_grade)
        grade_badge.setAlignment(Qt.AlignCenter)
        grade_badge.setFixedSize(32, 32)
        
        # Color based on grade
        grade_colors = {
            "A": "#10B981", "B+": "#059669", "B": "#F59E0B",
            "C+": "#EF4444", "C": "#DC2626", "D+": "#991B1B",
            "D": "#7F1D1D", "F": "#450A0A"
        }
        
        color = grade_colors.get(student.performance_grade, "#6B7280")
        grade_badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 700;
        """)
        
        # Average score
        score_label = QLabel(f"{student.average_score:.1f}%")
        score_label.setStyleSheet("font-size: 11px; color: #6B7280; margin-top: 4px;")
        score_label.setAlignment(Qt.AlignCenter)
        
        widget_layout = QVBoxLayout()
        widget_layout.setSpacing(2)
        widget_layout.addWidget(grade_badge)
        widget_layout.addWidget(score_label)
        
        layout.addLayout(widget_layout)
        widget.setLayout(layout)
        return widget
    
    def create_attendance_widget(self, student: Student):
        """Create attendance indicator widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Attendance percentage
        percentage_label = QLabel(f"{student.attendance_percentage:.1f}%")
        percentage_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #111827;")
        percentage_label.setAlignment(Qt.AlignCenter)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(student.attendance_percentage))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(6)
        
        # Color based on attendance
        if student.attendance_percentage >= 90:
            color = "#10B981"
        elif student.attendance_percentage >= 75:
            color = "#F59E0B"
        else:
            color = "#EF4444"
        
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: #F3F4F6;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {color};
            }}
        """)
        
        layout.addWidget(percentage_label)
        layout.addWidget(progress_bar)
        
        widget.setLayout(layout)
        return widget
    
    def create_actions_widget(self, student: Student):
        """Create actions widget for student row"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Action buttons
        actions = [
            {"icon": "Eye", "tooltip": "View Details", "color": "#6366F1"},
            {"icon": "Edit", "tooltip": "Edit Student", "color": "#059669"},
            {"icon": "FileText", "tooltip": "Generate Report", "color": "#DC2626"},
            {"icon": "Trash2", "tooltip": "Delete Student", "color": "#EF4444"}
        ]
        
        for action in actions:
            btn = QToolButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f"""
                QToolButton {{
                    border: none;
                    border-radius: 6px;
                    background-color: transparent;
                }}
                QToolButton:hover {{
                    background-color: {action['color']}20;
                }}
            """)
            
            # Set icon
            icon_widget = SvgIcon(ICONS[action["icon"]], QColor(action["color"]), QSize(16, 16))
            btn.setIcon(QIcon(icon_widget.get_pixmap(QSize(16, 16))))
            btn.setToolTip(action["tooltip"])
            btn.setCursor(Qt.PointingHandCursor)
            
            # Connect action
            if action["icon"] == "Eye":
                btn.clicked.connect(lambda checked, s=student: self.view_student(s))
            elif action["icon"] == "Edit":
                btn.clicked.connect(lambda checked, s=student: self.edit_student(s))
            elif action["icon"] == "FileText":
                btn.clicked.connect(lambda checked, s=student: self.generate_report(s))
            elif action["icon"] == "Trash2":
                btn.clicked.connect(lambda checked, s=student: self.delete_student(s))
            
            layout.addWidget(btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    # Event handlers
    def on_search_changed(self):
        """Handle search input changes"""
        # Debounce search to avoid too many requests
        if hasattr(self, 'search_timer'):
            self.search_timer.stop()
        
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.refresh_data)
        self.search_timer.start(300)  # 300ms delay
    
    def on_filter_changed(self):
        """Handle filter changes"""
        self.refresh_data()
    
    def clear_filters(self):
        """Clear all filters"""
        self.search_input.clear()
        self.class_filter.setCurrentText("All Classes")
        self.performance_filter.setCurrentText("All Grades")
        self.status_filter.setCurrentText("All Students")
    
    def on_select_all_changed(self, state):
        """Handle select all checkbox"""
        for row in range(self.students_table.rowCount()):
            checkbox_widget = self.students_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(state == Qt.Checked)
    
    def on_student_selection_changed(self):
        """Handle individual student selection"""
        selected_count = 0
        for row in range(self.students_table.rowCount()):
            checkbox_widget = self.students_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
        
        # Show/hide bulk actions
        if selected_count > 0:
            self.bulk_actions.show()
        else:
            self.bulk_actions.hide()
        
        # Update select all checkbox
        if selected_count == 0:
            self.select_all_cb.setCheckState(Qt.Unchecked)
        elif selected_count == self.students_table.rowCount():
            self.select_all_cb.setCheckState(Qt.Checked)
        else:
            self.select_all_cb.setCheckState(Qt.PartiallyChecked)
    
    # Action methods
    def view_student(self, student: Student):
        """View student details"""
        logger.info(f"Viewing student: {student.name}")
        # TODO: Implement student detail view
    
    def edit_student(self, student: Student):
        """Edit student information"""
        logger.info(f"Editing student: {student.name}")
        # TODO: Implement student edit dialog
    
    def generate_report(self, student: Student):
        """Generate report for student"""
        logger.info(f"Generating report for student: {student.name}")
        # TODO: Implement report generation
    
    def delete_student(self, student: Student):
        """Delete student (with confirmation)"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {student.name}?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.data_service.delete_student(student.id):
                logger.info(f"Deleted student: {student.name}")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete student.")
