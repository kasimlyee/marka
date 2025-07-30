const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs').promises;
const crypto = require('crypto');
const { app } = require('electron');
const log = require('electron-log');

class DatabaseManager {

/**
 * Constructs an instance of DatabaseManager.
 * 
 * Initializes the database connection, path, and various properties
 * related to transaction management, prepared statements, and connection pooling.
 * 
 * - `db`: The main database connection object, initially set to null.
 * - `dbPath`: The file path to the database, initially set to null.
 * - `isInitialized`: A flag indicating whether the database has been initialized, initially set to false.
 * - `transactionQueue`: A queue of pending transactions, initially an empty array.
 * - `isTransactionActive`: A flag indicating whether a transaction is currently active, initially set to false.
 * - `statements`: An object to store prepared SQL statements, initially an empty object.
 * - `connectionPool`: An array to manage pooled database connections, initially empty.
 * - `maxConnections`: The maximum number of connections allowed in the pool, set to 5.
 */

  constructor() {
    this.db = null;
    this.dbPath = null;
    this.isInitialized = false;
    this.transactionQueue = [];
    this.isTransactionActive = false;
    this.statements = {};
    this.connectionPool = [];
    this.maxConnections = 5;
  }

  /**
   * Initializes the database.
   *
   * Sets the database path, initializes the main database connection,
   * configures the database for performance, creates tables, creates prepared
   * statements, initializes the connection pool, and runs an integrity check.
   *
   * Emits a log message with the database path on success.
   *
   * @throws Will throw an error if the database initialization fails.
   * @returns {Promise<void>} A promise that resolves when the database has been initialized.
   */
  async initialize() {
    try {
      // Set database path
      const userData = app.getPath('userData');
      await fs.mkdir(userData, { recursive: true });
      this.dbPath = path.join(userData, 'marka_database.db');

      // Initialize main database connection
      this.db = new Database(this.dbPath, {
        verbose: console.log,
        fileMustExist: false
      });

      // Configure database for performance
      this.configureDatabase();

      // Create tables
      await this.createTables();

      // Create prepared statements
      this.createPreparedStatements();

      // Initialize connection pool
      this.initializeConnectionPool();

      // Run integrity check
      await this.runIntegrityCheck();

      this.isInitialized = true;
      log.info('Database initialized successfully at:', this.dbPath);

    } catch (error) {
      log.error('Database initialization failed:', error);
      throw error;
    }
  }

  /**
   * Configures the database for performance and security.
   *
   * This sets up write-ahead logging, normal synchronous mode, a 10MB cache,
   * stores temporary tables in memory, sets up a 256MB memory map, and optimizes
   * the page size. It also enables secure deletion, foreign key constraints,
   * and sets up functions for generating UUIDs, encrypting, and decrypting data.
   *
   * @private
   * @returns {void}
   */
  configureDatabase() {
    // Performance optimizations
    this.db.pragma('journal_mode = WAL'); // Write-Ahead Logging
    this.db.pragma('synchronous = NORMAL'); // Balance between performance and safety
    this.db.pragma('cache_size = 10000'); // 10MB cache
    this.db.pragma('temp_store = MEMORY'); // Store temp tables in memory
    this.db.pragma('mmap_size = 268435456'); // 256MB memory map
    this.db.pragma('page_size = 4096'); // Optimal page size
    this.db.pragma('auto_vacuum = INCREMENTAL'); // Automatic space recovery
    
    // Security settings
    this.db.pragma('secure_delete = ON'); // Secure deletion
    this.db.pragma('foreign_keys = ON'); // Enable foreign key constraints
    
    // Enable functions
    this.db.function('uuid', () => crypto.randomUUID());
    this.db.function('encrypt', (data) => {
      const cipher = crypto.createCipher('aes-256-cbc', process.env.ENCRYPTION_KEY || 'marka_default_key');
      let encrypted = cipher.update(data, 'utf8', 'hex');
      encrypted += cipher.final('hex');
      return encrypted;
    });
    
    this.db.function('decrypt', (encryptedData) => {
      const decipher = crypto.createDecipher('aes-256-cbc', process.env.ENCRYPTION_KEY || 'marka_default_key');
      let decrypted = decipher.update(encryptedData, 'hex', 'utf8');
      decrypted += decipher.final('utf8');
      return decrypted;
    });
  }

  async createTables() {
    const schemas = [
      // Schools table
      `CREATE TABLE IF NOT EXISTS schools (
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
      )`,

      // Students table
      `CREATE TABLE IF NOT EXISTS students (
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
      )`,

      // Subjects table
      `CREATE TABLE IF NOT EXISTS subjects (
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
      )`,

      // Grades table
      `CREATE TABLE IF NOT EXISTS grades (
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
      )`,

      // Attendance table
      `CREATE TABLE IF NOT EXISTS attendance (
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
      )`,

      // Conduct table
      `CREATE TABLE IF NOT EXISTS conduct (
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
      )`,

      // Users table
      `CREATE TABLE IF NOT EXISTS users (
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
      )`,

      // Settings table
      `CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT,
        type TEXT DEFAULT 'string',
        description TEXT,
        is_encrypted BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )`,

      // Reports table
      `CREATE TABLE IF NOT EXISTS reports (
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
      )`,

      // Grading schemas table
      `CREATE TABLE IF NOT EXISTS grading_schemas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT CHECK(type IN ('division', 'grade', 'points')) NOT NULL,
        class_levels TEXT NOT NULL, -- JSON array
        grade_ranges TEXT NOT NULL, -- JSON array
        is_active BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )`,

      // Audit logs table
      `CREATE TABLE IF NOT EXISTS audit_logs (
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
      )`,

      // Backups table
      `CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        size_bytes INTEGER,
        type TEXT CHECK(type IN ('manual', 'automatic', 'scheduled')) DEFAULT 'manual',
        created_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
      )`
    ];

    // Execute schema creation
    const transaction = this.db.transaction(() => {
      schemas.forEach(schema => this.db.exec(schema));
    });
    transaction();

    // Create indexes for performance
    await this.createIndexes();

    // Insert default data
    await this.insertDefaultData();
  }

  async createIndexes() {
    const indexes = [
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
    ];

    indexes.forEach(index => this.db.exec(index));
  }

  async insertDefaultData() {
    // Insert default grading schemas
    const defaultSchemas = [
      {
        name: 'UNEB Primary Leaving Examination',
        type: 'division',
        class_levels: JSON.stringify(['P7']),
        grade_ranges: JSON.stringify([
          { grade: 'Division 1', minPercent: 90, maxAggregate: 12, color: '#10B981' },
          { grade: 'Division 2', minPercent: 75, maxAggregate: 23, color: '#3B82F6' },
          { grade: 'Division 3', minPercent: 60, maxAggregate: 29, color: '#F59E0B' },
          { grade: 'Division 4', minPercent: 50, maxAggregate: 34, color: '#EF4444' },
          { grade: 'Ungraded', minPercent: 0, maxAggregate: 99, color: '#6B7280' }
        ]),
        is_active: 1
      },
      {
        name: 'UNEB Uganda Certificate of Education',
        type: 'grade',
        class_levels: JSON.stringify(['S4']),
        grade_ranges: JSON.stringify([
          { grade: 'A', minPercent: 85, color: '#10B981' },
          { grade: 'B', minPercent: 75, color: '#3B82F6' },
          { grade: 'C', minPercent: 65, color: '#F59E0B' },
          { grade: 'D', minPercent: 55, color: '#EF4444' },
          { grade: 'E', minPercent: 45, color: '#EF4444' },
          { grade: 'F', minPercent: 0, color: '#6B7280' }
        ]),
        is_active: 1
      },
      {
        name: 'UNEB Uganda Advanced Certificate of Education',
        type: 'points',
        class_levels: JSON.stringify(['S6']),
        grade_ranges: JSON.stringify([
          { grade: 'A', minPercent: 80, points: 6, color: '#10B981' },
          { grade: 'B', minPercent: 70, points: 5, color: '#3B82F6' },
          { grade: 'C', minPercent: 60, points: 4, color: '#F59E0B' },
          { grade: 'D', minPercent: 50, points: 3, color: '#EF4444' },
          { grade: 'E', minPercent: 40, points: 2, color: '#EF4444' },
          { grade: 'O', minPercent: 35, points: 1, color: '#8B5CF6' },
          { grade: 'F', minPercent: 0, points: 0, color: '#6B7280' }
        ]),
        is_active: 1
      }
    ];

    const insertSchema = this.db.prepare(`
      INSERT OR IGNORE INTO grading_schemas (name, type, class_levels, grade_ranges, is_active)
      VALUES (?, ?, ?, ?, ?)
    `);

    defaultSchemas.forEach(schema => {
      insertSchema.run(schema.name, schema.type, schema.class_levels, schema.grade_ranges, schema.is_active);
    });

    // Insert default settings
    const defaultSettings = [
      { key: 'school_name', value: 'Sample Primary School', type: 'string', description: 'School name' },
      { key: 'academic_year', value: '2024', type: 'string', description: 'Current academic year' },
      { key: 'current_term', value: 'term1', type: 'string', description: 'Current term' },
      { key: 'auto_backup', value: 'true', type: 'boolean', description: 'Enable automatic backups' },
      { key: 'backup_frequency', value: '7', type: 'number', description: 'Backup frequency in days' },
      { key: 'encryption_enabled', value: 'true', type: 'boolean', description: 'Enable data encryption' },
      { key: 'max_login_attempts', value: '5', type: 'number', description: 'Maximum login attempts before lockout' },
      { key: 'session_timeout', value: '30', type: 'number', description: 'Session timeout in minutes' },
      { key: 'cloud_sync_enabled', value: 'false', type: 'boolean', description: 'Enable cloud synchronization' },
      { key: 'report_language', value: 'English', type: 'string', description: 'Default report language' }
    ];

    const insertSetting = this.db.prepare(`
      INSERT OR IGNORE INTO settings (key, value, type, description)
      VALUES (?, ?, ?, ?)
    `);

    defaultSettings.forEach(setting => {
      insertSetting.run(setting.key, setting.value, setting.type, setting.description);
    });

    // Create default admin user
    const adminExists = this.db.prepare('SELECT COUNT(*) as count FROM users WHERE role = ?').get('admin');
    if (adminExists.count === 0) {
      const bcrypt = require('bcrypt');
      const defaultPassword = await bcrypt.hash('admin123', 12);
      
      this.db.prepare(`
        INSERT INTO users (username, email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
      `).run('admin', 'admin@school.ug', defaultPassword, 'System Administrator', 'admin', 1);
    }
  }

  createPreparedStatements() {
    // Student operations
    this.statements.getStudents = this.db.prepare(`
      SELECT * FROM students 
      WHERE status = 'Active' 
      ORDER BY class_level, name
    `);

    this.statements.getStudentsByClass = this.db.prepare(`
      SELECT * FROM students 
      WHERE class_level = ? AND status = 'Active'
      ORDER BY name
    `);

    this.statements.getStudent = this.db.prepare('SELECT * FROM students WHERE id = ?');
    
    this.statements.createStudent = this.db.prepare(`
      INSERT INTO students (student_id, name, class_level, date_of_birth, gender, address, parent_name, parent_phone, parent_email, admission_date)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    this.statements.updateStudent = this.db.prepare(`
      UPDATE students 
      SET name = ?, class_level = ?, date_of_birth = ?, gender = ?, address = ?, parent_name = ?, parent_phone = ?, parent_email = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `);

    this.statements.deleteStudent = this.db.prepare('UPDATE students SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?');

    // Subject operations
    this.statements.getSubjects = this.db.prepare('SELECT * FROM subjects ORDER BY class_level, name');
    this.statements.getSubjectsByClass = this.db.prepare('SELECT * FROM subjects WHERE class_level = ? ORDER BY name');
    this.statements.createSubject = this.db.prepare(`
      INSERT INTO subjects (name, code, class_level, is_core, weight, description, teacher_name)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);
    this.statements.updateSubject = this.db.prepare(`
      UPDATE subjects 
      SET name = ?, code = ?, class_level = ?, is_core = ?, weight = ?, description = ?, teacher_name = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `);
    this.statements.deleteSubject = this.db.prepare('DELETE FROM subjects WHERE id = ?');

    // Grade operations
    this.statements.getGrades = this.db.prepare(`
      SELECT g.*, s.name as subject_name, st.name as student_name
      FROM grades g
      JOIN subjects s ON g.subject_id = s.id
      JOIN students st ON g.student_id = st.id
      WHERE g.student_id = ? AND g.term = ? AND g.academic_year = ?
    `);

    this.statements.saveGrade = this.db.prepare(`
      INSERT OR REPLACE INTO grades (student_id, subject_id, term, academic_year, score, grade_letter, remarks)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    this.statements.getStudentGrades = this.db.prepare(`
      SELECT g.*, s.name as subject_name, s.weight
      FROM grades g
      JOIN subjects s ON g.subject_id = s.id
      WHERE g.student_id = ? AND g.academic_year = ?
      ORDER BY s.name, g.term
    `);

    // Settings operations
    this.statements.getSetting = this.db.prepare('SELECT * FROM settings WHERE key = ?');
    this.statements.setSetting = this.db.prepare(`
      INSERT OR REPLACE INTO settings (key, value, type, updated_at)
      VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    `);
    this.statements.getAllSettings = this.db.prepare('SELECT * FROM settings ORDER BY key');

    // User operations
    this.statements.getUserByEmail = this.db.prepare('SELECT * FROM users WHERE email = ? AND is_active = 1');
    this.statements.getUserById = this.db.prepare('SELECT * FROM users WHERE id = ?');
    this.statements.updateLastLogin = this.db.prepare('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?');
    this.statements.incrementFailedLogins = this.db.prepare(`
      UPDATE users SET failed_login_attempts = failed_login_attempts + 1 WHERE id = ?
    `);
    this.statements.resetFailedLogins = this.db.prepare('UPDATE users SET failed_login_attempts = 0 WHERE id = ?');
    this.statements.lockAccount = this.db.prepare('UPDATE users SET account_locked_until = ? WHERE id = ?');
  }

  initializeConnectionPool() {
    for (let i = 0; i < this.maxConnections; i++) {
      const connection = new Database(this.dbPath, {
        readonly: true,
        fileMustExist: true
      });
      connection.pragma('journal_mode = WAL');
      connection.pragma('synchronous = NORMAL');
      this.connectionPool.push({
        connection,
        inUse: false
      });
    }
  }

  getPooledConnection() {
    const availableConnection = this.connectionPool.find(conn => !conn.inUse);
    if (availableConnection) {
      availableConnection.inUse = true;
      return availableConnection;
    }
    return null;
  }

  releasePooledConnection(pooledConnection) {
    pooledConnection.inUse = false;
  }

  // High-level database operations
  async query(sql, params = []) {
    try {
      if (sql.trim().toUpperCase().startsWith('SELECT')) {
        const pooled = this.getPooledConnection();
        if (pooled) {
          try {
            const stmt = pooled.connection.prepare(sql);
            const result = stmt.all(params);
            return result;
          } finally {
            this.releasePooledConnection(pooled);
          }
        }
      }
      
      const stmt = this.db.prepare(sql);
      if (sql.trim().toUpperCase().startsWith('SELECT')) {
        return stmt.all(params);
      } else {
        return stmt.run(params);
      }
    } catch (error) {
      log.error('Database query error:', error);
      throw error;
    }
  }

  async transaction(operations) {
    const transaction = this.db.transaction(() => {
      const results = [];
      for (const op of operations) {
        const stmt = this.db.prepare(op.sql);
        const result = stmt.run(op.params || []);
        results.push(result);
      }
      return results;
    });

    return transaction();
  }

  // Student management methods
  async getStudents(filters = {}) {
    let query = 'SELECT * FROM students WHERE status = ?';
    let params = ['Active'];

    if (filters.class_level) {
      query += ' AND class_level = ?';
      params.push(filters.class_level);
    }

    if (filters.search) {
      query += ' AND (name LIKE ? OR student_id LIKE ?)';
      params.push(`%${filters.search}%`, `%${filters.search}%`);
    }

    query += ' ORDER BY class_level, name';

    return await this.query(query, params);
  }

  async getStudent(id) {
    return this.statements.getStudent.get(id);
  }

  async createStudent(studentData) {
    const result = this.statements.createStudent.run(
      studentData.student_id,
      studentData.name,
      studentData.class_level,
      studentData.date_of_birth,
      studentData.gender,
      studentData.address || null,
      studentData.parent_name || null,
      studentData.parent_phone || null,
      studentData.parent_email || null,
      studentData.admission_date || new Date().toISOString().split('T')[0]
    );

    await this.logAudit(null, 'CREATE', 'students', result.lastInsertRowid, null, studentData);
    return result;
  }

  async updateStudent(id, studentData) {
    const oldData = this.statements.getStudent.get(id);
    
    const result = this.statements.updateStudent.run(
      studentData.name,
      studentData.class_level,
      studentData.date_of_birth,
      studentData.gender,
      studentData.address || null,
      studentData.parent_name || null,
      studentData.parent_phone || null,
      studentData.parent_email || null,
      id
    );

    await this.logAudit(null, 'UPDATE', 'students', id, oldData, studentData);
    return result;
  }

  async deleteStudent(id) {
    const oldData = this.statements.getStudent.get(id);
    const result = this.statements.deleteStudent.run('Inactive', id);
    
    await this.logAudit(null, 'DELETE', 'students', id, oldData, { status: 'Inactive' });
    return result;
  }

  // Subject management methods
  async getSubjects(classLevel = null) {
    if (classLevel) {
      return this.statements.getSubjectsByClass.all(classLevel);
    }
    return this.statements.getSubjects.all();
  }

  async createSubject(subjectData) {
    const result = this.statements.createSubject.run(
      subjectData.name,
      subjectData.code || null,
      subjectData.class_level,
      subjectData.is_core ? 1 : 0,
      subjectData.weight || 1.0,
      subjectData.description || null,
      subjectData.teacher_name || null
    );

    await this.logAudit(null, 'CREATE', 'subjects', result.lastInsertRowid, null, subjectData);
    return result;
  }

  async updateSubject(id, subjectData) {
    const oldData = this.db.prepare('SELECT * FROM subjects WHERE id = ?').get(id);
    
    const result = this.statements.updateSubject.run(
      subjectData.name,
      subjectData.code || null,
      subjectData.class_level,
      subjectData.is_core ? 1 : 0,
      subjectData.weight || 1.0,
      subjectData.description || null,
      subjectData.teacher_name || null,
      id
    );

    await this.logAudit(null, 'UPDATE', 'subjects', id, oldData, subjectData);
    return result;
  }

  async deleteSubject(id) {
    const oldData = this.db.prepare('SELECT * FROM subjects WHERE id = ?').get(id);
    const result = this.statements.deleteSubject.run(id);
    
    await this.logAudit(null, 'DELETE', 'subjects', id, oldData, null);
    return result;
  }

  // Grade management methods
  async getGrades(studentId, term, academicYear = null) {
    const year = academicYear || await this.getSetting('academic_year');
    return this.statements.getGrades.all(studentId, term, year.value);
  }

  async saveGrades(gradesData) {
    const transaction = this.db.transaction((grades) => {
      const results = [];
      for (const grade of grades) {
        const result = this.statements.saveGrade.run(
          grade.student_id,
          grade.subject_id,
          grade.term,
          grade.academic_year,
          grade.score,
          grade.grade_letter || null,
          grade.remarks || null
        );
        results.push(result);
      }
      return results;
    });

    const results = transaction(gradesData);
    await this.logAudit(null, 'BULK_INSERT', 'grades', null, null, { count: gradesData.length });
    return results;
  }

  async getStudentGrades(studentId, academicYear = null) {
    const year = academicYear || await this.getSetting('academic_year');
    return this.statements.getStudentGrades.all(studentId, year.value);
  }

  async bulkImportGrades(csvData) {
    // Implementation for bulk CSV import
    const results = [];
    const transaction = this.db.transaction((data) => {
      for (const row of data) {
        // Validate and insert each row
        const result = this.statements.saveGrade.run(
          row.student_id,
          row.subject_id,
          row.term,
          row.academic_year,
          row.score,
          row.grade_letter,
          row.remarks
        );
        results.push(result);
      }
      return results;
    });

    return transaction(csvData);
  }

  // Settings management
  async getSetting(key) {
    const setting = this.statements.getSetting.get(key);
    if (!setting) return null;

    let value = setting.value;
    if (setting.is_encrypted) {
      value = this.db.function('decrypt')(value);
    }

    // Type conversion
    switch (setting.type) {
      case 'boolean':
        value = value === 'true';
        break;
      case 'number':
        value = parseFloat(value);
        break;
      case 'json':
        value = JSON.parse(value);
        break;
    }

    return { ...setting, value };
  }

  async setSetting(key, value, type = 'string', encrypt = false) {
    let processedValue = value;

    // Type conversion
    if (type === 'boolean') {
      processedValue = value.toString();
    } else if (type === 'json') {
      processedValue = JSON.stringify(value);
    } else if (type === 'number') {
      processedValue = value.toString();
    }

    // Encryption
    if (encrypt) {
      processedValue = this.db.function('encrypt')(processedValue);
    }

    const result = this.statements.setSetting.run(key, processedValue, type);
    
    // Update encryption flag if needed
    if (encrypt) {
      this.db.prepare('UPDATE settings SET is_encrypted = 1 WHERE key = ?').run(key);
    }

    return result;
  }

  async getAllSettings() {
    const settings = this.statements.getAllSettings.all();
    const processedSettings = {};

    for (const setting of settings) {
      let value = setting.value;
      
      if (setting.is_encrypted) {
        value = this.db.function('decrypt')(value);
      }

      switch (setting.type) {
        case 'boolean':
          value = value === 'true';
          break;
        case 'number':
          value = parseFloat(value);
          break;
        case 'json':
          value = JSON.parse(value);
          break;
      }

      processedSettings[setting.key] = {
        ...setting,
        value
      };
    }

    return processedSettings;
  }

  // Audit logging
  async logAudit(userId, action, tableName, recordId, oldValues, newValues, ipAddress = null, userAgent = null) {
    try {
      this.db.prepare(`
        INSERT INTO audit_logs (user_id, action, table_name, record_id, old_values, new_values, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        userId,
        action,
        tableName,
        recordId,
        oldValues ? JSON.stringify(oldValues) : null,
        newValues ? JSON.stringify(newValues) : null,
        ipAddress,
        userAgent
      );
    } catch (error) {
      log.error('Audit logging error:', error);
    }
  }

  // Performance and maintenance
  async runIntegrityCheck() {
    const result = this.db.pragma('integrity_check');
    if (result[0].integrity_check !== 'ok') {
      throw new Error('Database integrity check failed');
    }
    return true;
  }

  async optimize() {
    this.db.pragma('optimize');
    this.db.pragma('incremental_vacuum');
  }

  async getStatistics() {
    const stats = {
      students: this.db.prepare('SELECT COUNT(*) as count FROM students WHERE status = ?').get('Active').count,
      subjects: this.db.prepare('SELECT COUNT(*) as count FROM subjects').get().count,
      grades: this.db.prepare('SELECT COUNT(*) as count FROM grades').get().count,
      users: this.db.prepare('SELECT COUNT(*) as count FROM users WHERE is_active = 1').get().count,
      reports: this.db.prepare('SELECT COUNT(*) as count FROM reports').get().count,
      backups: this.db.prepare('SELECT COUNT(*) as count FROM backups').get().count,
      diskUsage: await this.getDiskUsage(),
      lastBackup: this.db.prepare('SELECT MAX(created_at) as last_backup FROM backups').get().last_backup,
      uptime: process.uptime()
    };
    return stats;
  }

  async getDiskUsage() {
    try {
      const stats = await fs.stat(this.dbPath);
      return {
        database: stats.size,
        wal: await this.getFileSize(this.dbPath + '-wal'),
        shm: await this.getFileSize(this.dbPath + '-shm')
      };
    } catch (error) {
      return { database: 0, wal: 0, shm: 0 };
    }
  }

  async getFileSize(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return stats.size;
    } catch (error) {
      return 0;
    }
  }

  async flush() {
    // Force write any pending transactions
    this.db.pragma('wal_checkpoint(TRUNCATE)');
  }

  async close() {
    try {
      // Close all pooled connections
      for (const pooled of this.connectionPool) {
        pooled.connection.close();
      }
      this.connectionPool = [];

      // Close main connection
      if (this.db) {
        this.db.close();
        this.db = null;
      }

      this.isInitialized = false;
      log.info('Database connections closed');
    } catch (error) {
      log.error('Error closing database:', error);
      throw error;
    }
  }

  // Backup and restore methods
  async createBackupInfo(backupPath, type = 'manual', userId = null) {
    try {
      const stats = await fs.stat(backupPath);
      const filename = path.basename(backupPath);
      
      const result = this.db.prepare(`
        INSERT INTO backups (filename, file_path, size_bytes, type, created_by)
        VALUES (?, ?, ?, ?, ?)
      `).run(filename, backupPath, stats.size, type, userId);
      
      return result;
    } catch (error) {
      log.error('Error creating backup info:', error);
      throw error;
    }
  }

  async getBackupHistory(limit = 10) {
    return this.db.prepare(`
      SELECT b.*, u.full_name as created_by_name
      FROM backups b
      LEFT JOIN users u ON b.created_by = u.id
      ORDER BY b.created_at DESC
      LIMIT ?
    `).all(limit);
  }

  // User management methods
  async getUserByEmail(email) {
    return this.statements.getUserByEmail.get(email);
  }

  async getUserById(id) {
    return this.statements.getUserById.get(id);
  }

  async createUser(userData) {
    const bcrypt = require('bcrypt');
    const passwordHash = await bcrypt.hash(userData.password, 12);
    
    const result = this.db.prepare(`
      INSERT INTO users (username, email, password_hash, full_name, role, is_active)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(
      userData.username,
      userData.email,
      passwordHash,
      userData.full_name,
      userData.role || 'teacher',
      userData.is_active !== undefined ? userData.is_active : 1
    );

    await this.logAudit(null, 'CREATE', 'users', result.lastInsertRowid, null, {
      username: userData.username,
      email: userData.email,
      full_name: userData.full_name,
      role: userData.role
    });

    return result;
  }

  async updateUser(id, userData) {
    const oldData = this.statements.getUserById.get(id);
    
    let updateQuery = `
      UPDATE users 
      SET username = ?, email = ?, full_name = ?, role = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
    `;
    let params = [userData.username, userData.email, userData.full_name, userData.role, userData.is_active];

    if (userData.password) {
      const bcrypt = require('bcrypt');
      const passwordHash = await bcrypt.hash(userData.password, 12);
      updateQuery += ', password_hash = ?';
      params.push(passwordHash);
    }

    updateQuery += ' WHERE id = ?';
    params.push(id);

    const result = this.db.prepare(updateQuery).run(...params);
    
    await this.logAudit(null, 'UPDATE', 'users', id, oldData, userData);
    return result;
  }

  async updateLastLogin(userId) {
    return this.statements.updateLastLogin.run(userId);
  }

  async incrementFailedLogins(userId) {
    return this.statements.incrementFailedLogins.run(userId);
  }

  async resetFailedLogins(userId) {
    return this.statements.resetFailedLogins.run(userId);
  }

  async lockAccount(userId, lockUntil) {
    return this.statements.lockAccount.run(lockUntil.toISOString(), userId);
  }

  // Analytics and reporting methods
  async getPerformanceAnalytics(classLevel = null, term = null, academicYear = null) {
    let query = `
      SELECT 
        s.name as subject_name,
        COUNT(g.id) as total_grades,
        AVG(g.score) as average_score,
        MIN(g.score) as min_score,
        MAX(g.score) as max_score,
        COUNT(CASE WHEN g.score >= 85 THEN 1 END) as excellent_count,
        COUNT(CASE WHEN g.score >= 75 AND g.score < 85 THEN 1 END) as good_count,
        COUNT(CASE WHEN g.score >= 65 AND g.score < 75 THEN 1 END) as satisfactory_count,
        COUNT(CASE WHEN g.score < 65 THEN 1 END) as below_average_count
      FROM grades g
      JOIN subjects s ON g.subject_id = s.id
      JOIN students st ON g.student_id = st.id
      WHERE st.status = 'Active'
    `;

    let params = [];

    if (classLevel) {
      query += ' AND st.class_level = ?';
      params.push(classLevel);
    }

    if (term) {
      query += ' AND g.term = ?';
      params.push(term);
    }

    if (academicYear) {
      query += ' AND g.academic_year = ?';
      params.push(academicYear);
    }

    query += ' GROUP BY s.id, s.name ORDER BY s.name';

    return await this.query(query, params);
  }

  async getStudentPerformanceTrends(studentId, academicYear = null) {
    const year = academicYear || (await this.getSetting('academic_year')).value;
    
    return await this.query(`
      SELECT 
        g.term,
        s.name as subject_name,
        g.score,
        g.grade_letter,
        AVG(g.score) OVER (PARTITION BY g.subject_id ORDER BY g.term) as running_average
      FROM grades g
      JOIN subjects s ON g.subject_id = s.id
      WHERE g.student_id = ? AND g.academic_year = ?
      ORDER BY s.name, g.term
    `, [studentId, year]);
  }

  async getClassPerformanceComparison(academicYear = null) {
    const year = academicYear || (await this.getSetting('academic_year')).value;
    
    return await this.query(`
      SELECT 
        st.class_level,
        COUNT(DISTINCT st.id) as student_count,
        COUNT(g.id) as total_grades,
        AVG(g.score) as average_score,
        COUNT(CASE WHEN g.score >= 85 THEN 1 END) as excellent_count,
        ROUND(COUNT(CASE WHEN g.score >= 85 THEN 1 END) * 100.0 / COUNT(g.id), 2) as excellent_percentage
      FROM students st
      LEFT JOIN grades g ON st.id = g.student_id AND g.academic_year = ?
      WHERE st.status = 'Active'
      GROUP BY st.class_level
      ORDER BY st.class_level
    `, [year]);
  }

  // Data validation methods
  validateStudentData(data) {
    const errors = [];
    
    if (!data.name || data.name.trim().length < 2) {
      errors.push('Student name must be at least 2 characters long');
    }
    
    if (!data.student_id || data.student_id.trim().length < 3) {
      errors.push('Student ID must be at least 3 characters long');
    }
    
    if (!data.class_level) {
      errors.push('Class level is required');
    }
    
    if (data.gender && !['Male', 'Female'].includes(data.gender)) {
      errors.push('Gender must be either Male or Female');
    }
    
    if (data.date_of_birth) {
      const birthDate = new Date(data.date_of_birth);
      const today = new Date();
      const age = today.getFullYear() - birthDate.getFullYear();
      
      if (age < 3 || age > 25) {
        errors.push('Student age must be between 3 and 25 years');
      }
    }
    
    // Check for duplicate student ID
    const existing = this.db.prepare('SELECT id FROM students WHERE student_id = ? AND id != ?')
      .get(data.student_id, data.id || 0);
    
    if (existing) {
      errors.push('Student ID already exists');
    }
    
    return errors;
  }

  validateGradeData(data) {
    const errors = [];
    
    if (!data.student_id || !Number.isInteger(data.student_id)) {
      errors.push('Valid student ID is required');
    }
    
    if (!data.subject_id || !Number.isInteger(data.subject_id)) {
      errors.push('Valid subject ID is required');
    }
    
    if (!data.term || !['term1', 'term2', 'term3'].includes(data.term)) {
      errors.push('Valid term is required (term1, term2, or term3)');
    }
    
    if (data.score === undefined || data.score < 0 || data.score > 100) {
      errors.push('Score must be between 0 and 100');
    }
    
    if (!data.academic_year || data.academic_year.length !== 4) {
      errors.push('Valid academic year is required (YYYY format)');
    }
    
    return errors;
  }

  // Migration methods for schema updates
  async runMigrations() {
    const currentVersion = await this.getDatabaseVersion();
    const targetVersion = 1; // Current schema version
    
    if (currentVersion < targetVersion) {
      log.info(`Running database migrations from version ${currentVersion} to ${targetVersion}`);
      
      for (let version = currentVersion + 1; version <= targetVersion; version++) {
        await this.runMigration(version);
      }
      
      await this.setDatabaseVersion(targetVersion);
    }
  }

  async getDatabaseVersion() {
    try {
      const result = await this.getSetting('database_version');
      return result ? parseInt(result.value) : 0;
    } catch (error) {
      return 0;
    }
  }

  async setDatabaseVersion(version) {
    await this.setSetting('database_version', version.toString(), 'number');
  }

  async runMigration(version) {
    log.info(`Running migration for version ${version}`);
    
    switch (version) {
      case 1:
        // Initial schema - already created in createTables()
        break;
      // Add future migrations here
      default:
        log.warn(`Unknown migration version: ${version}`);
    }
  }

  // Health check method
  async healthCheck() {
    try {
      // Test basic database operations
      await this.query('SELECT 1');
      
      // Check connection pool
      const availableConnections = this.connectionPool.filter(conn => !conn.inUse).length;
      
      // Check WAL file size
      const walSize = await this.getFileSize(this.dbPath + '-wal');
      const walSizeMB = walSize / (1024 * 1024);
      
      // Get database statistics
      const stats = await this.getStatistics();
      
      return {
        status: 'healthy',
        database: {
          connected: true,
          path: this.dbPath,
          size: stats.diskUsage.database,
          walSize: walSizeMB
        },
        connectionPool: {
          total: this.maxConnections,
          available: availableConnections,
          inUse: this.maxConnections - availableConnections
        },
        statistics: stats,
        lastCheck: new Date().toISOString()
      };
    } catch (error) {
      log.error('Database health check failed:', error);
      return {
        status: 'unhealthy',
        error: error.message,
        lastCheck: new Date().toISOString()
      };
    }
  }
}

module.exports = DatabaseManager;