const { contextBridge, ipcRenderer } = require('electron');
const log = require('electron-log');

// Security: Only expose safe, validated APIs to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Database operations
  db: {
    query: (sql, params) => ipcRenderer.invoke('db-query', sql, params),
    transaction: (operations) => ipcRenderer.invoke('db-transaction', operations)
  },

  // Student management
  students: {
    getAll: (filters) => ipcRenderer.invoke('students-get-all', filters),
    getById: (id) => ipcRenderer.invoke('students-get-by-id', id),
    create: (studentData) => ipcRenderer.invoke('students-create', studentData),
    update: (id, studentData) => ipcRenderer.invoke('students-update', id, studentData),
    delete: (id) => ipcRenderer.invoke('students-delete', id)
  },

  // Subject management
  subjects: {
    getAll: (classLevel) => ipcRenderer.invoke('subjects-get-all', classLevel),
    create: (subjectData) => ipcRenderer.invoke('subjects-create', subjectData),
    update: (id, subjectData) => ipcRenderer.invoke('subjects-update', id, subjectData),
    delete: (id) => ipcRenderer.invoke('subjects-delete', id)
  },

  // Grades management
  grades: {
    get: (studentId, term) => ipcRenderer.invoke('grades-get', studentId, term),
    save: (gradesData) => ipcRenderer.invoke('grades-save', gradesData),
    bulkImport: (csvData) => ipcRenderer.invoke('grades-bulk-import', csvData)
  },

  // Report generation
  reports: {
    generatePDF: (reportData) => ipcRenderer.invoke('reports-generate-pdf', reportData),
    generateBulk: (reportCriteria) => ipcRenderer.invoke('reports-generate-bulk', reportCriteria)
  },

  // File operations
  files: {
    importStudents: () => ipcRenderer.invoke('files-import-students'),
    exportStudents: (format) => ipcRenderer.invoke('files-export-students', format),
    selectFolder: () => ipcRenderer.invoke('files-select-folder')
  },

  // License management
  license: {
    verify: () => ipcRenderer.invoke('license-verify'),
    activate: (licenseKey) => ipcRenderer.invoke('license-activate', licenseKey),
    getInfo: () => ipcRenderer.invoke('license-get-info')
  },

  // Backup operations
  backup: {
    create: (options) => ipcRenderer.invoke('backup-create', options),
    restore: (backupPath) => ipcRenderer.invoke('backup-restore', backupPath),
    list: () => ipcRenderer.invoke('backup-list')
  },

  // Cloud sync
  sync: {
    toCloud: () => ipcRenderer.invoke('sync-to-cloud'),
    fromCloud: () => ipcRenderer.invoke('sync-from-cloud')
  },

  // System information
  system: {
    getInfo: () => ipcRenderer.invoke('system-info'),
    getPerformance: () => ipcRenderer.invoke('system-performance')
  },

  // Settings management
  settings: {
    get: (key) => ipcRenderer.invoke('settings-get', key),
    set: (key, value) => ipcRenderer.invoke('settings-set', key, value),
    getAll: () => ipcRenderer.invoke('settings-get-all')
  },

  // Security operations
  security: {
    hashPassword: (password) => ipcRenderer.invoke('security-hash-password', password),
    verifyPassword: (password, hash) => ipcRenderer.invoke('security-verify-password', password, hash),
    encryptData: (data) => ipcRenderer.invoke('security-encrypt-data', data),
    decryptData: (encryptedData) => ipcRenderer.invoke('security-decrypt-data', encryptedData)
  },

  // Event listeners for menu actions and notifications
  onMenuAction: (callback) => {
    ipcRenderer.on('menu-action', (event, action) => callback(action));
  },

  onNotification: (callback) => {
    ipcRenderer.on('notification', (event, notification) => callback(notification));
  },

  // Remove listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },

  // Version info
  getVersion: () => ipcRenderer.invoke('get-version'),
  
  // Development helpers (only in dev mode)
  isDev: process.env.NODE_ENV === 'development',
  
  // Platform info
  platform: process.platform,
  arch: process.arch
});

// Logging for debugging (dev mode only)
if (process.env.NODE_ENV === 'development') {
  contextBridge.exposeInMainWorld('devTools', {
    log: (...args) => log.info('[Renderer]', ...args),
    error: (...args) => log.error('[Renderer]', ...args),
    warn: (...args) => log.warn('[Renderer]', ...args)
  });
}

// Error handling
window.addEventListener('error', (event) => {
  log.error('Renderer error:', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error
  });
});

window.addEventListener('unhandledrejection', (event) => {
  log.error('Unhandled promise rejection in renderer:', event.reason);
});

log.info('Preload script loaded successfully');