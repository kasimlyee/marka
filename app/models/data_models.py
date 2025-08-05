from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import List

class UserRole(Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"

class LicenseType(Enum):
    TRIAL = "trial"
    STANDARD = "standard"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class NotificationType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class Student:
    id: str
    name: str
    class_name: str
    performance_grade: str
    attendance_percentage: float
    registration_date: datetime
    guardian_contact: str
    subjects: List[str]
    average_score: float
    is_active: bool = True

@dataclass
class SystemMetrics:
    total_students: int
    active_classes: int
    average_performance: float
    high_performers: int
    database_status: str
    license_status: str
    cloud_sync_status: str
    storage_status: str
    last_backup: datetime
