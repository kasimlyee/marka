const fs = require('fs').promises;
const path = require('path');
const { app, dialog } = require('electron');
const crypto = require('crypto');
const zlib = require('zlib');
const log = require('electron-log');
const { pipeline } = require('stream/promises');
const tar = require('tar');
const moment = require('moment');
const { Storage } = require('@google-cloud/storage');
const AWS = require('aws-sdk');

class BackupManager {
  constructor(databaseManager, options = {}) {
    this.databaseManager = databaseManager;
    this.options = {
      encryptionKey: process.env.BACKUP_ENCRYPTION_KEY || 'default-encryption-key',
      backupDir: path.join(app.getPath('userData'), 'backups'),
      retentionDays: 30,
      maxBackups: 10,
      cloudProviders: [],
      ...options
    };

    this.cloudClients = this.initializeCloudClients();
    this.ensureBackupDir();
  }

  initializeCloudClients() {
    const clients = {};
    
    if (this.options.cloudProviders.includes('gcp') && process.env.GCP_PROJECT_ID) {
      clients.gcp = new Storage({
        projectId: process.env.GCP_PROJECT_ID,
        keyFilename: process.env.GCP_KEY_FILE
      });
    }

    if (this.options.cloudProviders.includes('aws') && process.env.AWS_ACCESS_KEY_ID) {
      AWS.config.update({
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
        region: process.env.AWS_REGION
      });
      clients.aws = new AWS.S3();
    }

    return clients;
  }

  async ensureBackupDir() {
    try {
      await fs.mkdir(this.options.backupDir, { recursive: true });
    } catch (error) {
      log.error('Failed to create backup directory:', error);
      throw error;
    }
  }

  /**
   * Creates a backup of the database with optional encryption and compression
   * @param {Object} options 
   * @param {boolean} options.encrypt - Whether to encrypt the backup
   * @param {boolean} options.compress - Whether to compress the backup
   * @param {boolean} options.automatic - Whether this is an automatic backup
   * @returns {Promise<string>} Path to the created backup file
   */
  async createBackup(options = {}) {
    const { encrypt = true, compress = true, automatic = false } = options;
    const timestamp = moment().format('YYYYMMDD-HHmmss');
    const backupName = `marka-backup-${timestamp}${automatic ? '-auto' : ''}.marka`;
    const backupPath = path.join(this.options.backupDir, backupName);
    const tempPath = `${backupPath}.tmp`;

    try {
      log.info(`Creating backup at ${backupPath}`, { options });

      // Step 1: Create a temporary backup file
      await this.createTempBackup(tempPath);

      // Step 2: Process the backup (compress and/or encrypt)
      await this.processBackup(tempPath, backupPath, { encrypt, compress });

      // Step 3: Clean up temporary file
      await fs.unlink(tempPath);

      // Step 4: Upload to cloud if configured
      await this.uploadToCloud(backupPath, backupName);

      // Step 5: Record backup in database
      await this.databaseManager.createBackupInfo(backupPath, automatic ? 'automatic' : 'manual');

      // Step 6: Apply retention policy
      await this.applyRetentionPolicy();

      log.info('Backup created successfully');
      return backupPath;
    } catch (error) {
      log.error('Backup creation failed:', error);
      
      // Clean up any partial files
      try {
        await fs.access(tempPath);
        await fs.unlink(tempPath);
      } catch (cleanupError) {
        log.error('Failed to clean up temporary backup file:', cleanupError);
      }

      throw error;
    }
  }

  async createTempBackup(tempPath) {
    try {
      // Create a tarball of the database files
      await tar.c({
        gzip: false,
        file: tempPath,
        cwd: path.dirname(this.databaseManager.dbPath),
      }, [path.basename(this.databaseManager.dbPath)]);
    } catch (error) {
      log.error('Failed to create temporary backup:', error);
      throw new Error('Failed to create database tarball');
    }
  }

  async processBackup(sourcePath, destPath, options) {
    try {
      let sourceStream = fs.createReadStream(sourcePath);
      let destStream = fs.createWriteStream(destPath);
      let transformStream = null;

      // Apply compression if requested
      if (options.compress) {
        transformStream = zlib.createGzip();
      }

      // Apply encryption if requested
      if (options.encrypt) {
        const cipher = crypto.createCipheriv(
          'aes-256-gcm',
          crypto.scryptSync(this.options.encryptionKey, 'salt', 32),
          crypto.randomBytes(16)
        );

        if (transformStream) {
          // If we already have a transform stream (from compression), pipe through cipher
          transformStream = transformStream.pipe(cipher);
        } else {
          transformStream = cipher;
        }
      }

      // Set up the pipeline
      if (transformStream) {
        await pipeline(sourceStream, transformStream, destStream);
      } else {
        await pipeline(sourceStream, destStream);
      }
    } catch (error) {
      log.error('Backup processing failed:', error);
      throw new Error('Failed to process backup file');
    }
  }

  async uploadToCloud(backupPath, backupName) {
    const uploadPromises = [];
    
    // Upload to GCP if configured
    if (this.cloudClients.gcp && process.env.GCP_BUCKET_NAME) {
      uploadPromises.push(
        this.cloudClients.gcp.bucket(process.env.GCP_BUCKET_NAME)
          .upload(backupPath, {
            destination: `backups/${backupName}`,
            metadata: {
              contentType: 'application/octet-stream',
              metadata: {
                source: 'marka-desktop',
                timestamp: new Date().toISOString()
              }
            }
          })
          .catch(error => {
            log.error('GCP upload failed:', error);
            throw error;
          })
      );
    }

    // Upload to AWS if configured
    if (this.cloudClients.aws && process.env.AWS_BUCKET_NAME) {
      const fileContent = await fs.readFile(backupPath);
      
      uploadPromises.push(
        this.cloudClients.aws.upload({
          Bucket: process.env.AWS_BUCKET_NAME,
          Key: `backups/${backupName}`,
          Body: fileContent,
          ContentType: 'application/octet-stream',
          Metadata: {
            source: 'marka-desktop',
            timestamp: new Date().toISOString()
          }
        }).promise()
        .catch(error => {
          log.error('AWS upload failed:', error);
          throw error;
        })
      );
    }

    // Execute all uploads in parallel
    if (uploadPromises.length > 0) {
      await Promise.all(uploadPromises);
      log.info('Cloud backup uploads completed');
    }
  }

  async applyRetentionPolicy() {
    try {
      const files = await fs.readdir(this.options.backupDir);
      const backupFiles = files
        .filter(file => file.endsWith('.marka'))
        .map(file => ({
          name: file,
          path: path.join(this.options.backupDir, file),
          time: fs.statSync(path.join(this.options.backupDir, file)).mtime.getTime()
        }))
        .sort((a, b) => b.time - a.time);

      // Delete files beyond maxBackups count
      if (backupFiles.length > this.options.maxBackups) {
        const filesToDelete = backupFiles.slice(this.options.maxBackups);
        for (const file of filesToDelete) {
          try {
            await fs.unlink(file.path);
            log.info(`Deleted old backup: ${file.name}`);
          } catch (error) {
            log.error(`Failed to delete old backup ${file.name}:`, error);
          }
        }
      }

      // Delete files older than retentionDays
      const cutoffDate = Date.now() - (this.options.retentionDays * 24 * 60 * 60 * 1000);
      const oldFiles = backupFiles.filter(file => file.time < cutoffDate);
      
      for (const file of oldFiles) {
        try {
          await fs.unlink(file.path);
          log.info(`Deleted expired backup: ${file.name}`);
        } catch (error) {
          log.error(`Failed to delete expired backup ${file.name}:`, error);
        }
      }
    } catch (error) {
      log.error('Failed to apply retention policy:', error);
    }
  }

  /**
   * Restores the database from a backup file
   * @param {string} backupPath Path to the backup file
   * @returns {Promise<void>}
   */
  async restoreBackup(backupPath) {
    try {
      log.info(`Starting restore from backup: ${backupPath}`);

      // Step 1: Verify backup file
      await this.verifyBackupFile(backupPath);

      // Step 2: Create restore directory
      const restoreDir = path.join(this.options.backupDir, 'restore');
      await fs.mkdir(restoreDir, { recursive: true });

      // Step 3: Process the backup file
      const extractedPath = await this.processRestore(backupPath, restoreDir);

      // Step 4: Verify the extracted database
      await this.verifyDatabaseFile(extractedPath);

      // Step 5: Replace current database
      await this.replaceDatabase(extractedPath);

      // Step 6: Clean up
      await fs.rm(restoreDir, { recursive: true, force: true });

      log.info('Database restore completed successfully');
    } catch (error) {
      log.error('Restore failed:', error);
      throw error;
    }
  }

  async verifyBackupFile(backupPath) {
    try {
      const stats = await fs.stat(backupPath);
      if (stats.size === 0) {
        throw new Error('Backup file is empty');
      }
    } catch (error) {
      log.error('Backup file verification failed:', error);
      throw new Error('Invalid backup file');
    }
  }

  async processRestore(backupPath, restoreDir) {
    try {
      let sourceStream = fs.createReadStream(backupPath);
      let transformStream = null;

      // Check if file is encrypted by trying to read the first few bytes
      const header = Buffer.alloc(16);
      const fd = await fs.open(backupPath, 'r');
      await fd.read(header, 0, 16, 0);
      await fd.close();

      const isEncrypted = !header.toString('hex').includes('1f8b'); // Gzip magic number

      if (isEncrypted) {
        const decipher = crypto.createDecipheriv(
          'aes-256-gcm',
          crypto.scryptSync(this.options.encryptionKey, 'salt', 32),
          header.slice(0, 16) // Use first 16 bytes as IV
        );
        transformStream = decipher;
      }

      // Create decompression stream if needed
      const isCompressed = !isEncrypted || header.includes('1f8b');
      if (isCompressed) {
        const gunzip = zlib.createGunzip();
        if (transformStream) {
          transformStream = transformStream.pipe(gunzip);
        } else {
          transformStream = gunzip;
        }
      }

      // Extract the tarball
      const extractStream = tar.x({
        cwd: restoreDir,
        strict: true
      });

      if (transformStream) {
        await pipeline(sourceStream, transformStream, extractStream);
      } else {
        await pipeline(sourceStream, extractStream);
      }

      return path.join(restoreDir, path.basename(this.databaseManager.dbPath));
    } catch (error) {
      log.error('Backup processing failed during restore:', error);
      throw new Error('Failed to process backup file for restore');
    }
  }

  async verifyDatabaseFile(dbPath) {
    try {
      // Quick integrity check
      const db = new (require('better-sqlite3'))(dbPath, { readonly: true });
      const result = db.pragma('integrity_check');
      db.close();

      if (result[0].integrity_check !== 'ok') {
        throw new Error('Database integrity check failed');
      }
    } catch (error) {
      log.error('Database verification failed:', error);
      throw new Error('Invalid database file in backup');
    }
  }

  async replaceDatabase(newDbPath) {
    try {
      // Close existing database connections
      await this.databaseManager.close();

      // Backup current database in case restore fails
      const backupCurrentPath = `${this.databaseManager.dbPath}.pre-restore`;
      await fs.copyFile(this.databaseManager.dbPath, backupCurrentPath);

      try {
        // Replace the database file
        await fs.copyFile(newDbPath, this.databaseManager.dbPath);

        // Reinitialize the database
        await this.databaseManager.initialize();
      } catch (error) {
        // Restore original database if replacement failed
        log.error('Restore failed, reverting to original database:', error);
        await fs.copyFile(backupCurrentPath, this.databaseManager.dbPath);
        await this.databaseManager.initialize();
        throw error;
      } finally {
        // Clean up the backup
        await fs.unlink(backupCurrentPath).catch(() => {});
      }
    } catch (error) {
      log.error('Database replacement failed:', error);
      throw new Error('Failed to replace database file');
    }
  }

  /**
   * Lists available backups
   * @returns {Promise<Array<{name: string, path: string, size: number, modified: Date}>>}
   */
  async listBackups() {
    try {
      const files = await fs.readdir(this.options.backupDir);
      const backupFiles = files.filter(file => file.endsWith('.marka'));

      const backups = await Promise.all(
        backupFiles.map(async file => {
          const filePath = path.join(this.options.backupDir, file);
          const stats = await fs.stat(filePath);
          return {
            name: file,
            path: filePath,
            size: stats.size,
            modified: stats.mtime
          };
        })
      );

      return backups.sort((a, b) => b.modified - a.modified);
    } catch (error) {
      log.error('Failed to list backups:', error);
      throw error;
    }
  }

  /**
   * Downloads a backup from cloud storage
   * @param {string} backupName Name of the backup to download
   * @param {string} provider Cloud provider ('aws' or 'gcp')
   * @returns {Promise<string>} Path to the downloaded backup file
   */
  async downloadFromCloud(backupName, provider) {
    if (!this.cloudClients[provider]) {
      throw new Error(`Cloud provider ${provider} not configured`);
    }

    const destPath = path.join(this.options.backupDir, backupName);
    
    try {
      if (provider === 'gcp') {
        await this.cloudClients.gcp.bucket(process.env.GCP_BUCKET_NAME)
          .file(`backups/${backupName}`)
          .download({ destination: destPath });
      } else if (provider === 'aws') {
        const data = await this.cloudClients.aws.getObject({
          Bucket: process.env.AWS_BUCKET_NAME,
          Key: `backups/${backupName}`
        }).promise();
        
        await fs.writeFile(destPath, data.Body);
      }

      return destPath;
    } catch (error) {
      log.error(`Failed to download backup from ${provider}:`, error);
      throw error;
    }
  }
}

module.exports = BackupManager;