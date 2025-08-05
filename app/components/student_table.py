from PySide6.QtCore import Qt, QModelIndex, QAbstractTableModel

class StudentTableModel(QAbstractTableModel):
    """Advanced table model for student data with sorting and filtering"""
    
    def __init__(self, data_service):
        super().__init__()
        self.data_service = data_service
        self._students = []  
        self._headers = ["Student", "Class", "Performance", "Attendance", "Subjects", "Actions"]
        self.refresh_data()
        
        # Connect to data updates
        self.data_service.data_updated.connect(self.on_data_updated)
    
    def refresh_data(self, class_filter: str = None, search_term: str = None):
        """Refresh the model data"""
        self.beginResetModel()
        self._students = self.data_service.get_students(class_filter, search_term)
        self.endResetModel()
    
    def on_data_updated(self, data_type: str):
        """Handle data updates"""
        if data_type == "students":
            self.refresh_data()
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._students)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._students):
            return None
        
        student = self._students[index.row()]
        column = index.column()
        
        if role == Qt.DisplayRole:
            if column == 0:  # Student
                return f"{student.name}\nID: {student.id}"
            elif column == 1:  # Class
                return student.class_name
            elif column == 2:  # Performance
                return student.performance_grade
            elif column == 3:  # Attendance
                return f"{student.attendance_percentage:.1f}%"
            elif column == 4:  # Subjects
                return f"{len(student.subjects)} subjects"
        
        elif role == Qt.UserRole:
            return student
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None
