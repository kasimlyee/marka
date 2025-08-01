const fs = require('fs').promises;
const path = require('path');
const { app, dialog } = require('electron');
const log = require('electron-log');
const csv = require('csv-parser');
const ExcelJS = require('exceljs');
const { pipeline } = require('stream/promises');
const archiver = require('archiver');
const extract = require('extract-zip');
const crypto = require('crypto');
const { Mutex } = require('async-mutex');

class FileManager {
  constructor(options = {}) {
    this.options = {
      uploadDir: path.join(app.getPath('userData'), 'uploads'),
      maxFileSize: 50 * 1024 * 1024, // 50MB
      allowedExtensions: ['.csv', '.xlsx', '.xls', '.pdf', '.jpg', '.png'],
      encryptionKey: process.env.FILE_ENCRYPTION_KEY || 'default-file-key',
      ...options
    };

    this.fileMutex = new Mutex();
    this.ensureDirectories();
  }

  async ensureDirectories() {
    try {
      await fs.mkdir(this.options.uploadDir, { recursive: true });
    } catch (error) {
      log.error('Failed to create upload directory:', error);
      throw error;
    }
  }

  /**
   * Imports student data from a file
   * @param {string} filePath Path to the import file
   * @param {string} [format] File format (auto-detected if not provided)
   * @returns {Promise<Array<Object>>} Imported student data
   */
  async importStudents(filePath, format) {
    const release = await this.fileMutex.acquire();
    try {
      // Validate file
      await this.validateFile(filePath);

      // Determine format if not provided
      const fileFormat = format || this.detectFileFormat(filePath);

      // Process based on format
      switch (fileFormat) {
        case 'csv':
          return await this.importCSV(filePath);
        case 'excel':
          return await this.importExcel(filePath);
        default:
          throw new Error(`Unsupported file format: ${fileFormat}`);
      }
    } finally {
      release();
    }
  }

  /**
   * Exports student data to a file
   * @param {string} outputPath Path to save the exported file
   * @param {string} format Export format
   * @param {Array<Object>} data Data to export
   * @returns {Promise<string>} Path to the exported file
   */
  async exportStudents(outputPath, format = 'csv', data) {
    const release = await this.fileMutex.acquire();
    try {
      // Ensure directory exists
      await fs.mkdir(path.dirname(outputPath), { recursive: true });

      // Process based on format
      switch (format.toLowerCase()) {
        case 'csv':
          return await this.exportCSV(outputPath, data);
        case 'xlsx':
          return await this.exportExcel(outputPath, data);
        case 'pdf':
          return await this.exportPDF(outputPath, data);
        case 'zip':
          return await this.exportZIP(outputPath, data);
        default:
          throw new Error(`Unsupported export format: ${format}`);
      }
    } finally {
      release();
    }
  }

  async importCSV(filePath) {
    const results = [];
    try {
      await pipeline(
        fs.createReadStream(filePath),
        csv(),
        async function* (source) {
          for await (const chunk of source) {
            results.push(chunk);
          }
        }
      );

      log.info(`Imported ${results.length} records from CSV`);
      return results;
    } catch (error) {
      log.error('CSV import failed:', error);
      throw error;
    }
  }

  async importExcel(filePath) {
    try {
      const workbook = new ExcelJS.Workbook();
      await workbook.xlsx.readFile(filePath);

      const worksheet = workbook.worksheets[0];
      const results = [];

      worksheet.eachRow({ includeEmpty: false }, (row, rowNumber) => {
        if (rowNumber === 1) return; // Skip header row

        const rowData = {};
        row.eachCell({ includeEmpty: true }, (cell, colNumber) => {
          const header = worksheet.getRow(1).getCell(colNumber).value;
          rowData[header] = cell.value;
        });

        results.push(rowData);
      });

      log.info(`Imported ${results.length} records from Excel`);
      return results;
    } catch (error) {
      log.error('Excel import failed:', error);
      throw error;
    }
  }

  async exportCSV(outputPath, data) {
    try {
      const headers = Object.keys(data[0] || {});
      let csvContent = headers.join(',') + '\n';

      for (const item of data) {
        const row = headers.map(header => {
          let value = item[header];
          if (typeof value === 'string' && value.includes(',')) {
            value = `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        }).join(',');
        csvContent += row + '\n';
      }

      await fs.writeFile(outputPath, csvContent);
      log.info(`Exported ${data.length} records to CSV at ${outputPath}`);
      return outputPath;
    } catch (error) {
      log.error('CSV export failed:', error);
      throw error;
    }
  }

  async exportExcel(outputPath, data) {
    try {
      const workbook = new ExcelJS.Workbook();
      workbook.creator = 'Marka';
      workbook.created = new Date();

      const worksheet = workbook.addWorksheet('Students');

      // Add headers
      if (data.length > 0) {
        const headers = Object.keys(data[0]);
        worksheet.addRow(headers);

        // Add data rows
        data.forEach(item => {
          const row = headers.map(header => item[header]);
          worksheet.addRow(row);
        });

        // Auto-fit columns
        worksheet.columns.forEach(column => {
          let maxLength = 0;
          column.eachCell({ includeEmpty: true }, cell => {
            const cellLength = cell.value ? cell.value.toString().length : 0;
            maxLength = Math.max(maxLength, cellLength);
          });
          column.width = Math.min(Math.max(maxLength + 2, 10), 50);
        });
      }

      await workbook.xlsx.writeFile(outputPath);
      log.info(`Exported ${data.length} records to Excel at ${outputPath}`);
      return outputPath;
    } catch (error) {
      log.error('Excel export failed:', error);
      throw error;
    }
  }

  async exportPDF(outputPath, data) {
    try {
      const PDFDocument = require('pdfkit');
      const doc = new PDFDocument();

      await pipeline(
        doc,
        fs.createWriteStream(outputPath)
      );

      // Add title
      doc.fontSize(20).text('Student Records', { align: 'center' });
      doc.moveDown();

      // Add table
      if (data.length > 0) {
        const headers = Object.keys(data[0]);
        const columnWidths = this.calculateColumnWidths(headers, doc);

        // Draw table headers
        this.drawTableRow(doc, headers, columnWidths, true);

        // Draw data rows
        data.forEach(item => {
          const row = headers.map(header => item[header]);
          this.drawTableRow(doc, row, columnWidths);
        });
      }

      doc.end();
      log.info(`Exported ${data.length} records to PDF at ${outputPath}`);
      return outputPath;
    } catch (error) {
      log.error('PDF export failed:', error);
      throw error;
    }
  }

  async exportZIP(outputPath, data) {
    try {
      const archive = archiver('zip', { zlib: { level: 9 } });
      const outputStream = fs.createWriteStream(outputPath);

      await new Promise((resolve, reject) => {
        archive.pipe(outputStream);

        // Add CSV version
        archive.append(this.convertToCSV(data), { name: 'students.csv' });

        // Add JSON version
        archive.append(JSON.stringify(data, null, 2), { name: 'students.json' });

        // Add PDF version
        const pdfDoc = this.createPDFDocument(data);
        archive.append(pdfDoc, { name: 'students.pdf' });

        outputStream.on('close', resolve);
        outputStream.on('error', reject);
        archive.finalize();
      });

      log.info(`Exported ${data.length} records to ZIP at ${outputPath}`);
      return outputPath;
    } catch (error) {
      log.error('ZIP export failed:', error);
      throw error;
    }
  }

  calculateColumnWidths(headers, doc) {
    return headers.map(header => {
      const width = doc.widthOfString(header) + 20;
      return Math.min(width, 200);
    });
  }

  drawTableRow(doc, row, columnWidths, isHeader = false) {
    const rowHeight = 20;
    const startY = doc.y;

    // Draw cell backgrounds and borders
    let x = doc.x;
    for (let i = 0; i < row.length; i++) {
      doc.rect(x, startY, columnWidths[i], rowHeight)
        .fillAndStroke(isHeader ? '#f0f0f0' : 'white', 'black');
      x += columnWidths[i];
    }

    // Draw text
    x = doc.x;
    for (let i = 0; i < row.length; i++) {
      doc.font(isHeader ? 'Helvetica-Bold' : 'Helvetica')
         .fontSize(isHeader ? 12 : 10)
         .text(row[i], x + 5, startY + 5, {
           width: columnWidths[i] - 10,
           height: rowHeight - 10,
           align: 'left'
         });
      x += columnWidths[i];
    }

    doc.moveDown();
  }

  convertToCSV(data) {
    if (data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    let csvContent = headers.join(',') + '\n';

    for (const item of data) {
      const row = headers.map(header => {
        let value = item[header];
        if (typeof value === 'string' && value.includes(',')) {
          value = `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      }).join(',');
      csvContent += row + '\n';
    }

    return csvContent;
  }

  createPDFDocument(data) {
    const PDFDocument = require('pdfkit');
    const doc = new PDFDocument();
    const buffers = [];
    
    doc.on('data', buffers.push.bind(buffers));
    
    // Add title
    doc.fontSize(20).text('Student Records', { align: 'center' });
    doc.moveDown();

    // Add table if data exists
    if (data.length > 0) {
      const headers = Object.keys(data[0]);
      const columnWidths = this.calculateColumnWidths(headers, doc);

      // Draw table headers
      this.drawTableRow(doc, headers, columnWidths, true);

      // Draw data rows
      data.forEach(item => {
        const row = headers.map(header => item[header]);
        this.drawTableRow(doc, row, columnWidths);
      });
    }

    doc.end();
    return Buffer.concat(buffers);
  }

  async validateFile(filePath) {
    // Check file exists
    try {
      await fs.access(filePath);
    } catch {
      throw new Error('File does not exist');
    }

    // Check file size
    const stats = await fs.stat(filePath);
    if (stats.size > this.options.maxFileSize) {
      throw new Error(`File size exceeds limit of ${this.options.maxFileSize / 1024 / 1024}MB`);
    }

    // Check file extension
    const ext = path.extname(filePath).toLowerCase();
    if (!this.options.allowedExtensions.includes(ext)) {
      throw new Error(`File type ${ext} is not allowed`);
    }
  }

  detectFileFormat(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    switch (ext) {
      case '.csv':
        return 'csv';
      case '.xlsx':
      case '.xls':
        return 'excel';
      default:
        throw new Error(`Cannot detect format for file extension ${ext}`);
    }
  }

  /**
   * Compresses files into a ZIP archive
   * @param {string} outputPath Output ZIP file path
   * @param {Array<{path: string, name: string}>} files Files to include
   * @returns {Promise<string>} Path to created ZIP file
   */
  async createZipArchive(outputPath, files) {
    try {
      const archive = archiver('zip', { zlib: { level: 9 } });
      const outputStream = fs.createWriteStream(outputPath);

      await new Promise((resolve, reject) => {
        archive.pipe(outputStream);

        for (const file of files) {
          archive.file(file.path, { name: file.name });
        }

        outputStream.on('close', resolve);
        outputStream.on('error', reject);
        archive.finalize();
      });

      return outputPath;
    } catch (error) {
      log.error('ZIP archive creation failed:', error);
      throw error;
    }
  }

  /**
   * Extracts a ZIP archive
   * @param {string} zipPath Path to ZIP file
   * @param {string} extractDir Directory to extract to
   * @returns {Promise<Array<string>>} List of extracted files
   */
  async extractZipArchive(zipPath, extractDir) {
    try {
      await fs.mkdir(extractDir, { recursive: true });
      await extract(zipPath, { dir: extractDir });

      const files = await fs.readdir(extractDir);
      return files.map(file => path.join(extractDir, file));
    } catch (error) {
      log.error('ZIP extraction failed:', error);
      throw error;
    }
  }

  /**
   * Encrypts a file
   * @param {string} inputPath Path to input file
   * @param {string} outputPath Path to output file
   * @returns {Promise<string>} Path to encrypted file
   */
  async encryptFile(inputPath, outputPath) {
    try {
      const cipher = crypto.createCipheriv(
        'aes-256-gcm',
        crypto.scryptSync(this.options.encryptionKey, 'salt', 32),
        crypto.randomBytes(16)
      );

      await pipeline(
        fs.createReadStream(inputPath),
        cipher,
        fs.createWriteStream(outputPath)
      );

      return outputPath;
    } catch (error) {
      log.error('File encryption failed:', error);
      throw error;
    }
  }

  /**
   * Decrypts a file
   * @param {string} inputPath Path to encrypted file
   * @param {string} outputPath Path to decrypted file
   * @returns {Promise<string>} Path to decrypted file
   */
  async decryptFile(inputPath, outputPath) {
    try {
      // Read IV from first 16 bytes of file
      const iv = Buffer.alloc(16);
      const fd = await fs.open(inputPath, 'r');
      await fd.read(iv, 0, 16, 0);
      await fd.close();

      const decipher = crypto.createDecipheriv(
        'aes-256-gcm',
        crypto.scryptSync(this.options.encryptionKey, 'salt', 32),
        iv
      );

      await pipeline(
        fs.createReadStream(inputPath, { start: 16 }), // Skip IV
        decipher,
        fs.createWriteStream(outputPath)
      );

      return outputPath;
    } catch (error) {
      log.error('File decryption failed:', error);
      throw error;
    }
  }

  /**
   * Gets file information
   * @param {string} filePath Path to file
   * @returns {Promise<{size: number, mtime: Date, type: string}>}
   */
  async getFileInfo(filePath) {
    try {
      const stats = await fs.stat(filePath);
      return {
        size: stats.size,
        mtime: stats.mtime,
        type: path.extname(filePath).toLowerCase().replace('.', '')
      };
    } catch (error) {
      log.error('Failed to get file info:', error);
      throw error;
    }
  }
}

module.exports = FileManager;