const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const log = require('electron-log');
const { Storage } = require('@google-cloud/storage');
const AWS = require('aws-sdk');
const { Mutex } = require('async-mutex');

class CloudSyncManager {
  constructor(options = {}) {
    this.options = {
      syncInterval: 3600000, // 1 hour
      encryptionKey: process.env.CLOUD_SYNC_KEY || 'default-sync-key',
      maxRetries: 3,
      retryDelay: 5000,
      conflictResolution: 'server', // 'server' or 'client'
      ...options
    };

    this.clients = this.initializeClients();
    this.syncMutex = new Mutex();
    this.syncInterval = null;
    this.lastSync = null;
    this.syncStatus = 'idle';
  }

  initializeClients() {
    const clients = {};
    
    if (process.env.GCP_PROJECT_ID) {
      clients.gcp = new Storage({
        projectId: process.env.GCP_PROJECT_ID,
        keyFilename: process.env.GCP_KEY_FILE
      });
    }

    if (process.env.AWS_ACCESS_KEY_ID) {
      AWS.config.update({
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
        region: process.env.AWS_REGION
      });
      clients.aws = new AWS.S3();
    }

    return clients;
  }

  /**
   * Starts automatic synchronization
   */
  startAutoSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }

    this.syncInterval = setInterval(() => {
      this.syncToCloud().catch(error => {
        log.error('Auto sync failed:', error);
      });
    }, this.options.syncInterval);

    log.info('Auto sync started');
  }

  /**
   * Stops automatic synchronization
   */
  stopAutoSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
    log.info('Auto sync stopped');
  }

  /**
   * Synchronizes local data to cloud storage
   * @returns {Promise<void>}
   */
  async syncToCloud() {
    const release = await this.syncMutex.acquire();
    this.syncStatus = 'syncing';

    try {
      log.info('Starting cloud sync');
      
      // Step 1: Create a sync package
      const syncPackagePath = await this.createSyncPackage();

      // Step 2: Upload to all configured cloud providers
      await this.uploadSyncPackage(syncPackagePath);

      // Step 3: Clean up
      await fs.unlink(syncPackagePath);

      this.lastSync = new Date();
      this.syncStatus = 'idle';
      log.info('Cloud sync completed successfully');
    } catch (error) {
      this.syncStatus = 'error';
      log.error('Cloud sync failed:', error);
      throw error;
    } finally {
      release();
    }
  }

  /**
   * Synchronizes from cloud storage to local
   * @returns {Promise<void>}
   */
  async syncFromCloud() {
    const release = await this.syncMutex.acquire();
    this.syncStatus = 'syncing';

    try {
      log.info('Starting cloud sync download');

      // Step 1: Download latest sync package
      const syncPackagePath = await this.downloadSyncPackage();

      // Step 2: Apply sync package
      await this.applySyncPackage(syncPackagePath);

      // Step 3: Clean up
      await fs.unlink(syncPackagePath);

      this.lastSync = new Date();
      this.syncStatus = 'idle';
      log.info('Cloud sync download completed successfully');
    } catch (error) {
      this.syncStatus = 'error';
      log.error('Cloud sync download failed:', error);
      throw error;
    } finally {
      release();
    }
  }

  async createSyncPackage() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const syncPackagePath = path.join(require('os').tmpdir(), `marka-sync-${timestamp}.msync`);

    try {
      // Create a checksum of the database file
      const dbHash = await this.hashFile(require('electron').app.getPath('userData') + '/marka_database.db');

      // Create a manifest file
      const manifest = {
        timestamp: new Date().toISOString(),
        dbHash,
        version: require('electron').app.getVersion(),
        files: ['database.db']
      };

      // Write manifest to temp file
      const manifestPath = path.join(require('os').tmpdir(), `manifest-${timestamp}.json`);
      await fs.writeFile(manifestPath, JSON.stringify(manifest));

      // Create encrypted tarball
      const cipher = crypto.createCipheriv(
        'aes-256-gcm',
        crypto.scryptSync(this.options.encryptionKey, 'salt', 32),
        crypto.randomBytes(16)
      );

      await new Promise((resolve, reject) => {
        const tar = require('tar').c({
          gzip: true,
          cwd: require('electron').app.getPath('userData')
        }, ['marka_database.db', manifestPath])
        .pipe(cipher)
        .pipe(fs.createWriteStream(syncPackagePath))
        .on('finish', resolve)
        .on('error', reject);
      });

      // Clean up manifest file
      await fs.unlink(manifestPath);

      return syncPackagePath;
    } catch (error) {
      log.error('Failed to create sync package:', error);
      throw error;
    }
  }

  async uploadSyncPackage(syncPackagePath) {
    const uploadPromises = [];
    const fileName = path.basename(syncPackagePath);

    // Upload to GCP if configured
    if (this.clients.gcp && process.env.GCP_BUCKET_NAME) {
      uploadPromises.push(
        this.retryOperation(
          () => this.clients.gcp.bucket(process.env.GCP_BUCKET_NAME)
            .upload(syncPackagePath, {
              destination: `sync/${fileName}`,
              metadata: {
                contentType: 'application/octet-stream',
                metadata: {
                  source: 'marka-desktop',
                  timestamp: new Date().toISOString()
                }
              }
            }),
          'GCP upload'
        )
      );
    }

    // Upload to AWS if configured
    if (this.clients.aws && process.env.AWS_BUCKET_NAME) {
      uploadPromises.push(
        this.retryOperation(
          () => {
            const fileContent = fs.readFile(syncPackagePath);
            return this.clients.aws.upload({
              Bucket: process.env.AWS_BUCKET_NAME,
              Key: `sync/${fileName}`,
              Body: fileContent,
              ContentType: 'application/octet-stream',
              Metadata: {
                source: 'marka-desktop',
                timestamp: new Date().toISOString()
              }
            }).promise();
          },
          'AWS upload'
        )
      );
    }

    // Execute all uploads in parallel
    if (uploadPromises.length > 0) {
      await Promise.all(uploadPromises);
    } else {
      throw new Error('No cloud providers configured for sync');
    }
  }

  async downloadSyncPackage() {
    // Determine which cloud provider to use
    const provider = process.env.PRIMARY_CLOUD_PROVIDER || 
                    (this.clients.gcp ? 'gcp' : 'aws') || 
                    Object.keys(this.clients)[0];

    if (!provider) {
      throw new Error('No cloud providers configured for sync');
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const syncPackagePath = path.join(require('os').tmpdir(), `marka-sync-download-${timestamp}.msync`);

    try {
      if (provider === 'gcp') {
        // Get latest sync file from GCP
        const [files] = await this.clients.gcp.bucket(process.env.GCP_BUCKET_NAME)
          .getFiles({ prefix: 'sync/', autoPaginate: false });

        if (files.length === 0) {
          throw new Error('No sync files found in GCP bucket');
        }

        const latestFile = files.sort((a, b) => 
          new Date(b.metadata.updated) - new Date(a.metadata.updated)
        )[0];

        await this.retryOperation(
          () => latestFile.download({ destination: syncPackagePath }),
          'GCP download'
        );
      } else if (provider === 'aws') {
        // Get latest sync file from AWS
        const data = await this.clients.aws.listObjectsV2({
          Bucket: process.env.AWS_BUCKET_NAME,
          Prefix: 'sync/'
        }).promise();

        if (!data.Contents || data.Contents.length === 0) {
          throw new Error('No sync files found in AWS bucket');
        }

        const latestFile = data.Contents.sort((a, b) => 
          new Date(b.LastModified) - new Date(a.LastModified)
        )[0];

        const fileData = await this.retryOperation(
          () => this.clients.aws.getObject({
            Bucket: process.env.AWS_BUCKET_NAME,
            Key: latestFile.Key
          }).promise(),
          'AWS download'
        );

        await fs.writeFile(syncPackagePath, fileData.Body);
      }

      return syncPackagePath;
    } catch (error) {
      log.error('Failed to download sync package:', error);
      throw error;
    }
  }

  async applySyncPackage(syncPackagePath) {
    try {
      // Create temp directory for extraction
      const extractDir = path.join(require('os').tmpdir(), `marka-sync-extract-${Date.now()}`);
      await fs.mkdir(extractDir, { recursive: true });

      // Decrypt and extract the package
      const decipher = crypto.createDecipheriv(
        'aes-256-gcm',
        crypto.scryptSync(this.options.encryptionKey, 'salt', 32),
        crypto.randomBytes(16)
      );

      await new Promise((resolve, reject) => {
        fs.createReadStream(syncPackagePath)
          .pipe(decipher)
          .pipe(require('zlib').createGunzip())
          .pipe(require('tar').x({ cwd: extractDir }))
          .on('finish', resolve)
          .on('error', reject);
      });

      // Read manifest
      const manifestPath = path.join(extractDir, 'manifest.json');
      const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));

      // Verify database hash
      const dbPath = path.join(extractDir, 'database.db');
      const currentHash = await this.hashFile(dbPath);
      if (currentHash !== manifest.dbHash) {
        throw new Error('Database hash verification failed');
      }

      // Apply conflict resolution
      if (this.options.conflictResolution === 'server') {
        // Replace local database with server version
        await this.replaceDatabase(dbPath);
      } else {
        // Client wins - merge changes (would need more complex implementation)
        await this.mergeDatabases(dbPath);
      }

      // Clean up
      await fs.rm(extractDir, { recursive: true, force: true });
    } catch (error) {
      log.error('Failed to apply sync package:', error);
      throw error;
    }
  }

  async replaceDatabase(newDbPath) {
    const userDataPath = require('electron').app.getPath('userData');
    const currentDbPath = path.join(userDataPath, 'marka_database.db');
    const backupPath = path.join(userDataPath, 'marka_database.backup');

    try {
      // Create backup of current database
      await fs.copyFile(currentDbPath, backupPath);

      // Replace database
      await fs.copyFile(newDbPath, currentDbPath);

      // Notify main process to reload database
      require('electron').ipcRenderer.send('database-reload');
    } catch (error) {
      // Restore backup if replacement failed
      if (await fs.access(backupPath).then(() => true).catch(() => false)) {
        await fs.copyFile(backupPath, currentDbPath);
      }
      throw error;
    } finally {
      // Clean up backup
      await fs.unlink(backupPath).catch(() => {});
    }
  }

  async mergeDatabases(newDbPath) {
    // This would require a more sophisticated implementation
    // using the better-sqlite3 backup API or similar
    throw new Error('Database merge not yet implemented');
  }

  async hashFile(filePath) {
    return new Promise((resolve, reject) => {
      const hash = crypto.createHash('sha256');
      const stream = fs.createReadStream(filePath);

      stream.on('error', reject);
      stream.on('data', chunk => hash.update(chunk));
      stream.on('end', () => resolve(hash.digest('hex')));
    });
  }

  async retryOperation(operation, operationName) {
    let lastError;
    for (let attempt = 1; attempt <= this.options.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        log.warn(`${operationName} attempt ${attempt} failed:`, error);
        if (attempt < this.options.maxRetries) {
          await new Promise(resolve => setTimeout(resolve, this.options.retryDelay));
        }
      }
    }
    throw lastError;
  }

  /**
   * Gets sync status
   * @returns {Object} Sync status information
   */
  getStatus() {
    return {
      status: this.syncStatus,
      lastSync: this.lastSync,
      nextSync: this.syncInterval ? 
        new Date(Date.now() + this.options.syncInterval) : null,
      providers: Object.keys(this.clients)
    };
  }
}

module.exports = CloudSyncManager;