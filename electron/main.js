const { app, BrowserWindow, ipcMain, dialog, Menu, shell, session } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const { autoUpdater } = require('electron-updater');
const windowStateKeeper = require('electron-window-state');
const contextMenu = require('electron-context-menu');
const log = require('electron-log');

const DatabaseManager = require('./src/database/DatabaseManager');
const SecurityManager = require('./src/security/SecurityManager');
const LicenseManager = require('./src/license/LicenseManager');
const BackupManager = require('./src/backup/BackupManager');
const CloudSyncManager = require('./src/sync/CloudSyncManager');
const ReportGenerator = require('./src/reports/ReportGenerator');
const FileManager = require('./src/files/FileManager');
const SystemMonitor = require('./src/monitoring/SystemMonitor');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'debug';
autoUpdater.logger = log;

class MarkaApplication {
  constructor() {
    this.mainWindow = null;
    this.isQuitting = false;
    this.databaseManager = null;
    this.securityManager = null;
    this.licenseManager = null;
    this.backupManager = null;
    this.cloudSyncManager = null;
    this.reportGenerator = null;
    this.fileManager = null;
    this.systemMonitor = null;
    
    this.initialize();
  }


  /**
   * Initializes the Marka application.
   *
   * Initializes all core managers, initializes the database, verifies the license,
   * and sets up event listeners and security headers.
   *
   * @returns {Promise<void>} A promise that resolves when the application has been initialized.
   */
  async initialize() {
    try {
      
      this.databaseManager = new DatabaseManager();
      this.securityManager = new SecurityManager();
      this.licenseManager = new LicenseManager();
      this.backupManager = new BackupManager(this.databaseManager);
      this.cloudSyncManager = new CloudSyncManager();
      this.reportGenerator = new ReportGenerator(this.databaseManager);
      this.fileManager = new FileManager();
      this.systemMonitor = new SystemMonitor();

      
      await this.databaseManager.initialize();
      
      
      const licenseValid = await this.licenseManager.verifyLicense();
      if (!licenseValid) {
        log.warn('Invalid license detected');
      }

      // Setup app event listeners
      this.setupAppEvents();
      this.setupIpcHandlers();
      this.setupSecurityHeaders();
      this.setupContextMenu();
      
      log.info('Marka application initialized successfully');
      
    } catch (error) {
      log.error('Failed to initialize application:', error);
      app.quit();
    }
  }

  /**
   * Sets up event listeners for the application.
   *
   * Sets up event listeners for creating the main window, recreating the window
   * when the dock icon is clicked (macOS specific), checking for updates,
   * starting system monitoring, handling window closure, and handling certificate
   * errors. It also sets Marka as the default protocol client for deep linking.
   */
  setupAppEvents() {
    app.whenReady().then(() => {
      this.createMainWindow();
      
      // macOS specific - recreate window when dock icon is clicked
      app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
          this.createMainWindow();
        }
      });

      // Check for updates
      if (!isDev) {
        autoUpdater.checkForUpdatesAndNotify();
      }

      // Start system monitoring
      this.systemMonitor.start();
    });

    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.cleanup();
        app.quit();
      }
    });

    app.on('before-quit', (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        this.performShutdownTasks();
      }
    });

    app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
      // In production, implement proper certificate validation
      event.preventDefault();
      callback(false);
    });

    // Handle protocol for deep linking
    app.setAsDefaultProtocolClient('marka');
  }

  /**
   * Creates and initializes the main application window.
   *
   * Loads the window state using windowStateKeeper, creates a new BrowserWindow
   * with specified properties, and manages the window state. Loads the application
   * content from a local file or development server, and displays the window
   * when ready. Handles events such as window ready-to-show, closed, and
   * external link navigation. Sets up the application menu.
   *
   * @returns {Promise<void>} A promise that resolves when the main window is
   * successfully created and displayed, or rejects with an error if creation fails.
   */

  async createMainWindow() {
    try {
      // Load window state
      let mainWindowState = windowStateKeeper({
        defaultWidth: 1400,
        defaultHeight: 900
      });

      
      this.mainWindow = new BrowserWindow({
        x: mainWindowState.x,
        y: mainWindowState.y,
        width: mainWindowState.width,
        height: mainWindowState.height,
        minWidth: 1200,
        minHeight: 800,
        show: false,
        icon: path.join(__dirname, 'assets/icon.png'),
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          enableRemoteModule: false,
          preload: path.join(__dirname, 'preload.js'),
          webSecurity: true,
          allowRunningInsecureContent: false,
          experimentalFeatures: false
        },
        titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
        backgroundColor: '#F1FAEE',
        frame: true,
        resizable: true,
        maximizable: true,
        minimizable: true,
        closable: true
      });

      // Manage window state
      mainWindowState.manage(this.mainWindow);

      // Load the app
      const startUrl = isDev 
        ? 'http://localhost:3000' 
        : `file://${path.join(__dirname, '../build/index.html')}`;
      
      await this.mainWindow.loadURL(startUrl);

      // Show window when ready
      this.mainWindow.once('ready-to-show', () => {
        this.mainWindow.show();
        
        if (isDev) {
          this.mainWindow.webContents.openDevTools();
        }
      });

      // Handle window closed
      this.mainWindow.on('closed', () => {
        this.mainWindow = null;
      });

      // Handle external links
      this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
      });

      // Setup menu
      this.setupApplicationMenu();

      log.info('Main window created successfully');
      
    } catch (error) {
      log.error('Failed to create main window:', error);
      throw error;
    }
  }

  /**
   * Sets up security headers to be sent with all requests.
   *
   * Adds Content-Security-Policy, X-Content-Type-Options, X-Frame-Options,
   * X-XSS-Protection, and Strict-Transport-Security headers to all responses.
   *
   * The Content-Security-Policy is set to prevent inline scripts and styles, and
   * limits the sources of scripts, styles, images, and fonts to the application
   * itself. The connect-src directive also allows requests to the Marka API.
   */
  setupSecurityHeaders() {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      callback({
        responseHeaders: {
          ...details.responseHeaders,
          'Content-Security-Policy': [
            "default-src 'self'; " +
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
            "style-src 'self' 'unsafe-inline'; " +
            "img-src 'self' data: https:; " +
            "font-src 'self' data:; " +
            "connect-src 'self' https://api.marka.codewithlyee.com;"
          ],
          'X-Content-Type-Options': ['nosniff'],
          'X-Frame-Options': ['DENY'],
          'X-XSS-Protection': ['1; mode=block'],
          'Strict-Transport-Security': ['max-age=31536000; includeSubDomains']
        }
      });
    });
  }

/**
 * Configures the context menu for the application.
 *
 * Sets up the context menu with options tailored for the development environment.
 * The context menu includes a reload option when in development mode and excludes
 * options to search with Google, copy images, or save images. The "Reload" option
 * is only visible in development mode and allows the user to reload the browser window.
 */

  setupContextMenu() {
    contextMenu({
      showInspectElement: isDev,
      showSearchWithGoogle: false,
      showCopyImage: false,
      showSaveImage: false,
      prepend: (defaultActions, params, browserWindow) => [
        {
          label: 'Reload',
          visible: isDev,
          click: () => {
            browserWindow.reload();
          }
        }
      ]
    });
  }

  /**
   * Configures the application menu.
   *
   * Sets up the application menu with options that allow the user to interact with
   * the application. The menu includes options to create a new student, import and
   * export data, generate reports, and exit the application. The menu also includes
   * options to control the application's view and tools, such as reloading the window,
   * toggling the developer tools, and viewing system information.
   *
   * The menu is adjusted for macOS by adding an "About Marka" option and moving the
   * "Quit" option to the "Marka" menu.
   */
  setupApplicationMenu() {
    const template = [
      {
        label: 'File',
        submenu: [
          {
            label: 'New Student',
            accelerator: 'CmdOrCtrl+N',
            click: () => {
              this.mainWindow.webContents.send('menu-action', 'new-student');
            }
          },
          {
            label: 'Import Data',
            accelerator: 'CmdOrCtrl+I',
            click: () => {
              this.handleImportData();
            }
          },
          {
            label: 'Export Data',
            accelerator: 'CmdOrCtrl+E',
            click: () => {
              this.handleExportData();
            }
          },
          { type: 'separator' },
          {
            label: 'Generate Report',
            accelerator: 'CmdOrCtrl+R',
            click: () => {
              this.mainWindow.webContents.send('menu-action', 'generate-report');
            }
          },
          { type: 'separator' },
          {
            label: 'Exit',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => {
              this.isQuitting = true;
              app.quit();
            }
          }
        ]
      },
      {
        label: 'Edit',
        submenu: [
          { role: 'undo' },
          { role: 'redo' },
          { type: 'separator' },
          { role: 'cut' },
          { role: 'copy' },
          { role: 'paste' },
          { role: 'selectall' }
        ]
      },
      {
        label: 'View',
        submenu: [
          { role: 'reload' },
          { role: 'forceReload' },
          { role: 'toggleDevTools' },
          { type: 'separator' },
          { role: 'resetZoom' },
          { role: 'zoomIn' },
          { role: 'zoomOut' },
          { type: 'separator' },
          { role: 'togglefullscreen' }
        ]
      },
      {
        label: 'Tools',
        submenu: [
          {
            label: 'Backup Database',
            click: () => {
              this.handleBackupDatabase();
            }
          },
          {
            label: 'Restore Database',
            click: () => {
              this.handleRestoreDatabase();
            }
          },
          { type: 'separator' },
          {
            label: 'Sync to Cloud',
            click: () => {
              this.handleCloudSync();
            }
          },
          {
            label: 'System Information',
            click: () => {
              this.showSystemInformation();
            }
          }
        ]
      },
      {
        label: 'Help',
        submenu: [
          {
            label: 'Documentation',
            click: () => {
              shell.openExternal('https://docs.marka.codewithlyee.com');
            }
          },
          {
            label: 'Support',
            click: () => {
              shell.openExternal('mailto:support@codewithlyee.com');
            }
          },
          { type: 'separator' },
          {
            label: 'About Marka',
            click: () => {
              this.showAboutDialog();
            }
          }
        ]
      }
    ];

    // macOS specific menu adjustments
    if (process.platform === 'darwin') {
      template.unshift({
        label: app.getName(),
        submenu: [
          { role: 'about' },
          { type: 'separator' },
          { role: 'services' },
          { type: 'separator' },
          { role: 'hide' },
          { role: 'hideothers' },
          { role: 'unhide' },
          { type: 'separator' },
          { role: 'quit' }
        ]
      });
    }

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  setupIpcHandlers() {
    // Database operations
    ipcMain.handle('db-query', async (event, query, params) => {
      try {
        return await this.databaseManager.query(query, params);
      } catch (error) {
        log.error('Database query error:', error);
        throw error;
      }
    });

    ipcMain.handle('db-transaction', async (event, operations) => {
      try {
        return await this.databaseManager.transaction(operations);
      } catch (error) {
        log.error('Database transaction error:', error);
        throw error;
      }
    });

    // Student management
    ipcMain.handle('students-get-all', async (event, filters = {}) => {
      return await this.databaseManager.getStudents(filters);
    });

    ipcMain.handle('students-get-by-id', async (event, id) => {
      return await this.databaseManager.getStudent(id);
    });

    ipcMain.handle('students-create', async (event, studentData) => {
      return await this.databaseManager.createStudent(studentData);
    });

    ipcMain.handle('students-update', async (event, id, studentData) => {
      return await this.databaseManager.updateStudent(id, studentData);
    });

    ipcMain.handle('students-delete', async (event, id) => {
      return await this.databaseManager.deleteStudent(id);
    });

    // Subject management
    ipcMain.handle('subjects-get-all', async (event, classLevel) => {
      return await this.databaseManager.getSubjects(classLevel);
    });

    ipcMain.handle('subjects-create', async (event, subjectData) => {
      return await this.databaseManager.createSubject(subjectData);
    });

    ipcMain.handle('subjects-update', async (event, id, subjectData) => {
      return await this.databaseManager.updateSubject(id, subjectData);
    });

    ipcMain.handle('subjects-delete', async (event, id) => {
      return await this.databaseManager.deleteSubject(id);
    });

    // Grades management
    ipcMain.handle('grades-get', async (event, studentId, term) => {
      return await this.databaseManager.getGrades(studentId, term);
    });

    ipcMain.handle('grades-save', async (event, gradesData) => {
      return await this.databaseManager.saveGrades(gradesData);
    });

    ipcMain.handle('grades-bulk-import', async (event, csvData) => {
      return await this.databaseManager.bulkImportGrades(csvData);
    });

    // Report generation
    ipcMain.handle('reports-generate-pdf', async (event, reportData) => {
      try {
        const pdfPath = await this.reportGenerator.generatePDF(reportData);
        return { success: true, path: pdfPath };
      } catch (error) {
        log.error('PDF generation error:', error);
        return { success: false, error: error.message };
      }
    });

    ipcMain.handle('reports-generate-bulk', async (event, reportCriteria) => {
      try {
        const results = await this.reportGenerator.generateBulkReports(reportCriteria);
        return { success: true, reports: results };
      } catch (error) {
        log.error('Bulk report generation error:', error);
        return { success: false, error: error.message };
      }
    });

    // File operations
    ipcMain.handle('files-import-students', async (event) => {
      return await this.handleImportStudents();
    });

    ipcMain.handle('files-export-students', async (event, format = 'csv') => {
      return await this.handleExportStudents(format);
    });

    ipcMain.handle('files-select-folder', async (event) => {
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openDirectory'],
        title: 'Select Export Folder'
      });
      return result;
    });

    // License management
    ipcMain.handle('license-verify', async (event) => {
      return await this.licenseManager.verifyLicense();
    });

    ipcMain.handle('license-activate', async (event, licenseKey) => {
      return await this.licenseManager.activateLicense(licenseKey);
    });

    ipcMain.handle('license-get-info', async (event) => {
      return await this.licenseManager.getLicenseInfo();
    });

    // Backup operations
    ipcMain.handle('backup-create', async (event, options = {}) => {
      try {
        const backupPath = await this.backupManager.createBackup(options);
        return { success: true, path: backupPath };
      } catch (error) {
        log.error('Backup creation error:', error);
        return { success: false, error: error.message };
      }
    });

    ipcMain.handle('backup-restore', async (event, backupPath) => {
      try {
        await this.backupManager.restoreBackup(backupPath);
        return { success: true };
      } catch (error) {
        log.error('Backup restoration error:', error);
        return { success: false, error: error.message };
      }
    });

    ipcMain.handle('backup-list', async (event) => {
      return await this.backupManager.listBackups();
    });

    // Cloud sync
    ipcMain.handle('sync-to-cloud', async (event) => {
      try {
        await this.cloudSyncManager.syncToCloud();
        return { success: true };
      } catch (error) {
        log.error('Cloud sync error:', error);
        return { success: false, error: error.message };
      }
    });

    ipcMain.handle('sync-from-cloud', async (event) => {
      try {
        await this.cloudSyncManager.syncFromCloud();
        return { success: true };
      } catch (error) {
        log.error('Cloud sync error:', error);
        return { success: false, error: error.message };
      }
    });

    // System information
    ipcMain.handle('system-info', async (event) => {
      return await this.systemMonitor.getSystemInfo();
    });

    ipcMain.handle('system-performance', async (event) => {
      return await this.systemMonitor.getPerformanceMetrics();
    });

    // Settings management
    ipcMain.handle('settings-get', async (event, key) => {
      return await this.databaseManager.getSetting(key);
    });

    ipcMain.handle('settings-set', async (event, key, value) => {
      return await this.databaseManager.setSetting(key, value);
    });

    ipcMain.handle('settings-get-all', async (event) => {
      return await this.databaseManager.getAllSettings();
    });

    // Security operations
    ipcMain.handle('security-hash-password', async (event, password) => {
      return await this.securityManager.hashPassword(password);
    });

    ipcMain.handle('security-verify-password', async (event, password, hash) => {
      return await this.securityManager.verifyPassword(password, hash);
    });

    ipcMain.handle('security-encrypt-data', async (event, data) => {
      return await this.securityManager.encryptData(data);
    });

    ipcMain.handle('security-decrypt-data', async (event, encryptedData) => {
      return await this.securityManager.decryptData(encryptedData);
    });
  }

  /**
   * Opens a file dialog to select a file to import student data.
   *
   * Supported file formats are CSV, Excel (xlsx and xls), and any other file
   * type.
   *
   * @returns {Promise<Object>} A promise that resolves with an object containing
   * a success boolean and an error message if the import fails, or an object
   * with the imported data if the import is successful.
   */
  async handleImportStudents() {
    try {
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openFile'],
        filters: [
          { name: 'CSV Files', extensions: ['csv'] },
          { name: 'Excel Files', extensions: ['xlsx', 'xls'] },
          { name: 'All Files', extensions: ['*'] }
        ],
        title: 'Import Student Data'
      });

      if (!result.canceled && result.filePaths.length > 0) {
        const filePath = result.filePaths[0];
        const importResult = await this.fileManager.importStudents(filePath);
        return { success: true, data: importResult };
      }

      return { success: false, error: 'No file selected' };
    } catch (error) {
      log.error('Student import error:', error);
      return { success: false, error: error.message };
    }
  }

/**
 * Exports student data to a specified format.
 *
 * Opens a save dialog to allow the user to select a location and file format
 * for exporting student data. Supported formats are CSV, Excel (xlsx), and PDF.
 * 
 * @param {string} format - The format to export the student data in ('csv', 'xlsx', or 'pdf').
 * @returns {Promise<Object>} A promise that resolves with an object containing a success
 * boolean and the path to the exported file if successful, or an error message if the
 * export is canceled or fails.
 */

  async handleExportStudents(format) {
    try {
      const result = await dialog.showSaveDialog(this.mainWindow, {
        defaultPath: `students_export_${new Date().toISOString().split('T')[0]}.${format}`,
        filters: [
          { name: 'CSV Files', extensions: ['csv'] },
          { name: 'Excel Files', extensions: ['xlsx'] },
          { name: 'PDF Files', extensions: ['pdf'] }
        ],
        title: 'Export Student Data'
      });

      if (!result.canceled) {
        const exportPath = await this.fileManager.exportStudents(result.filePath, format);
        return { success: true, path: exportPath };
      }

      return { success: false, error: 'Export cancelled' };
    } catch (error) {
      log.error('Student export error:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Creates a backup of the database.
   *
   * Creates a backup of the database file and saves it to the default backup
   * directory. The backup file is named according to the current date and time.
   * 
   * A message box is displayed to the user to indicate the success or failure
   * of the backup operation.
   * 
   * @returns {Promise<void>} A promise that resolves when the backup operation
   * is complete.
   */
  async handleBackupDatabase() {
    try {
      const result = await this.backupManager.createBackup();
      
      dialog.showMessageBox(this.mainWindow, {
        type: 'info',
        title: 'Backup Complete',
        message: 'Database backup created successfully',
        detail: `Backup saved to: ${result}`
      });
    } catch (error) {
      dialog.showErrorBox('Backup Error', error.message);
    }
  }

  /**
   * Restores the database from a backup file.
   * 
   * Allows the user to select a backup file and then confirms with the user
   * if they want to restore from the backup. If confirmed, the database is
   * replaced with the content of the backup file. The application is then
   * restarted to apply the changes.
   * 
   * A message box is displayed to the user to indicate the success or failure
   * of the restore operation.
   * 
   * @returns {Promise<void>} A promise that resolves when the restore operation
   * is complete.
   */
  async handleRestoreDatabase() {
    try {
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openFile'],
        filters: [
          { name: 'Marka Backup Files', extensions: ['marka'] },
          { name: 'All Files', extensions: ['*'] }
        ],
        title: 'Select Backup File to Restore'
      });

      if (!result.canceled && result.filePaths.length > 0) {
        const confirmed = await dialog.showMessageBox(this.mainWindow, {
          type: 'warning',
          buttons: ['Yes', 'No'],
          title: 'Confirm Restore',
          message: 'Are you sure you want to restore from backup?',
          detail: 'This will replace all current data. This action cannot be undone.'
        });

        if (confirmed.response === 0) {
          await this.backupManager.restoreBackup(result.filePaths[0]);
          
          dialog.showMessageBox(this.mainWindow, {
            type: 'info',
            title: 'Restore Complete',
            message: 'Database restored successfully',
            detail: 'The application will restart to apply changes.'
          });

          app.relaunch();
          app.exit();
        }
      }
    } catch (error) {
      dialog.showErrorBox('Restore Error', error.message);
    }
  }

  async handleCloudSync() {
    try {
      const licenseInfo = await this.licenseManager.getLicenseInfo();
      
      if (licenseInfo.type !== 'Enterprise') {
        dialog.showMessageBox(this.mainWindow, {
          type: 'warning',
          title: 'Feature Unavailable',
          message: 'Cloud sync is only available in Enterprise edition',
          detail: 'Please upgrade your license to access this feature.'
        });
        return;
      }

      await this.cloudSyncManager.syncToCloud();
      
      dialog.showMessageBox(this.mainWindow, {
        type: 'info',
        title: 'Sync Complete',
        message: 'Data synchronized to cloud successfully'
      });
    } catch (error) {
      dialog.showErrorBox('Sync Error', error.message);
    }
  }

  /**
   * Shows a message box with system information.
   * 
   * Shows the Marka version, platform, architecture, Node.js version, license type,
   * memory usage in MB, and uptime in seconds.
   * 
   * @returns {Promise<void>} A promise that resolves when the message box is closed.
   */
  async showSystemInformation() {
    const systemInfo = await this.systemMonitor.getSystemInfo();
    const licenseInfo = await this.licenseManager.getLicenseInfo();
    
    dialog.showMessageBox(this.mainWindow, {
      type: 'info',
      title: 'System Information',
      message: 'Marka Report Card Generator',
      detail: `Version: ${app.getVersion()}
Platform: ${process.platform}
Architecture: ${process.arch}
Node.js: ${process.version}
License: ${licenseInfo.type}
Memory Usage: ${Math.round(process.memoryUsage().rss / 1024 / 1024)} MB
Uptime: ${Math.round(process.uptime())} seconds`
    });
  }

  /**
   * Shows a message box with application information.
   * 
   * Shows the application version, author, email, website, and copyright information.
   * 
   * @returns {Promise<void>} A promise that resolves when the message box is closed.
   */
  showAboutDialog() {
    dialog.showMessageBox(this.mainWindow, {
      type: 'info',
      title: 'About Marka',
      message: 'Marka Report Card Generator',
      detail: `Version: ${app.getVersion()}
Developed by: Kasim Lyee
Email: lyee@codewithlyee.com
Website: https://marka.codewithlyee.com

© 2025 Kasim Lyee. All rights reserved.

The leading report card generation software for Ugandan schools, fully compliant with UNEB standards.`
    });
  }

/**
 * Performs shutdown tasks for the application.
 *
 * This method handles the tasks required to gracefully shut down the application.
 * It flushes any pending data to the database, creates an automatic backup if
 * enabled, syncs data to the cloud if auto-sync is enabled and the license type
 * is Enterprise, and stops system monitoring. It logs the start and completion
 * of shutdown tasks and ensures the application quits properly, even in case of
 * errors during the shutdown process.
 *
 * @returns {Promise<void>} A promise that resolves when all shutdown tasks are complete.
 */

  async performShutdownTasks() {
    try {
      log.info('Performing shutdown tasks...');
      
      // Save any pending data
      await this.databaseManager.flush();
      
      // Create automatic backup if enabled
      const autoBackup = await this.databaseManager.getSetting('autoBackup');
      if (autoBackup) {
        await this.backupManager.createBackup({ automatic: true });
      }
      
      // Sync to cloud if enabled and enterprise
      const licenseInfo = await this.licenseManager.getLicenseInfo();
      if (licenseInfo.type === 'Enterprise') {
        const autoSync = await this.databaseManager.getSetting('autoSync');
        if (autoSync) {
          await this.cloudSyncManager.syncToCloud();
        }
      }
      
      // Stop monitoring
      this.systemMonitor.stop();
      
      log.info('Shutdown tasks completed');
      this.isQuitting = true;
      app.quit();
      
    } catch (error) {
      log.error('Error during shutdown:', error);
      this.isQuitting = true;
      app.quit();
    }
  }

  async cleanup() {
    try {
      if (this.databaseManager) {
        await this.databaseManager.close();
      }
      
      if (this.systemMonitor) {
        this.systemMonitor.stop();
      }
      
      log.info('Application cleanup completed');
    } catch (error) {
      log.error('Error during cleanup:', error);
    }
  }
}

// Handle app instance lock
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Someone tried to run a second instance, focus our window instead
    const markaApp = new MarkaApplication();
    if (markaApp.mainWindow) {
      if (markaApp.mainWindow.isMinimized()) markaApp.mainWindow.restore();
      markaApp.mainWindow.focus();
    }
  });

  // Create the application
  new MarkaApplication();
}

// Handle unhandled errors
process.on('uncaughtException', (error) => {
  log.error('Uncaught Exception:', error);
  app.quit();
});

process.on('unhandledRejection', (reason, promise) => {
  log.error('Unhandled Rejection at:', promise, 'reason:', reason);
});