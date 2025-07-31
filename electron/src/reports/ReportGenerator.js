const PDFDocument = require('pdfkit');
const fs = require('fs').promises;
const path = require('path');
const { app } = require('electron');
const QRCode = require('qrcode');
const sharp = require('sharp');
const log = require('electron-log');

class ReportGenerator {
  /**
   * Constructs a new ReportGenerator instance.
   * 
   * @param {DatabaseManager} databaseManager - The database manager instance to use for generating reports.
   * 
   * @property {DatabaseManager} db - The database manager instance.
   * @property {string|null} outputDir - The output directory for generated reports, or null if it has not been set.
   * @property {Map<string, PDFDocument>} templateCache - A cache of loaded PDF templates.
   * @property {Object<string, PDFDocument.Font>} fonts - An object containing the PDF fonts used for generating reports.
   * @property {Object<string, string>} colors - An object containing the colors used for generating reports.
   * 
   * Initializes the ReportGenerator by loading PDF fonts and the output directory.
   */
  constructor(databaseManager) {
    this.db = databaseManager;
    this.outputDir = null;
    this.templateCache = new Map();
    this.fonts = {};
    this.colors = {
      primary: '#1D3557',
      secondary: '#2A9D8F',
      accent: '#F4A261',
      success: '#10B981',
      warning: '#F59E0B',
      error: '#E63946',
      text: '#374151',
      textLight: '#6B7280',
      background: '#F9FAFB'
    };
    
    this.initialize();
  }

  /**
   * Initializes the ReportGenerator instance.
   *
   * Sets the output directory for generated reports, loads the PDF fonts, and loads the default templates.
   *
   * @returns {Promise<void>} A promise that resolves when the initialization is complete.
   * @throws Will throw an error if the initialization fails.
   */
  async initialize() {
    try {
      // Set output directory
      const userData = app.getPath('userData');
      this.outputDir = path.join(userData, 'reports');
      await fs.mkdir(this.outputDir, { recursive: true });

      // Load fonts
      await this.loadFonts();

      // Load default templates
      await this.loadTemplates();

      log.info('ReportGenerator initialized successfully');
    } catch (error) {
      log.error('Failed to initialize ReportGenerator:', error);
      throw error;
    }
  }

  /**
   * Loads the PDF fonts.
   *
   * Loads the Roboto font family from the assets/fonts directory. If any of the font files
   * are not found, the system defaults will be used. If the entire fonts directory is not
   * found, the system defaults will be used.
   *
   * @returns {Promise<void>} A promise that resolves when the fonts have been loaded.
   * @throws Will throw an error if the font loading fails.
   */
  async loadFonts() {
    const fontsDir = path.join(__dirname, '..', '..', 'assets', 'fonts');
    
    try {
      this.fonts = {
        regular: path.join(fontsDir, 'Roboto-Regular.ttf'),
        bold: path.join(fontsDir, 'Roboto-Bold.ttf'),
        italic: path.join(fontsDir, 'Roboto-Italic.ttf'),
        light: path.join(fontsDir, 'Roboto-Light.ttf')
      };

      // Verify fonts exist, use system defaults if not available
      for (const [key, fontPath] of Object.entries(this.fonts)) {
        try {
          await fs.access(fontPath);
        } catch (error) {
          log.warn(`Font file not found: ${fontPath}, using system default`);
          delete this.fonts[key];
        }
      }
    } catch (error) {
      log.warn('Fonts directory not found, using system defaults');
      this.fonts = {};
    }
  }

  /**
   * Loads the default templates for different grading systems.
   *
   * Loads the standard templates for Primary Leaving Examinations (PLE), Uganda
   * Certificate of Education (UCE), and Uganda Advanced Certificate of Education
   * (UACE). The templates are stored in the template cache for later use.
   *
   * @returns {Promise<void>} A promise that resolves when the templates have been
   * loaded.
   * @throws Will throw an error if the template loading fails.
   */
  async loadTemplates() {
    // Load default templates for different grading systems
    this.templateCache.set('PLE_STANDARD', await this.createPLETemplate());
    this.templateCache.set('UCE_STANDARD', await this.createUCETemplate());
    this.templateCache.set('UACE_STANDARD', await this.createUACETemplate());
  }

  /**
   * Generates a PDF report based on the given report data.
   * 
   * The method takes a report data object as an argument, which should contain the following properties:
   * 
   * - `student`: The student object to generate the report for.
   * - `grades`: The grades object to include in the report.
   * - `term`: The term for which the report is being generated.
   * - `academicYear`: The academic year for which the report is being generated.
   * - `template`: The name of the template to use for the report. Defaults to 'STANDARD'.
   * - `options`: An object containing additional options for the report generation.
   * 
   * The method generates a PDF file in the configured output directory with a unique filename based on the student's name, term, and academic year.
   * 
   * @param {Object} reportData The report data object.
   * @returns {Promise<string>} A promise that resolves with the path to the generated PDF file.
   * @throws Will throw an error if the report generation fails.
   */
  async generatePDF(reportData) {
    try {
      const {
        student,
        grades,
        term,
        academicYear,
        template = 'STANDARD',
        options = {}
      } = reportData;

      // Validate required data
      this.validateReportData(reportData);

      // Determine template based on student class
      const templateType = this.getTemplateType(student.class_level);
      const templateKey = `${templateType}_${template}`;

      // Generate unique filename
      const fileName = this.generateFileName(student, term, academicYear);
      const filePath = path.join(this.outputDir, fileName);

      // Create PDF document
      const doc = new PDFDocument({ 
        size: 'A4', 
        margin: 50,
        info: {
          Title: `Report Card - ${student.name}`,
          Author: 'Marka Report Generator',
          Subject: 'Student Report Card',
          Creator: 'Marka Report Generator v' + app.getVersion()
        }
      });

      // Stream to file
      const stream = doc.pipe(fs.createWriteStream(filePath));

      // Generate report based on template
      await this.generateReportContent(doc, reportData, templateKey, options);

      // Finalize PDF
      doc.end();

      // Wait for stream to finish
      await new Promise((resolve, reject) => {
        stream.on('finish', resolve);
        stream.on('error', reject);
      });

      log.info(`PDF report generated: ${fileName}`);
      return filePath;

    } catch (error) {
      log.error('PDF generation failed:', error);
      throw error;
    }
  }

  async generateBulkReports(criteria) {
    try {
      const {
        classLevel,
        term,
        academicYear,
        template = 'STANDARD',
        outputFormat = 'individual', // 'individual' or 'combined'
        options = {}
      } = criteria;

      // Get students based on criteria
      const students = await this.db.getStudents({ class_level: classLevel });
      
      if (students.length === 0) {
        throw new Error('No students found matching criteria');
      }

      const results = [];
      const batchSize = 10; // Process in batches to avoid memory issues

      for (let i = 0; i < students.length; i += batchSize) {
        const batch = students.slice(i, i + batchSize);
        const batchPromises = batch.map(async (student) => {
          try {
            // Get student grades
            const grades = await this.db.getGrades(student.id, term, academicYear);
            
            // Generate individual report
            const filePath = await this.generatePDF({
              student,
              grades,
              term,
              academicYear,
              template,
              options
            });

            return {
              success: true,
              student: student.name,
              filePath
            };
          } catch (error) {
            log.error(`Failed to generate report for ${student.name}:`, error);
            return {
              success: false,
              student: student.name,
              error: error.message
            };
          }
        });

        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);

        // Log progress
        log.info(`Generated batch ${Math.floor(i / batchSize) + 1} of ${Math.ceil(students.length / batchSize)}`);
      }

      // Create summary report
      const summary = {
        total: students.length,
        successful: results.filter(r => r.success).length,
        failed: results.filter(r => !r.success).length,
        results
      };

      log.info(`Bulk report generation completed: ${summary.successful}/${summary.total} successful`);
      return summary;

    } catch (error) {
      log.error('Bulk report generation failed:', error);
      throw error;
    }
  }

  async generateReportContent(doc, reportData, templateKey, options) {
    const { student, grades, term, academicYear } = reportData;

    // Get school information
    const schoolInfo = await this.getSchoolInfo();

    // Add header
    await this.addReportHeader(doc, schoolInfo, options);

    // Add student information
    this.addStudentInfo(doc, student, term, academicYear);

    // Add grades table
    await this.addGradesTable(doc, student, grades, templateKey);

    // Add performance summary
    await this.addPerformanceSummary(doc, student, grades, templateKey);

    // Add conduct and attendance
    await this.addConductAndAttendance(doc, student, term, academicYear);

    // Add comments section
    this.addCommentsSection(doc);

    // Add footer with signatures
    this.addReportFooter(doc, schoolInfo);

    // Add QR code for verification
    await this.addQRCode(doc, student, term, academicYear);
  }

  async addReportHeader(doc, schoolInfo, options = {}) {
    const headerHeight = 120;
    let yPosition = 50;

    // School logo (if available)
    if (schoolInfo.logo && options.includeLogo !== false) {
      try {
        // Resize logo to fit
        const logoBuffer = await sharp(schoolInfo.logo)
          .resize(80, 80, { fit: 'inside' })
          .png()
          .toBuffer();

        doc.image(logoBuffer, 50, yPosition, { width: 80, height: 80 });
      } catch (error) {
        log.warn('Failed to add school logo:', error);
      }
    }

    // School information
    const textX = schoolInfo.logo ? 150 : 50;
    
    // School name
    doc.fontSize(20)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text(schoolInfo.name, textX, yPosition, { align: 'left' });

    yPosition += 25;

    // School details
    doc.fontSize(10)
       .fillColor(this.colors.text)
       .font(this.fonts.regular || 'Helvetica')
       .text(schoolInfo.address, textX, yPosition)
       .text(`Tel: ${schoolInfo.phone} | Email: ${schoolInfo.email}`, textX, yPosition + 12);

    // Report title
    yPosition += 40;
    doc.fontSize(16)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text('STUDENT REPORT CARD', 50, yPosition, { align: 'center' });

    // Add decorative line
    yPosition += 25;
    doc.strokeColor(this.colors.secondary)
       .lineWidth(2)
       .moveTo(50, yPosition)
       .lineTo(550, yPosition)
       .stroke();

    return yPosition + 20;
  }

  addStudentInfo(doc, student, term, academicYear) {
    const startY = 200;
    let yPosition = startY;

    // Create info box
    doc.rect(50, yPosition, 500, 80)
       .strokeColor(this.colors.secondary)
       .fillColor(this.colors.background)
       .fillAndStroke();

    yPosition += 15;

    // Student information in two columns
    const leftX = 70;
    const rightX = 320;

    doc.fontSize(11)
       .fillColor(this.colors.text)
       .font(this.fonts.regular || 'Helvetica');

    // Left column
    doc.text('Student Name:', leftX, yPosition)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text(student.name, leftX + 80, yPosition);

    yPosition += 15;
    doc.font(this.fonts.regular || 'Helvetica')
       .text('Student ID:', leftX, yPosition)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text(student.student_id, leftX + 80, yPosition);

    // Right column
    yPosition = startY + 15;
    doc.font(this.fonts.regular || 'Helvetica')
       .text('Class:', rightX, yPosition)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text(student.class_level, rightX + 80, yPosition);

    yPosition += 15;
    doc.font(this.fonts.regular || 'Helvetica')
       .text('Term:', rightX, yPosition)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text(`${term.replace('term', 'Term ')} ${academicYear}`, rightX + 80, yPosition);

    yPosition += 15;
    doc.font(this.fonts.regular || 'Helvetica')
       .text('Date of Birth:', rightX, yPosition)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text(student.date_of_birth || 'N/A', rightX + 80, yPosition);

    return startY + 100;
  }

  async addGradesTable(doc, student, grades, templateKey) {
    const startY = 300;
    let yPosition = startY;

    // Table header
    doc.fontSize(12)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text('ACADEMIC PERFORMANCE', 50, yPosition);

    yPosition += 25;

    // Table dimensions
    const tableWidth = 500;
    const colWidths = [200, 80, 60, 80, 80];
    const rowHeight = 25;
    let currentX = 50;

    // Draw table header
    const headers = ['Subject', 'Score', 'Grade', 'Position', 'Remarks'];
    
    // Header background
    doc.rect(50, yPosition, tableWidth, rowHeight)
       .fillColor(this.colors.secondary)
       .fill();

    doc.fillColor('white')
       .fontSize(10)
       .font(this.fonts.bold || 'Helvetica-Bold');

    headers.forEach((header, index) => {
      doc.text(header, currentX + 5, yPosition + 8, {
        width: colWidths[index] - 10,
        align: 'center'
      });
      currentX += colWidths[index];
    });

    yPosition += rowHeight;
    currentX = 50;

    // Calculate grades and positions
    const processedGrades = await this.processGrades(grades, student.class_level);

    // Draw data rows
    doc.fillColor(this.colors.text)
       .font(this.fonts.regular || 'Helvetica');

    processedGrades.forEach((grade, index) => {
      // Alternate row colors
      if (index % 2 === 1) {
        doc.rect(50, yPosition, tableWidth, rowHeight)
           .fillColor('#F9FAFB')
           .fill();
      }

      currentX = 50;

      // Subject name
      doc.fillColor(this.colors.text)
         .text(grade.subject_name, currentX + 5, yPosition + 8, {
           width: colWidths[0] - 10,
           align: 'left'
         });
      currentX += colWidths[0];

      // Score
      doc.text(grade.score.toString(), currentX + 5, yPosition + 8, {
        width: colWidths[1] - 10,
        align: 'center'
      });
      currentX += colWidths[1];

      // Grade
      doc.fillColor(this.getGradeColor(grade.grade_letter))
         .text(grade.grade_letter, currentX + 5, yPosition + 8, {
           width: colWidths[2] - 10,
           align: 'center'
         });
      currentX += colWidths[2];

      // Position
      doc.fillColor(this.colors.text)
         .text(grade.position || 'N/A', currentX + 5, yPosition + 8, {
           width: colWidths[3] - 10,
           align: 'center'
         });
      currentX += colWidths[3];

      // Remarks
      doc.text(grade.remarks || this.getGradeRemark(grade.score), currentX + 5, yPosition + 8, {
        width: colWidths[4] - 10,
        align: 'center'
      });

      yPosition += rowHeight;
    });

    // Draw table borders
    this.drawTableBorders(doc, 50, startY + 25, tableWidth, (processedGrades.length + 1) * rowHeight, colWidths);

    return yPosition + 20;
  }

  async addPerformanceSummary(doc, student, grades, templateKey) {
    const startY = doc.y + 20;
    let yPosition = startY;

    // Performance summary box
    doc.rect(50, yPosition, 240, 120)
       .strokeColor(this.colors.secondary)
       .fillColor(this.colors.background)
       .fillAndStroke();

    yPosition += 15;

    doc.fontSize(11)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text('PERFORMANCE SUMMARY', 60, yPosition);

    yPosition += 20;

    // Calculate summary statistics
    const summary = await this.calculatePerformanceSummary(grades, student.class_level);

    doc.fontSize(10)
       .fillColor(this.colors.text)
       .font(this.fonts.regular || 'Helvetica');

    const summaryItems = [
      ['Total Subjects:', summary.totalSubjects],
      ['Average Score:', `${summary.averageScore}%`],
      ['Overall Grade:', summary.overallGrade],
      ['Class Position:', summary.classPosition || 'N/A'],
      ['Total Points:', summary.totalPoints || 'N/A']
    ];

    summaryItems.forEach(([label, value]) => {
      doc.text(label, 60, yPosition)
         .font(this.fonts.bold || 'Helvetica-Bold')
         .text(value, 150, yPosition);
      
      yPosition += 15;
      doc.font(this.fonts.regular || 'Helvetica');
    });

    // Performance chart (simple bar representation)
    this.addPerformanceChart(doc, 310, startY, summary);

    return Math.max(startY + 140, doc.y + 20);
  }

  addPerformanceChart(doc, x, y, summary) {
    const chartWidth = 200;
    const chartHeight = 100;

    // Chart background
    doc.rect(x, y, chartWidth, chartHeight)
       .strokeColor(this.colors.secondary)
       .fillColor('white')
       .fillAndStroke();

    // Chart title
    doc.fontSize(10)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text('Grade Distribution', x + 10, y + 10);

    // Simple bar chart showing grade distribution
    const gradeDistribution = summary.gradeDistribution || {};
    const grades = ['A', 'B', 'C', 'D', 'E', 'F'];
    const barWidth = 25;
    const maxBarHeight = 60;
    const maxCount = Math.max(...Object.values(gradeDistribution), 1);

    let barX = x + 15;
    const barY = y + 70;

    grades.forEach(grade => {
      const count = gradeDistribution[grade] || 0;
      const barHeight = (count / maxCount) * maxBarHeight;

      // Draw bar
      doc.rect(barX, barY - barHeight, barWidth, barHeight)
         .fillColor(this.getGradeColor(grade))
         .fill();

      // Draw grade label
      doc.fontSize(8)
         .fillColor(this.colors.text)
         .text(grade, barX + 8, barY + 5);

      barX += 30;
    });
  }

  async addConductAndAttendance(doc, student, term, academicYear) {
    const startY = doc.y + 20;
    let yPosition = startY;

    // Get conduct and attendance data
    const conductData = await this.getConductData(student.id, term, academicYear);
    const attendanceData = await this.getAttendanceData(student.id, term, academicYear);

    // Conduct section
    doc.rect(50, yPosition, 240, 80)
       .strokeColor(this.colors.secondary)
       .fillColor(this.colors.background)
       .fillAndStroke();

    doc.fontSize(11)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text('CONDUCT & DISCIPLINE', 60, yPosition + 15);

    yPosition += 35;

    doc.fontSize(10)
       .fillColor(this.colors.text)
       .font(this.fonts.regular || 'Helvetica');

    const conductItems = [
      ['Behavior Grade:', conductData.behavior_grade || 'Good'],
      ['Discipline Score:', `${conductData.discipline_score || 4}/5`],
      ['Punctuality:', conductData.punctuality || 'Good']
    ];

    conductItems.forEach(([label, value]) => {
      doc.text(label, 60, yPosition)
         .font(this.fonts.bold || 'Helvetica-Bold')
         .text(value, 150, yPosition);
      
      yPosition += 15;
      doc.font(this.fonts.regular || 'Helvetica');
    });

    // Attendance section
    yPosition = startY;
    doc.rect(310, yPosition, 240, 80)
       .strokeColor(this.colors.secondary)
       .fillColor(this.colors.background)
       .fillAndStroke();

    doc.fontSize(11)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text('ATTENDANCE RECORD', 320, yPosition + 15);

    yPosition += 35;

    doc.fontSize(10)
       .fillColor(this.colors.text)
       .font(this.fonts.regular || 'Helvetica');

    const attendanceItems = [
      ['Days Present:', attendanceData.present_days || 0],
      ['Days Absent:', attendanceData.absent_days || 0],
      ['Attendance %:', `${attendanceData.attendance_percentage || 100}%`]
    ];

    attendanceItems.forEach(([label, value]) => {
      doc.text(label, 320, yPosition)
         .font(this.fonts.bold || 'Helvetica-Bold')
         .text(value, 410, yPosition);
      
      yPosition += 15;
      doc.font(this.fonts.regular || 'Helvetica');
    });

    return startY + 100;
  }

  addCommentsSection(doc) {
    const startY = doc.y + 30;
    let yPosition = startY;

    // Comments section
    doc.fontSize(11)
       .fillColor(this.colors.primary)
       .font(this.fonts.bold || 'Helvetica-Bold')
       .text('TEACHER\'S COMMENTS', 50, yPosition);

    yPosition += 20;

    // Comment box
    doc.rect(50, yPosition, 500, 60)
       .strokeColor(this.colors.secondary)
       .stroke();

    // Add comment lines
    for (let i = 0; i < 3; i++) {
      doc.moveTo(60, yPosition + 15 + (i * 15))
         .lineTo(540, yPosition + 15 + (i * 15))
         .strokeColor('#E5E7EB')
         .stroke();
    }

    return yPosition + 80;
  }

  addReportFooter(doc, schoolInfo) {
    const startY = doc.y + 30;
    let yPosition = startY;

    // Signatures section
    doc.fontSize(10)
       .fillColor(this.colors.text)
       .font(this.fonts.regular || 'Helvetica');

    // Class teacher signature
    doc.text('Class Teacher: ___________________', 50, yPosition);
    doc.text('Date: ___________', 50, yPosition + 20);

    // Head teacher signature
    doc.text('Head Teacher: ___________________', 320, yPosition);
    doc.text('Date: ___________', 320, yPosition + 20);

    yPosition += 60;

    // School motto or footer text
    if (schoolInfo.motto) {
      doc.fontSize(8)
         .fillColor(this.colors.textLight)
         .text(`"${schoolInfo.motto}"`, 50, yPosition, { align: 'center' });
    }

    // Report generation info
    yPosition += 20;
    doc.fontSize(7)
       .fillColor(this.colors.textLight)
       .text(`Generated on ${new Date().toLocaleDateString()} by Marka Report Generator v${app.getVersion()}`, 
             50, yPosition, { align: 'center' });
  }

  async addQRCode(doc, student, term, academicYear) {
    try {
      // Generate verification data
      const verificationData = {
        studentId: student.student_id,
        name: student.name,
        class: student.class_level,
        term,
        academicYear,
        generated: new Date().toISOString(),
        hash: this.generateVerificationHash(student, term, academicYear)
      };

      // Generate QR code
      const qrDataURL = await QRCode.toDataURL(JSON.stringify(verificationData), {
        width: 80,
        margin: 1,
        color: {
          dark: this.colors.primary,
          light: '#FFFFFF'
        }
      });

      // Convert data URL to buffer
      const qrBuffer = Buffer.from(qrDataURL.split(',')[1], 'base64');

      // Add QR code to bottom right
      doc.image(qrBuffer, 470, doc.page.height - 130, { width: 80, height: 80 });

      // Add verification text
      doc.fontSize(6)
         .fillColor(this.colors.textLight)
         .text('Scan for verification', 470, doc.page.height - 45, { width: 80, align: 'center' });

    } catch (error) {
      log.warn('Failed to add QR code:', error);
    }
  }

  // Helper methods

  validateReportData(reportData) {
    const { student, grades, term, academicYear } = reportData;

    if (!student || !student.id) {
      throw new Error('Valid student data is required');
    }

    if (!grades || !Array.isArray(grades)) {
      throw new Error('Valid grades array is required');
    }

    if (!term || !['term1', 'term2', 'term3'].includes(term)) {
      throw new Error('Valid term is required');
    }

    if (!academicYear) {
      throw new Error('Academic year is required');
    }
  }

  getTemplateType(classLevel) {
    if (classLevel === 'P7') return 'PLE';
    if (classLevel === 'S4') return 'UCE';
    if (classLevel === 'S6') return 'UACE';
    return 'STANDARD';
  }

  generateFileName(student, term, academicYear) {
    const sanitizedName = student.name.replace(/[^a-zA-Z0-9]/g, '_');
    const timestamp = new Date().toISOString().split('T')[0];
    return `${sanitizedName}_${student.student_id}_${term}_${academicYear}_${timestamp}.pdf`;
  }

  async getSchoolInfo() {
    try {
      const settings = await this.db.getAllSettings();
      return {
        name: settings.school_name?.value || 'Sample School',
        address: settings.school_address?.value || 'School Address',
        phone: settings.school_phone?.value || '+256 XXX XXXXXX',
        email: settings.school_email?.value || 'info@school.edu',
        motto: settings.school_motto?.value || 'Excellence in Education',
        logo: settings.school_logo?.value || null
      };
    } catch (error) {
      log.error('Failed to get school info:', error);
      return {
        name: 'Sample School',
        address: 'School Address',
        phone: '+256 XXX XXXXXX',
        email: 'info@school.edu',
        motto: 'Excellence in Education',
        logo: null
      };
    }
  }

  async processGrades(grades, classLevel) {
    return grades.map(grade => ({
      ...grade,
      grade_letter: this.calculateGradeLetter(grade.score, classLevel),
      position: null // Would be calculated based on class performance
    }));
  }

  calculateGradeLetter(score, classLevel) {
    if (classLevel === 'P7') {
      // PLE grading system
      if (score >= 90) return 'D1';
      if (score >= 80) return 'D2';
      if (score >= 70) return 'C3';
      if (score >= 60) return 'C4';
      if (score >= 50) return 'C5';
      if (score >= 40) return 'C6';
      return 'P7';
    } else {
      // UCE/UACE grading system
      if (score >= 85) return 'A';
      if (score >= 75) return 'B';
      if (score >= 65) return 'C';
      if (score >= 55) return 'D';
      if (score >= 45) return 'E';
      return 'F';
    }
  }

  getGradeColor(grade) {
    const colors = {
      'A': this.colors.success,
      'B': '#3B82F6',
      'C': this.colors.warning,
      'D': this.colors.error,
      'E': this.colors.error,
      'F': '#6B7280',
      'D1': this.colors.success,
      'D2': this.colors.success,
      'C3': '#3B82F6',
      'C4': '#3B82F6',
      'C5': this.colors.warning,
      'C6': this.colors.warning,
      'P7': this.colors.error
    };
    return colors[grade] || this.colors.text;
  }

  getGradeRemark(score) {
    if (score >= 85) return 'Excellent';
    if (score >= 75) return 'Very Good';
    if (score >= 65) return 'Good';
    if (score >= 55) return 'Satisfactory';
    if (score >= 45) return 'Fair';
    return 'Needs Improvement';
  }

  async calculatePerformanceSummary(grades, classLevel) {
    const totalSubjects = grades.length;
    const totalScore = grades.reduce((sum, grade) => sum + grade.score, 0);
    const averageScore = totalSubjects > 0 ? Math.round(totalScore / totalSubjects) : 0;
    
    // Calculate grade distribution
    const gradeDistribution = {};
    grades.forEach(grade => {
      const letter = this.calculateGradeLetter(grade.score, classLevel);
      const baseLetter = letter.length > 1 ? letter[0] : letter;
      gradeDistribution[baseLetter] = (gradeDistribution[baseLetter] || 0) + 1;
    });

    return {
      totalSubjects,
      averageScore,
      overallGrade: this.calculateGradeLetter(averageScore, classLevel),
      gradeDistribution,
      classPosition: null, // Would need class-wide data
      totalPoints: classLevel === 'S6' ? this.calculateUACEPoints(grades) : null
    };
  }

  calculateUACEPoints(grades) {
    // UACE points calculation
    const pointsMap = { 'A': 6, 'B': 5, 'C': 4, 'D': 3, 'E': 2, 'O': 1, 'F': 0 };
    return grades.reduce((sum, grade) => {
      const letter = this.calculateGradeLetter(grade.score, 'S6');
      return sum + (pointsMap[letter] || 0);
    }, 0);
  }

  async getConductData(studentId, term, academicYear) {
    try {
      const conduct = await this.db.query(
        'SELECT * FROM conduct WHERE student_id = ? AND term = ? AND academic_year = ?',
        [studentId, term, academicYear]
      );
      return conduct[0] || {};
    } catch (error) {
      log.error('Failed to get conduct data:', error);
      return {};
    }
  }

  async getAttendanceData(studentId, term, academicYear) {
    try {
      const attendance = await this.db.query(`
        SELECT 
          COUNT(CASE WHEN status = 'Present' THEN 1 END) as present_days,
          COUNT(CASE WHEN status = 'Absent' THEN 1 END) as absent_days,
          ROUND(COUNT(CASE WHEN status = 'Present' THEN 1 END) * 100.0 / COUNT(*), 1) as attendance_percentage
        FROM attendance 
        WHERE student_id = ? AND term = ? AND academic_year = ?
      `, [studentId, term, academicYear]);
      
      return attendance[0] || { present_days: 0, absent_days: 0, attendance_percentage: 100 };
    } catch (error) {
      log.error('Failed to get attendance data:', error);
      return { present_days: 0, absent_days: 0, attendance_percentage: 100 };
    }
  }

  drawTableBorders(doc, x, y, width, height, colWidths) {
    // Draw outer border
    doc.rect(x, y, width, height)
       .strokeColor(this.colors.secondary)
       .stroke();

    // Draw vertical lines
    let currentX = x;
    colWidths.slice(0, -1).forEach(colWidth => {
      currentX += colWidth;
      doc.moveTo(currentX, y)
         .lineTo(currentX, y + height)
         .stroke();
    });

    // Draw horizontal lines
    const rowHeight = height / (Math.floor(height / 25)); // Approximate row height
    for (let i = 1; i < Math.floor(height / 25); i++) {
      doc.moveTo(x, y + (i * 25))
         .lineTo(x + width, y + (i * 25))
         .strokeColor('#E5E7EB')
         .stroke();
    }
  }

  generateVerificationHash(student, term, academicYear) {
    const crypto = require('crypto');
    const data = `${student.student_id}:${term}:${academicYear}:${new Date().toDateString()}`;
    return crypto.createHash('sha256').update(data).digest('hex').substring(0, 16);
  }

  // Template creation methods
  async createPLETemplate() {
    return {
      name: 'PLE Standard Template',
      type: 'PLE',
      gradingSystem: 'division',
      subjects: ['English', 'Mathematics', 'Science', 'Social Studies'],
      showAggregate: true,
      showDivision: true
    };
  }

  async createUCETemplate() {
    return {
      name: 'UCE Standard Template',
      type: 'UCE',
      gradingSystem: 'letter',
      subjects: ['English', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'History', 'Geography'],
      showAggregate: false,
      showDivision: false
    };
  }

  async createUACETemplate() {
    return {
      name: 'UACE Standard Template',
      type: 'UACE',
      gradingSystem: 'points',
      subjects: [], // Variable based on combination
      showPoints: true,
      showUniversityEligibility: true
    };
  }

  // Cleanup method
  cleanup() {
    this.templateCache.clear();
    log.info('ReportGenerator cleanup completed');
  }
}

module.exports = ReportGenerator;