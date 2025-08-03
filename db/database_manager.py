import os
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from uuid import uuid4
from PySide6.QtCore import QStandardPaths
import bcrypt
from cryptography.fernet import Fernet

class DatabaseManager:
    """
    A database manager for the Marka report card generator.
    Handles all database operations including initialization, schema management,
    CRUD operations, transactions, and maintenance.
    """
    
    def __init__(self):
        
        """
        Initialize a DatabaseManager instance.
        
        Sets up the instance with default values but does not connect to the
        database or initialize the database schema.
        """
        self.conn: Optional[sqlite3.Connection] = None
        self.db_path: Optional[Path] = None
        self.is_initialized: bool = False
        self.statements: Dict[str, sqlite3.Cursor] = {}
        self.encryption_key: bytes = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.logger = logging.getLogger('marka.database')
        
    def initialize(self) -> None:
        """
        Initialize the database connection and setup the schema.
        """
        try:
            # Set up database path
            data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = Path(data_dir) / 'marka_database.db'
            
            # Initialize database connection
            self.conn = sqlite3.connect(
                str(self.db_path),
                isolation_level=None,  # Autocommit mode
                check_same_thread=False  # Allow multiple threads to use the connection
            )
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            
            # Configure database
            self._configure_database()
            
            # Create tables and indexes
            self._create_tables()
            self._create_indexes()
            
            # Insert default data
            self._insert_default_data()
            
            # Create prepared statements
            self._create_prepared_statements()
            
            # Run integrity check
            self._run_integrity_check()
            
            self.is_initialized = True
            self.logger.info(f"Database initialized successfully at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise

    def _configure_database(self) -> None:
        """
        Configure database settings for performance and security.
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")
            
        # Performance optimizations
        self.conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
        self.conn.execute("PRAGMA synchronous = NORMAL")  # Balance between performance and safety
        self.conn.execute("PRAGMA cache_size = 10000")  # 10MB cache
        self.conn.execute("PRAGMA temp_store = MEMORY")  # Store temp tables in memory
        self.conn.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map
        self.conn.execute("PRAGMA page_size = 4096")  # Optimal page size
        self.conn.execute("PRAGMA auto_vacuum = INCREMENTAL")  # Automatic space recovery
        
        # Security settings
        self.conn.execute("PRAGMA secure_delete = ON")  # Secure deletion
        self.conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        
        # Register custom functions
        self.conn.create_function("uuid", 0, lambda: str(uuid4()))
        self.conn.create_function("encrypt", 1, self._encrypt_data)
        self.conn.create_function("decrypt", 1, self._decrypt_data)
        
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data using Fernet symmetric encryption."""
        if data is None:
            return None
        return self.cipher_suite.encrypt(data.encode()).decode()
        
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using Fernet symmetric encryption."""
        if encrypted_data is None:
            return None
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def _create_tables(self) -> None:
        """
        Create all necessary tables in the database.
        """
        schemas = [
            # Schools table
            """CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                phone TEXT,
                email TEXT,
                website TEXT,
                logo BLOB,
                motto TEXT,
                principal TEXT,
                founded TEXT,
                license_type TEXT DEFAULT 'Standard',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

            # Students table
            """CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                class_level TEXT NOT NULL,
                date_of_birth DATE,
                gender TEXT CHECK(gender IN ('Male', 'Female')),
                address TEXT,
                parent_name TEXT,
                parent_phone TEXT,
                parent_email TEXT,
                admission_date DATE,
                status TEXT DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive', 'Graduated', 'Transferred')),
                photo BLOB,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

            # Subjects table
            """CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE,
                class_level TEXT NOT NULL,
                is_core BOOLEAN DEFAULT 1,
                weight REAL DEFAULT 1.0,
                description TEXT,
                teacher_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

            # Grades table
            """CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                term TEXT NOT NULL CHECK(term IN ('term1', 'term2', 'term3')),
                academic_year TEXT NOT NULL,
                score REAL NOT NULL CHECK(score >= 0 AND score <= 100),
                grade_letter TEXT,
                remarks TEXT,
                teacher_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                UNIQUE(student_id, subject_id, term, academic_year)
            )""",

            # Attendance table
            """CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status TEXT CHECK(status IN ('Present', 'Absent', 'Late', 'Excused')) DEFAULT 'Present',
                term TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                remarks TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, date)
            )""",

            # Conduct table
            """CREATE TABLE IF NOT EXISTS conduct (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                term TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                behavior_grade TEXT CHECK(behavior_grade IN ('Excellent', 'Very Good', 'Good', 'Fair', 'Poor')),
                discipline_score INTEGER CHECK(discipline_score >= 1 AND discipline_score <= 5),
                comments TEXT,
                teacher_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, term, academic_year)
            )""",

            # Users table
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'teacher', 'staff')) DEFAULT 'teacher',
                is_active BOOLEAN DEFAULT 1,
                last_login DATETIME,
                failed_login_attempts INTEGER DEFAULT 0,
                account_locked_until DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

            # Settings table
            """CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                type TEXT DEFAULT 'string',
                description TEXT,
                is_encrypted BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

            # Reports table
            """CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                term TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                report_type TEXT NOT NULL,
                file_path TEXT,
                generated_by INTEGER,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (generated_by) REFERENCES users(id)
            )""",

            # Grading schemas table
            """CREATE TABLE IF NOT EXISTS grading_schemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT CHECK(type IN ('division', 'grade', 'points')) NOT NULL,
                class_levels TEXT NOT NULL, -- JSON array
                grade_ranges TEXT NOT NULL, -- JSON array
                is_active BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",

            # Audit logs table
            """CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                old_values TEXT, -- JSON
                new_values TEXT, -- JSON
                ip_address TEXT,
                user_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""",

            # Backups table
            """CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                size_bytes INTEGER,
                type TEXT CHECK(type IN ('manual', 'automatic', 'scheduled')) DEFAULT 'manual',
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )"""
        ]

        # Execute schema creation in a transaction
        with self.conn:
            for schema in schemas:
                self.conn.execute(schema)
    
    def _create_indexes(self) -> None:
        """
        Create indexes for performance optimization.
        """
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id)',
            'CREATE INDEX IF NOT EXISTS idx_students_class_level ON students(class_level)',
            'CREATE INDEX IF NOT EXISTS idx_students_status ON students(status)',
            'CREATE INDEX IF NOT EXISTS idx_grades_student_id ON grades(student_id)',
            'CREATE INDEX IF NOT EXISTS idx_grades_subject_id ON grades(subject_id)',
            'CREATE INDEX IF NOT EXISTS idx_grades_term_year ON grades(term, academic_year)',
            'CREATE INDEX IF NOT EXISTS idx_attendance_student_date ON attendance(student_id, date)',
            'CREATE INDEX IF NOT EXISTS idx_attendance_term_year ON attendance(term, academic_year)',
            'CREATE INDEX IF NOT EXISTS idx_conduct_student_term ON conduct(student_id, term, academic_year)',
            'CREATE INDEX IF NOT EXISTS idx_reports_student_term ON reports(student_id, term, academic_year)',
            'CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs(user_id, action)',
            'CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)',
            'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
            'CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)'
        ]

        with self.conn:
            for index in indexes:
                self.conn.execute(index)
    
    def _insert_default_data(self) -> None:
        """
        Insert default data into the database.
        """
        # Insert default grading schemas
        default_schemas = [
            {
                'name': 'UNEB Primary Leaving Examination',
                'type': 'division',
                'class_levels': json.dumps(['P7']),
                'grade_ranges': json.dumps([
                    {'grade': 'Division 1', 'minPercent': 90, 'maxAggregate': 12, 'color': '#10B981'},
                    {'grade': 'Division 2', 'minPercent': 75, 'maxAggregate': 23, 'color': '#3B82F6'},
                    {'grade': 'Division 3', 'minPercent': 60, 'maxAggregate': 29, 'color': '#F59E0B'},
                    {'grade': 'Division 4', 'minPercent': 50, 'maxAggregate': 34, 'color': '#EF4444'},
                    {'grade': 'Ungraded', 'minPercent': 0, 'maxAggregate': 99, 'color': '#6B7280'}
                ]),
                'is_active': 1
            },
            {
                'name': 'UNEB Uganda Certificate of Education',
                'type': 'grade',
                'class_levels': json.dumps(['S4']),
                'grade_ranges': json.dumps([
                    {'grade': 'A', 'minPercent': 85, 'color': '#10B981'},
                    {'grade': 'B', 'minPercent': 75, 'color': '#3B82F6'},
                    {'grade': 'C', 'minPercent': 65, 'color': '#F59E0B'},
                    {'grade': 'D', 'minPercent': 55, 'color': '#EF4444'},
                    {'grade': 'E', 'minPercent': 45, 'color': '#EF4444'},
                    {'grade': 'F', 'minPercent': 0, 'color': '#6B7280'}
                ]),
                'is_active': 1
            },
            {
                'name': 'UNEB Uganda Advanced Certificate of Education',
                'type': 'points',
                'class_levels': json.dumps(['S6']),
                'grade_ranges': json.dumps([
                    {'grade': 'A', 'minPercent': 80, 'points': 6, 'color': '#10B981'},
                    {'grade': 'B', 'minPercent': 70, 'points': 5, 'color': '#3B82F6'},
                    {'grade': 'C', 'minPercent': 60, 'points': 4, 'color': '#F59E0B'},
                    {'grade': 'D', 'minPercent': 50, 'points': 3, 'color': '#EF4444'},
                    {'grade': 'E', 'minPercent': 40, 'points': 2, 'color': '#EF4444'},
                    {'grade': 'O', 'minPercent': 35, 'points': 1, 'color': '#8B5CF6'},
                    {'grade': 'F', 'minPercent': 0, 'points': 0, 'color': '#6B7280'}
                ]),
                'is_active': 1
            }
        ]

        insert_schema = """
            INSERT OR IGNORE INTO grading_schemas (name, type, class_levels, grade_ranges, is_active)
            VALUES (?, ?, ?, ?, ?)
        """

        with self.conn:
            for schema in default_schemas:
                self.conn.execute(insert_schema, (
                    schema['name'], schema['type'], schema['class_levels'], 
                    schema['grade_ranges'], schema['is_active']
                ))

        # Insert default settings
        default_settings = [
            {'key': 'school_name', 'value': 'Sample Primary School', 'type': 'string', 'description': 'School name'},
            {'key': 'academic_year', 'value': str(datetime.now().year), 'type': 'string', 'description': 'Current academic year'},
            {'key': 'current_term', 'value': 'term1', 'type': 'string', 'description': 'Current term'},
            {'key': 'auto_backup', 'value': 'true', 'type': 'boolean', 'description': 'Enable automatic backups'},
            {'key': 'backup_frequency', 'value': '7', 'type': 'number', 'description': 'Backup frequency in days'},
            {'key': 'encryption_enabled', 'value': 'true', 'type': 'boolean', 'description': 'Enable data encryption'},
            {'key': 'max_login_attempts', 'value': '5', 'type': 'number', 'description': 'Maximum login attempts before lockout'},
            {'key': 'session_timeout', 'value': '30', 'type': 'number', 'description': 'Session timeout in minutes'},
            {'key': 'cloud_sync_enabled', 'value': 'false', 'type': 'boolean', 'description': 'Enable cloud synchronization'},
            {'key': 'report_language', 'value': 'English', 'type': 'string', 'description': 'Default report language'},
            {'key': 'database_version', 'value': '1', 'type': 'number', 'description': 'Database schema version'}
        ]

        insert_setting = """
            INSERT OR IGNORE INTO settings (key, value, type, description)
            VALUES (?, ?, ?, ?)
        """

        with self.conn:
            for setting in default_settings:
                self.conn.execute(insert_setting, (
                    setting['key'], setting['value'], 
                    setting['type'], setting['description']
                ))

        # Create default admin user if none exists
        admin_exists = self.conn.execute(
            "SELECT COUNT(*) as count FROM users WHERE role = 'admin'"
        ).fetchone()['count']

        if admin_exists == 0:
            default_password = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt(12)).decode()
            
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash, full_name, role, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ('admin', 'admin@school.ug', default_password, 
                     'System Administrator', 'admin', 1)
                )
    
    def _create_prepared_statements(self) -> None:
        """
        Create prepared statements for frequently used queries.
        """
        # Student operations
        self.statements['get_students'] = self.conn.cursor()
        self.statements['get_students'].prepare("""
            SELECT * FROM students 
            WHERE status = 'Active' 
            ORDER BY class_level, name
        """)

        self.statements['get_students_by_class'] = self.conn.cursor()
        self.statements['get_students_by_class'].prepare("""
            SELECT * FROM students 
            WHERE class_level = ? AND status = 'Active'
            ORDER BY name
        """)

        self.statements['get_student'] = self.conn.cursor()
        self.statements['get_student'].prepare("SELECT * FROM students WHERE id = ?")
        
        self.statements['create_student'] = self.conn.cursor()
        self.statements['create_student'].prepare("""
            INSERT INTO students (student_id, name, class_level, date_of_birth, gender, address, 
                                parent_name, parent_phone, parent_email, admission_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)

        self.statements['update_student'] = self.conn.cursor()
        self.statements['update_student'].prepare("""
            UPDATE students 
            SET name = ?, class_level = ?, date_of_birth = ?, gender = ?, 
                address = ?, parent_name = ?, parent_phone = ?, parent_email = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """)

        self.statements['delete_student'] = self.conn.cursor()
        self.statements['delete_student'].prepare("""
            UPDATE students SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """)

        # Subject operations
        self.statements['get_subjects'] = self.conn.cursor()
        self.statements['get_subjects'].prepare("SELECT * FROM subjects ORDER BY class_level, name")

        self.statements['get_subjects_by_class'] = self.conn.cursor()
        self.statements['get_subjects_by_class'].prepare("""
            SELECT * FROM subjects WHERE class_level = ? ORDER BY name
        """)

        self.statements['create_subject'] = self.conn.cursor()
        self.statements['create_subject'].prepare("""
            INSERT INTO subjects (name, code, class_level, is_core, weight, description, teacher_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        self.statements['update_subject'] = self.conn.cursor()
        self.statements['update_subject'].prepare("""
            UPDATE subjects 
            SET name = ?, code = ?, class_level = ?, is_core = ?, weight = ?, 
                description = ?, teacher_name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """)

        self.statements['delete_subject'] = self.conn.cursor()
        self.statements['delete_subject'].prepare("DELETE FROM subjects WHERE id = ?")

        # Grade operations
        self.statements['get_grades'] = self.conn.cursor()
        self.statements['get_grades'].prepare("""
            SELECT g.*, s.name as subject_name, st.name as student_name
            FROM grades g
            JOIN subjects s ON g.subject_id = s.id
            JOIN students st ON g.student_id = st.id
            WHERE g.student_id = ? AND g.term = ? AND g.academic_year = ?
        """)

        self.statements['save_grade'] = self.conn.cursor()
        self.statements['save_grade'].prepare("""
            INSERT OR REPLACE INTO grades (student_id, subject_id, term, academic_year, score, grade_letter, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        self.statements['get_student_grades'] = self.conn.cursor()
        self.statements['get_student_grades'].prepare("""
            SELECT g.*, s.name as subject_name, s.weight
            FROM grades g
            JOIN subjects s ON g.subject_id = s.id
            WHERE g.student_id = ? AND g.academic_year = ?
            ORDER BY s.name, g.term
        """)

        # Settings operations
        self.statements['get_setting'] = self.conn.cursor()
        self.statements['get_setting'].prepare("SELECT * FROM settings WHERE key = ?")

        self.statements['set_setting'] = self.conn.cursor()
        self.statements['set_setting'].prepare("""
            INSERT OR REPLACE INTO settings (key, value, type, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """)

        self.statements['get_all_settings'] = self.conn.cursor()
        self.statements['get_all_settings'].prepare("SELECT * FROM settings ORDER BY key")

        # User operations
        self.statements['get_user_by_email'] = self.conn.cursor()
        self.statements['get_user_by_email'].prepare("""
            SELECT * FROM users WHERE email = ? AND is_active = 1
        """)

        self.statements['get_user_by_id'] = self.conn.cursor()
        self.statements['get_user_by_id'].prepare("SELECT * FROM users WHERE id = ?")

        self.statements['update_last_login'] = self.conn.cursor()
        self.statements['update_last_login'].prepare("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
        """)

        self.statements['increment_failed_logins'] = self.conn.cursor()
        self.statements['increment_failed_logins'].prepare("""
            UPDATE users SET failed_login_attempts = failed_login_attempts + 1 WHERE id = ?
        """)

        self.statements['reset_failed_logins'] = self.conn.cursor()
        self.statements['reset_failed_logins'].prepare("""
            UPDATE users SET failed_login_attempts = 0 WHERE id = ?
        """)

        self.statements['lock_account'] = self.conn.cursor()
        self.statements['lock_account'].prepare("""
            UPDATE users SET account_locked_until = ? WHERE id = ?
        """)

        # Audit logging
        self.statements['log_audit'] = self.conn.cursor()
        self.statements['log_audit'].prepare("""
            INSERT INTO audit_logs (user_id, action, table_name, record_id, old_values, new_values, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """)
    
    def _run_integrity_check(self) -> None:
        """
        Run database integrity check.
        """
        result = self.conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] != 'ok':
            raise RuntimeError("Database integrity check failed")
    
    # ======================
    # Public API Methods
    # ======================
    
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.
        
        Args:
            sql: The SQL query to execute
            params: Parameters for the query
            
        Returns:
            List of rows as dictionaries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def execute_transaction(self, operations: List[Dict[str, Any]]) -> List[sqlite3.Cursor]:
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of operations, each with 'sql' and 'params' keys
            
        Returns:
            List of cursor objects for each operation
        """
        results = []
        try:
            with self.conn:
                for op in operations:
                    cursor = self.conn.cursor()
                    cursor.execute(op['sql'], op.get('params', ()))
                    results.append(cursor)
            return results
        except sqlite3.Error as e:
            self.logger.error(f"Transaction failed: {str(e)}")
            raise
    
    # Student management
    def get_students(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get students with optional filters.
        
        Args:
            filters: Dictionary of filters (class_level, search)
            
        Returns:
            List of student records
        """
        filters = filters or {}
        query = "SELECT * FROM students WHERE status = ?"
        params = ['Active']

        if filters.get('class_level'):
            query += " AND class_level = ?"
            params.append(filters['class_level'])

        if filters.get('search'):
            query += " AND (name LIKE ? OR student_id LIKE ?)"
            params.extend([f"%{filters['search']}%", f"%{filters['search']}%"])

        query += " ORDER BY class_level, name"
        return self.execute_query(query, tuple(params))
    
    def get_student(self, student_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single student by ID.
        
        Args:
            student_id: The student ID
            
        Returns:
            Student record or None if not found
        """
        self.statements['get_student'].execute((student_id,))
        row = self.statements['get_student'].fetchone()
        return dict(row) if row else None
    
    def create_student(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new student record.
        
        Args:
            student_data: Dictionary of student data
            
        Returns:
            Dictionary with 'success' flag and 'id' of new student
        """
        try:
            self.statements['create_student'].execute((
                student_data['student_id'],
                student_data['name'],
                student_data['class_level'],
                student_data.get('date_of_birth'),
                student_data.get('gender'),
                student_data.get('address'),
                student_data.get('parent_name'),
                student_data.get('parent_phone'),
                student_data.get('parent_email'),
                student_data.get('admission_date', datetime.now().date().isoformat())
            ))
            
            student_id = self.statements['create_student'].lastrowid
            self._log_audit(None, 'CREATE', 'students', student_id, None, student_data)
            
            return {'success': True, 'id': student_id}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create student: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_student(self, student_id: int, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing student record.
        
        Args:
            student_id: The ID of the student to update
            student_data: Dictionary of student data to update
            
        Returns:
            Dictionary with 'success' flag
        """
        old_data = self.get_student(student_id)
        
        try:
            self.statements['update_student'].execute((
                student_data['name'],
                student_data['class_level'],
                student_data.get('date_of_birth'),
                student_data.get('gender'),
                student_data.get('address'),
                student_data.get('parent_name'),
                student_data.get('parent_phone'),
                student_data.get('parent_email'),
                student_id
            ))
            
            self._log_audit(None, 'UPDATE', 'students', student_id, old_data, student_data)
            return {'success': True}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update student: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_student(self, student_id: int) -> Dict[str, Any]:
        """
        Mark a student as inactive (soft delete).
        
        Args:
            student_id: The ID of the student to delete
            
        Returns:
            Dictionary with 'success' flag
        """
        old_data = self.get_student(student_id)
        
        try:
            self.statements['delete_student'].execute(('Inactive', student_id))
            self._log_audit(None, 'DELETE', 'students', student_id, old_data, {'status': 'Inactive'})
            return {'success': True}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to delete student: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # Subject management
    def get_subjects(self, class_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get subjects, optionally filtered by class level.
        
        Args:
            class_level: Optional class level filter
            
        Returns:
            List of subject records
        """
        if class_level:
            self.statements['get_subjects_by_class'].execute((class_level,))
            return [dict(row) for row in self.statements['get_subjects_by_class'].fetchall()]
        else:
            self.statements['get_subjects'].execute()
            return [dict(row) for row in self.statements['get_subjects'].fetchall()]
    
    def create_subject(self, subject_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new subject.
        
        Args:
            subject_data: Dictionary of subject data
            
        Returns:
            Dictionary with 'success' flag and 'id' of new subject
        """
        try:
            self.statements['create_subject'].execute((
                subject_data['name'],
                subject_data.get('code'),
                subject_data['class_level'],
                int(subject_data.get('is_core', True)),
                float(subject_data.get('weight', 1.0)),
                subject_data.get('description'),
                subject_data.get('teacher_name')
            ))
            
            subject_id = self.statements['create_subject'].lastrowid
            self._log_audit(None, 'CREATE', 'subjects', subject_id, None, subject_data)
            
            return {'success': True, 'id': subject_id}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create subject: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_subject(self, subject_id: int, subject_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing subject.
        
        Args:
            subject_id: The ID of the subject to update
            subject_data: Dictionary of subject data to update
            
        Returns:
            Dictionary with 'success' flag
        """
        old_data = self.execute_query("SELECT * FROM subjects WHERE id = ?", (subject_id,))[0]
        
        try:
            self.statements['update_subject'].execute((
                subject_data['name'],
                subject_data.get('code'),
                subject_data['class_level'],
                int(subject_data.get('is_core', True)),
                float(subject_data.get('weight', 1.0)),
                subject_data.get('description'),
                subject_data.get('teacher_name'),
                subject_id
            ))
            
            self._log_audit(None, 'UPDATE', 'subjects', subject_id, old_data, subject_data)
            return {'success': True}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update subject: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_subject(self, subject_id: int) -> Dict[str, Any]:
        """
        Delete a subject.
        
        Args:
            subject_id: The ID of the subject to delete
            
        Returns:
            Dictionary with 'success' flag
        """
        old_data = self.execute_query("SELECT * FROM subjects WHERE id = ?", (subject_id,))[0]
        
        try:
            self.statements['delete_subject'].execute((subject_id,))
            self._log_audit(None, 'DELETE', 'subjects', subject_id, old_data, None)
            return {'success': True}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to delete subject: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # Grade management
    def get_grades(self, student_id: int, term: str, academic_year: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get grades for a student in a specific term and academic year.
        
        Args:
            student_id: The student ID
            term: The term (term1, term2, term3)
            academic_year: Optional academic year (defaults to current)
            
        Returns:
            List of grade records
        """
        year = academic_year or self.get_setting('academic_year')['value']
        self.statements['get_grades'].execute((student_id, term, year))
        return [dict(row) for row in self.statements['get_grades'].fetchall()]
    
    def save_grade(self, grade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save or update a grade.
        
        Args:
            grade_data: Dictionary of grade data
            
        Returns:
            Dictionary with 'success' flag
        """
        try:
            self.statements['save_grade'].execute((
                grade_data['student_id'],
                grade_data['subject_id'],
                grade_data['term'],
                grade_data['academic_year'],
                grade_data['score'],
                grade_data.get('grade_letter'),
                grade_data.get('remarks')
            ))
            
            return {'success': True}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save grade: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def save_grades(self, grades_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save multiple grades in a transaction.
        
        Args:
            grades_data: List of grade data dictionaries
            
        Returns:
            Dictionary with 'success' flag and count of saved grades
        """
        try:
            with self.conn:
                count = 0
                for grade in grades_data:
                    self.statements['save_grade'].execute((
                        grade['student_id'],
                        grade['subject_id'],
                        grade['term'],
                        grade['academic_year'],
                        grade['score'],
                        grade.get('grade_letter'),
                        grade.get('remarks')
                    ))
                    count += 1
                
                self._log_audit(None, 'BULK_INSERT', 'grades', None, None, {'count': count})
                return {'success': True, 'count': count}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save grades: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_student_grades(self, student_id: int, academic_year: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all grades for a student in an academic year.
        
        Args:
            student_id: The student ID
            academic_year: Optional academic year (defaults to current)
            
        Returns:
            List of grade records
        """
        year = academic_year or self.get_setting('academic_year')['value']
        self.statements['get_student_grades'].execute((student_id, year))
        return [dict(row) for row in self.statements['get_student_grades'].fetchall()]
    
    # Settings management
    def get_setting(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a setting by key.
        
        Args:
            key: The setting key
            
        Returns:
            Setting dictionary or None if not found
        """
        self.statements['get_setting'].execute((key,))
        setting = self.statements['get_setting'].fetchone()
        
        if not setting:
            return None
            
        setting = dict(setting)
        
        # Decrypt if needed
        if setting['is_encrypted']:
            setting['value'] = self._decrypt_data(setting['value'])
        
        # Type conversion
        if setting['type'] == 'boolean':
            setting['value'] = setting['value'].lower() == 'true'
        elif setting['type'] == 'number':
            setting['value'] = float(setting['value'])
        elif setting['type'] == 'json':
            setting['value'] = json.loads(setting['value'])
        
        return setting
    
    def set_setting(self, key: str, value: Any, type_: str = 'string', encrypt: bool = False) -> Dict[str, Any]:
        """
        Set a setting value.
        
        Args:
            key: The setting key
            value: The value to set
            type_: The value type (string, boolean, number, json)
            encrypt: Whether to encrypt the value
            
        Returns:
            Dictionary with 'success' flag
        """
        processed_value = str(value)
        
        if type_ == 'boolean':
            processed_value = 'true' if value else 'false'
        elif type_ == 'json':
            processed_value = json.dumps(value)
        
        if encrypt:
            processed_value = self._encrypt_data(processed_value)
        
        try:
            with self.conn:
                self.statements['set_setting'].execute((key, processed_value, type_))
                
                if encrypt:
                    self.conn.execute(
                        "UPDATE settings SET is_encrypted = 1 WHERE key = ?",
                        (key,)
                    )
            
            return {'success': True}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to set setting: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all settings as a dictionary keyed by setting key.
        
        Returns:
            Dictionary of settings
        """
        self.statements['get_all_settings'].execute()
        settings = {}
        
        for row in self.statements['get_all_settings'].fetchall():
            setting = dict(row)
            
            # Decrypt if needed
            if setting['is_encrypted']:
                setting['value'] = self._decrypt_data(setting['value'])
            
            # Type conversion
            if setting['type'] == 'boolean':
                setting['value'] = setting['value'].lower() == 'true'
            elif setting['type'] == 'number':
                setting['value'] = float(setting['value'])
            elif setting['type'] == 'json':
                setting['value'] = json.loads(setting['value'])
            
            settings[setting['key']] = setting
        
        return settings
    
    # User management
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by email address.
        
        Args:
            email: The user's email address
            
        Returns:
            User dictionary or None if not found
        """
        self.statements['get_user_by_email'].execute((email,))
        user = self.statements['get_user_by_email'].fetchone()
        return dict(user) if user else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user by ID.
        
        Args:
            user_id: The user's ID
            
        Returns:
            User dictionary or None if not found
        """
        self.statements['get_user_by_id'].execute((user_id,))
        user = self.statements['get_user_by_id'].fetchone()
        return dict(user) if user else None
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            user_data: Dictionary containing user data
            
        Returns:
            Dictionary with 'success' flag and 'id' of new user
        """
        try:
            password_hash = bcrypt.hashpw(
                user_data['password'].encode(), 
                bcrypt.gensalt(12)
            ).decode()
            
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash, full_name, role, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_data['username'],
                        user_data['email'],
                        password_hash,
                        user_data['full_name'],
                        user_data.get('role', 'teacher'),
                        int(user_data.get('is_active', True))
                    )
                )
                
                user_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                
                self._log_audit(
                    None, 'CREATE', 'users', user_id, None,
                    {
                        'username': user_data['username'],
                        'email': user_data['email'],
                        'full_name': user_data['full_name'],
                        'role': user_data.get('role', 'teacher')
                    }
                )
                
                return {'success': True, 'id': user_id}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create user: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user's information.
        
        Args:
            user_id: The user's ID
            user_data: Dictionary containing user data to update
            
        Returns:
            Dictionary with 'success' flag
        """
        old_data = self.get_user_by_id(user_id)
        
        try:
            update_fields = []
            params = []
            
            if 'username' in user_data:
                update_fields.append("username = ?")
                params.append(user_data['username'])
            
            if 'email' in user_data:
                update_fields.append("email = ?")
                params.append(user_data['email'])
            
            if 'full_name' in user_data:
                update_fields.append("full_name = ?")
                params.append(user_data['full_name'])
            
            if 'role' in user_data:
                update_fields.append("role = ?")
                params.append(user_data['role'])
            
            if 'is_active' in user_data:
                update_fields.append("is_active = ?")
                params.append(int(user_data['is_active']))
            
            if 'password' in user_data:
                password_hash = bcrypt.hashpw(
                    user_data['password'].encode(), 
                    bcrypt.gensalt(12)
                ).decode()
                update_fields.append("password_hash = ?")
                params.append(password_hash)
            
            if not update_fields:
                return {'success': True}
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            
            with self.conn:
                self.conn.execute(query, tuple(params))
                self._log_audit(None, 'UPDATE', 'users', user_id, old_data, user_data)
                
            return {'success': True}
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update user: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_last_login(self, user_id: int) -> None:
        """
        Update a user's last login timestamp.
        
        Args:
            user_id: The user's ID
        """
        self.statements['update_last_login'].execute((user_id,))
    
    def increment_failed_logins(self, user_id: int) -> None:
        """
        Increment a user's failed login count.
        
        Args:
            user_id: The user's ID
        """
        self.statements['increment_failed_logins'].execute((user_id,))
    
    def reset_failed_logins(self, user_id: int) -> None:
        """
        Reset a user's failed login count to 0.
        
        Args:
            user_id: The user's ID
        """
        self.statements['reset_failed_logins'].execute((user_id,))
    
    def lock_account(self, user_id: int, lock_until: datetime) -> None:
        """
        Lock a user's account until a specified time.
        
        Args:
            user_id: The user's ID
            lock_until: The datetime until which to lock the account
        """
        self.statements['lock_account'].execute((lock_until.isoformat(), user_id))
    
    # Audit logging
    def _log_audit(
        self,
        user_id: Optional[int],
        action: str,
        table_name: str,
        record_id: Optional[int],
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Internal method to log an audit event.
        """
        try:
            self.statements['log_audit'].execute((
                user_id,
                action,
                table_name,
                record_id,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                ip_address,
                user_agent
            ))
        except sqlite3.Error as e:
            self.logger.error(f"Failed to log audit event: {str(e)}")
    
    # Maintenance and utilities
    def optimize(self) -> None:
        """
        Optimize the database by running maintenance commands.
        """
        self.conn.execute("PRAGMA optimize")
        self.conn.execute("PRAGMA incremental_vacuum")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary containing various statistics
        """
        stats = {
            'students': self.conn.execute(
                "SELECT COUNT(*) as count FROM students WHERE status = 'Active'"
            ).fetchone()['count'],
            'subjects': self.conn.execute(
                "SELECT COUNT(*) as count FROM subjects"
            ).fetchone()['count'],
            'grades': self.conn.execute(
                "SELECT COUNT(*) as count FROM grades"
            ).fetchone()['count'],
            'users': self.conn.execute(
                "SELECT COUNT(*) as count FROM users WHERE is_active = 1"
            ).fetchone()['count'],
            'reports': self.conn.execute(
                "SELECT COUNT(*) as count FROM reports"
            ).fetchone()['count'],
            'backups': self.conn.execute(
                "SELECT COUNT(*) as count FROM backups"
            ).fetchone()['count'],
            'last_backup': self.conn.execute(
                "SELECT MAX(created_at) as last_backup FROM backups"
            ).fetchone()['last_backup']
        }
        
        return stats
    
    def create_backup(self, backup_path: str, backup_type: str = 'manual', user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a database backup.
        
        Args:
            backup_path: Path to save the backup
            backup_type: Type of backup (manual, automatic, scheduled)
            user_id: ID of user creating the backup
            
        Returns:
            Dictionary with 'success' flag
        """
        try:
            # Create the backup file
            with sqlite3.connect(str(self.db_path)) as source:
                with sqlite3.connect(backup_path) as destination:
                    source.backup(destination)
            
            # Record backup info
            file_size = os.path.getsize(backup_path)
            filename = os.path.basename(backup_path)
            
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO backups (filename, file_path, size_bytes, type, created_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (filename, backup_path, file_size, backup_type, user_id)
                )
            
            return {'success': True}
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_backup_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get backup history.
        
        Args:
            limit: Maximum number of backups to return
            
        Returns:
            List of backup records
        """
        return self.execute_query(
            """
            SELECT b.*, u.full_name as created_by_name
            FROM backups b
            LEFT JOIN users u ON b.created_by = u.id
            ORDER BY b.created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
    
    def close(self) -> None:
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()
            self.conn = None
            self.is_initialized = False
            self.logger.info("Database connection closed")
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()