import os
import sys

from PySide6.QtCore import QObject, Signal
from typing import List, Dict, Optional
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import setup_logging
from db.database_manager import DatabaseManager

logger = setup_logging(__name__)

class DataService(QObject):
    """Centralized data service for managing application data"""
    
    data_updated = Signal(str)  # Signal emitted when data changes
    
    def __init__(self):
        super().__init__()
        self._database_manager = DatabaseManager()
    
     # Student functions
    
    def get_students(self) -> List[Dict[str, str]]:
        """Get all students"""
        return self._database_manager.get_subjects()
    
    def get_student_by_id(self, student_id: int) -> Optional[Dict[str, str]]:
        """Get a student by ID"""
        return self._database_manager.get_student(student_id)
    
    def add_student(self, student: Dict[str, str]) -> None:
        """Add a new student"""
        self._database_manager.create_student(student)
        self.data_updated.emit("Student added")
    
    def update_student(self, student_id: int, updated_student: Dict[str, str]) -> None:
        """Update an existing student"""
        self._database_manager.update_student(student_id, updated_student)
        self.data_updated.emit("Student updated")
    
    def delete_student(self, student_id: int) -> None:
        """Delete a student"""
        self._database_manager.delete_student(student_id)
        self.data_updated.emit("Student deleted")
    
    # Setting functions
    
    def get_all_settings(self) -> List[Dict[str, str]]:
        """Get all settings"""
        return self._database_manager.get_all_settings()
    
    def get_setting_by_key(self, key: str) -> Optional[Dict[str, str]]:
        """Get a setting by key"""
        return self._database_manager.get_setting(key)
    
    def add_setting(self, setting: Dict[str, str]) -> None:
        """Add a new setting"""
        self._database_manager.add_setting(setting)
        self.data_updated.emit("Setting added")
    
    def update_setting(self, key: str, updated_setting: Dict[str, str]) -> None:
        """Update an existing setting"""
        self._database_manager.update_setting(key, updated_setting)
        self.data_updated.emit("Setting updated")
    
    def delete_setting(self, key: str) -> None:
        """Delete a setting"""
        self._database_manager.delete_setting(key)
        self.data_updated.emit("Setting deleted")
    
    # Subject functions
    
    def get_all_subjects(self) -> List[Dict[str, str]]:
        """Get all subjects"""
        return self._database_manager.get_subjects()
    
    def get_subject_by_id(self, subject_id: int) -> Optional[Dict[str, str]]:
        """Get a subject by ID"""
        return self._database_manager.get_subject(subject_id)
    
    def add_subject(self, subject: Dict[str, str]) -> None:
        """Add a new subject"""
        self._database_manager.add_subject(subject)
        self.data_updated.emit("Subject added")
    
    def update_subject(self, subject_id: int, updated_subject: Dict[str, str]) -> None:
        """Update an existing subject"""
        self._database_manager.update_subject(subject_id, updated_subject)
        self.data_updated.emit("Subject updated")
    
    def delete_subject(self, subject_id: int) -> None:
        """Delete a subject"""
        self._database_manager.delete_subject(subject_id)
        self.data_updated.emit("Subject deleted")
    
    # Grade functions
    
    def get_all_grades(self) -> List[Dict[str, str]]:
        """Get all grades"""
        return self._database_manager.get_all_grades()
    
    def get_grade_by_id(self, grade_id: int) -> Optional[Dict[str, str]]:
        """Get a grade by ID"""
        return self._database_manager.get_grade(grade_id)
    
    def add_grade(self, grade: Dict[str, str]) -> Dict[str, str]:
        """Add a new grade"""
        return self._database_manager.save_grade(grade)

    def get_metrics(self):
        pass
