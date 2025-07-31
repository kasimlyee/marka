const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');
const { app } = require('electron');
const axios = require('axios');
const { machineIdSync } = require('node-machine-id');
const log = require('electron-log');

class LicenseManager {
  constructor() {
    this.licenseFile = null;
    this.currentLicense = null;
    this.machineId = null;
    this.validationInterval = null;
    this.apiEndpoint = 'https://api.marka.codewithlyee.com/license';
    this.publicKey = null;
    this.licenseTypes = {
      'STANDARD': {
        name: 'Standard',
        features: ['basic_reporting', 'student_management', 'grade_entry'],
        limits: { students: 1000, custom_templates: 2, cloud_sync: false }
      },
      'PRO': {
        name: 'Pro',
        features: ['basic_reporting', 'student_management', 'grade_entry', 'advanced_analytics', 'bulk_operations'],
        limits: { students: 5000, custom_templates: 10, cloud_sync: false }
      },
      'ENTERPRISE': {
        name: 'Enterprise',
        features: ['basic_reporting', 'student_management', 'grade_entry', 'advanced_analytics', 'bulk_operations', 'cloud_sync', 'multi_user', 'api_access'],
        limits: { students: -1, custom_templates: -1, cloud_sync: true }
      },
      'LIFETIME': {
        name: 'Lifetime',
        features: ['basic_reporting', 'student_management', 'grade_entry', 'advanced_analytics', 'bulk_operations', 'cloud_sync', 'multi_user', 'api_access', 'priority_support'],
        limits: { students: -1, custom_templates: -1, cloud_sync: true }
      }
    };
    
    this.initialize();
  }

  /**
   * Initializes the LicenseManager.
   *
   * Initializes the machine ID, sets the license file path, loads the RSA public key,
   * loads the existing license, and starts the periodic validation.
   *
   * @returns {Promise<void>} A promise that resolves when the LicenseManager has been
   * initialized.
   */
  async initialize() {
    try {
      // Get machine ID for hardware fingerprinting
      this.machineId = machineIdSync();
      
      // Set license file path
      const userData = app.getPath('userData');
      this.licenseFile = path.join(userData, '.marka_license');
      
      // Load RSA public key for license verification
      await this.loadPublicKey();
      
      // Load existing license
      await this.loadLicense();
      
      // Start periodic validation
      this.startPeriodicValidation();
      
      log.info('LicenseManager initialized successfully');
    } catch (error) {
      log.error('Failed to initialize LicenseManager:', error);
      // Don't throw error - allow app to run with limited functionality
    }
  }

  async loadPublicKey() {
    // In production, this would be embedded or downloaded from a secure source
    this.publicKey = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuGbXWiK3dQTyCbX5xdE4
yCuYp0nt7S130Z1vUNiQVlelJdxHPdHgzN+2eAx+SdB7QaWdyocjg3w4bUKOcGhO
mDDz+kc4Hnn2vBPLHFsYwBNlLrLa5AV3T7LlC8pJtUjH8FtGqQ1YLSi5fvq9SV7E
a9B7c0hRq7x2N4BLe8Z1a1v3XqAZx5h8k6GbzY8OB9oGJW0kEsw4yCKsJo6FZTrv
4cOEp8m6ykTk7xd3fGk2Y3tUeNe8JoB6tBKP4KcYGQJkO5jW5hcJnxoD4eJtXqLi
wL9dL6UX1SeL4Qk6sKOzE5RFp8VNJtUl5jM7y9xPV4cQ1pAQKhJtbK5GYJFDfB
QIDAQAB
-----END PUBLIC KEY-----`;
  }

  async loadLicense() {
    try {
      const licenseData = await fs.readFile(this.licenseFile, 'utf8');
      const parsed = JSON.parse(licenseData);
      
      // Verify license signature
      const isValid = await this.verifyLicenseSignature(parsed);
      
      if (isValid) {
        this.currentLicense = parsed;
        log.info('License loaded successfully:', {
          type: parsed.type,
          expiry: parsed.expiry,
          machineId: parsed.machineId
        });
      } else {
        log.warn('Invalid license signature detected');
        this.currentLicense = null;
      }
    } catch (error) {
      log.info('No valid license file found, running in trial mode');
      this.currentLicense = null;
    }
  }

  async saveLicense(licenseData) {
    try {
      await fs.writeFile(this.licenseFile, JSON.stringify(licenseData, null, 2), { mode: 0o600 });
      log.info('License saved successfully');
    } catch (error) {
      log.error('Failed to save license:', error);
      throw error;
    }
  }

  /**
   * Activates a license with the given license key.
   *
   * Validates the license key format, contacts the license server for activation,
   * verifies the received license signature, and saves the new license data.
   * If successful, updates the current license and returns activation details.
   *
   * @param {string} licenseKey - The license key to be activated.
   * @returns {Promise<Object>} A promise that resolves to an object containing
   * the activation success status and license information, or an error message
   * if activation fails.
   */

  async activateLicense(licenseKey) {
    try {
      // Validate license key format
      if (!this.validateLicenseKeyFormat(licenseKey)) {
        throw new Error('Invalid license key format');
      }

      // Contact license server for activation
      const activationData = await this.contactLicenseServer('activate', {
        licenseKey,
        machineId: this.machineId,
        appVersion: app.getVersion(),
        platform: process.platform,
        arch: process.arch
      });

      // Verify the received license
      const isValid = await this.verifyLicenseSignature(activationData);
      if (!isValid) {
        throw new Error('Received invalid license from server');
      }

      // Save and load the new license
      await this.saveLicense(activationData);
      this.currentLicense = activationData;

      log.info('License activated successfully:', {
        type: activationData.type,
        expiry: activationData.expiry
      });

      return {
        success: true,
        license: this.getLicenseInfo()
      };

    } catch (error) {
      log.error('License activation failed:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Verifies the current license by checking its basic validity and periodically
   * contacting the license server for validation.
   *
   * If the license is invalid or has not been validated with the server within the
   * last 24 hours, this method will contact the server and update the license with
   * the latest validation result.
   *
   * @returns {Promise<boolean>} A promise that resolves to true if the license is
   * valid and false otherwise.
   */
  async verifyLicense() {
    try {
      if (!this.currentLicense) {
        return false;
      }

      // Check basic validity
      if (!this.isLicenseValid()) {
        return false;
      }

      // Periodic server validation (every 24 hours)
      const lastValidation = this.currentLicense.lastValidation || 0;
      const now = Date.now();
      const validationInterval = 24 * 60 * 60 * 1000; // 24 hours

      if (now - lastValidation > validationInterval) {
        const serverValid = await this.validateWithServer();
        if (serverValid) {
          this.currentLicense.lastValidation = now;
          await this.saveLicense(this.currentLicense);
        } else {
          log.warn('Server validation failed for license');
          return false;
        }
      }

      return true;
    } catch (error) {
      log.error('License verification error:', error);
      return false;
    }
  }

  /**
   * Validates the current license to ensure it is still valid.
   *
   * Checks include:
   * - Whether a current license is loaded.
   * - The expiration date of the license, ensuring it has not expired.
   * - The machine ID, verifying it matches the expected hardware fingerprint.
   * - The license type, confirming it is recognized and valid.
   *
   * @returns {boolean} True if the license is valid, false otherwise.
   */

  isLicenseValid() {
    if (!this.currentLicense) {
      return false;
    }

    // Check expiry
    if (this.currentLicense.expiry !== 'never' && Date.now() > new Date(this.currentLicense.expiry).getTime()) {
      log.info('License has expired');
      return false;
    }

    // Check machine ID (hardware fingerprint)
    if (this.currentLicense.machineId !== this.machineId) {
      log.warn('License machine ID mismatch');
      return false;
    }

    // Check license type
    if (!this.licenseTypes[this.currentLicense.type]) {
      log.warn('Unknown license type:', this.currentLicense.type);
      return false;
    }

    return true;
  }

  /**
   * Verifies the signature of the provided license data.
   *
   * This method checks the integrity and authenticity of the license data
   * by verifying its signature using the RSA public key. It ensures that
   * the data has not been tampered with and originates from a trusted source.
   *
   * @param {Object} licenseData - The license data containing the signature
   * and other related information.
   * @returns {Promise<boolean>} A promise that resolves to true if the
   * signature is valid, or false otherwise.
   * @throws Will log an error and return false if the signature verification
   * process fails.
   */

  async verifyLicenseSignature(licenseData) {
    try {
      if (!licenseData.signature || !this.publicKey) {
        return false;
      }

      // Create data string for verification (excluding signature)
      const { signature, ...dataToVerify } = licenseData;
      const dataString = JSON.stringify(dataToVerify, Object.keys(dataToVerify).sort());

      // Verify signature
      const verifier = crypto.createVerify('SHA256');
      verifier.update(dataString);
      
      return verifier.verify(this.publicKey, signature, 'base64');
    } catch (error) {
      log.error('Signature verification error:', error);
      return false;
    }
  }

/**
 * Validates the format of the given license key.
 *
 * This function checks whether the provided license key matches
 * the expected format: MARKA-XXXXX-XXXXX-XXXXX-XXXXX, where each
 * 'X' is an alphanumeric character (A-Z, 0-9).
 *
 * @param {string} licenseKey - The license key to validate.
 * @returns {boolean} True if the license key format is valid, false otherwise.
 */

  validateLicenseKeyFormat(licenseKey) {
    // Expected format: MARKA-XXXXX-XXXXX-XXXXX-XXXXX
    const pattern = /^MARKA-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$/;
    return pattern.test(licenseKey);
  }

  /**
   * Contacts the license server with the given action and data.
   *
   * Makes a POST request to the license server with the given action and data.
   * If the request is successful and the server returns a valid response, the
   * license object is returned. Otherwise, an error is thrown.
   *
   * @param {string} action - The action to perform on the license server.
   * @param {Object} data - The data to send with the request.
   * @returns {Promise<Object>} A promise that resolves with the license object
   * if the request is successful, or rejects with an error if the request fails.
   */
  async contactLicenseServer(action, data) {
    try {
      const response = await axios.post(`${this.apiEndpoint}/${action}`, data, {
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': `Marka/${app.getVersion()} (${process.platform})`
        }
      });

      if (response.status === 200 && response.data.success) {
        return response.data.license || response.data;
      } else {
        throw new Error(response.data.error || 'Server request failed');
      }
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.error || 'Server error');
      } else if (error.request) {
        throw new Error('Unable to contact license server. Please check your internet connection.');
      } else {
        throw error;
      }
    }
  }

  /**
   * Contacts the license server for validation.
   *
   * Makes a POST request to the license server with the license ID, machine ID,
   * and a checksum of the license data. If the request is successful and the
   * server returns a valid response, the validity of the license is returned.
   * Otherwise, an error is thrown and caught, and the function returns true if
   * the error indicates that the server is unreachable.
   *
   * @returns {Promise<boolean>} A promise that resolves to true if the license is
   * valid, or false otherwise.
   */
  async validateWithServer() {
    try {
      const response = await this.contactLicenseServer('validate', {
        licenseId: this.currentLicense.id,
        machineId: this.machineId,
        checksum: this.calculateLicenseChecksum()
      });

      return response.valid === true;
    } catch (error) {
      log.warn('Server validation failed:', error.message);
      // Return true for offline validation if server is unreachable
      return error.message.includes('contact license server');
    }
  }

  /**
   * Calculates a SHA-256 checksum of the current license data.
   *
   * @returns {string} A SHA-256 checksum of the current license data, or null if
   * the current license is not set.
   */
  calculateLicenseChecksum() {
    if (!this.currentLicense) return null;
    
    const data = {
      id: this.currentLicense.id,
      type: this.currentLicense.type,
      machineId: this.currentLicense.machineId,
      expiry: this.currentLicense.expiry
    };
    
    return crypto.createHash('sha256').update(JSON.stringify(data)).digest('hex');
  }

  /**
   * Gets the current license information.
   *
   * Returns an object containing the current license type, name, status, features,
   * limits, expiry date, days remaining, validity, machine ID, activation date,
   * and last validation date.
   *
   * @returns {Object} An object containing the current license information.
   */
  getLicenseInfo() {
    if (!this.currentLicense) {
      return {
        type: 'TRIAL',
        status: 'trial',
        features: ['basic_reporting', 'student_management'],
        limits: { students: 50, custom_templates: 1, cloud_sync: false },
        expiry: null,
        daysRemaining: null,
        isValid: false
      };
    }

    const licenseType = this.licenseTypes[this.currentLicense.type];
    const now = new Date();
    const expiry = this.currentLicense.expiry === 'never' ? null : new Date(this.currentLicense.expiry);
    
    let daysRemaining = null;
    if (expiry) {
      daysRemaining = Math.max(0, Math.ceil((expiry - now) / (1000 * 60 * 60 * 24)));
    }

    return {
      type: this.currentLicense.type,
      name: licenseType.name,
      status: this.isLicenseValid() ? 'active' : 'invalid',
      features: licenseType.features,
      limits: licenseType.limits,
      expiry: this.currentLicense.expiry,
      daysRemaining,
      isValid: this.isLicenseValid(),
      machineId: this.currentLicense.machineId,
      activationDate: this.currentLicense.activationDate,
      lastValidation: this.currentLicense.lastValidation
    };
  }

  /**
   * Checks if the current license has a given feature.
   *
   * @param {string} featureName - The name of the feature to check.
   * @returns {boolean} True if the current license has the feature, false otherwise.
   */
  hasFeature(featureName) {
    const licenseInfo = this.getLicenseInfo();
    return licenseInfo.features.includes(featureName);
  }

/**
 * Checks if the current usage value is within the specified limit for the current license.
 *
 * @param {string} limitName - The name of the limit to check.
 * @param {number} currentValue - The current usage value to compare against the limit.
 * @returns {Object} An object containing:
 *   - {boolean} allowed - True if the current usage is within the limit, false otherwise.
 *   - {number} remaining - The number of remaining units allowed, or -1 for unlimited.
 *   - {number} limit - The limit value.
 */

  checkLimit(limitName, currentValue) {
    const licenseInfo = this.getLicenseInfo();
    const limit = licenseInfo.limits[limitName];
    
    if (limit === -1) {
      return { allowed: true, remaining: -1 }; // Unlimited
    }
    
    return {
      allowed: currentValue < limit,
      remaining: Math.max(0, limit - currentValue),
      limit
    };
  }

  /**
   * Deactivates the current license.
   *
   * This method notifies the license server of the deactivation and removes
   * the local license file. If the current license exists, it contacts the
   * server to perform the deactivation process. The local license data is
   * then deleted to ensure the application is no longer associated with the
   * deactivated license.
   *
   * @returns {Promise<Object>} A promise that resolves to an object indicating
   * the success status of the deactivation. If successful, the object contains
   * `success: true`; otherwise, it contains `success: false` and an error message.
   */

  async deactivateLicense() {
    try {
      if (this.currentLicense) {
        // Notify server about deactivation
        await this.contactLicenseServer('deactivate', {
          licenseId: this.currentLicense.id,
          machineId: this.machineId
        });
      }

      // Remove local license file
      try {
        await fs.unlink(this.licenseFile);
      } catch (error) {
        // File might not exist, ignore error
      }

      this.currentLicense = null;
      
      log.info('License deactivated successfully');
      return { success: true };
    } catch (error) {
      log.error('License deactivation failed:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Transfers the current license to a new machine ID.
   *
   * Initiates the license transfer process by contacting the license server.
   * If the transfer is successful, the server returns a transfer ID that can
   * be used to later activate the license on the new machine. If the transfer
   * fails, an error is returned and the license remains active on the current
   * machine.
   *
   * @param {string} newMachineId - The new machine ID to transfer the license to.
   * @returns {Promise<Object>} A promise that resolves to an object containing
   * the success status of the transfer. If successful, the object contains
   * `success: true` and a `transferId` property; otherwise, it contains
   * `success: false` and an `error` property.
   */
  async transferLicense(newMachineId) {
    try {
      if (!this.currentLicense) {
        throw new Error('No active license to transfer');
      }

      const response = await this.contactLicenseServer('transfer', {
        licenseId: this.currentLicense.id,
        oldMachineId: this.machineId,
        newMachineId: newMachineId
      });

      log.info('License transfer initiated');
      return { success: true, transferId: response.transferId };
    } catch (error) {
      log.error('License transfer failed:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Renews the current license by contacting the license server.
   *
   * If the renewal is successful, the server returns a new expiry date for
   * the license. The license is then updated with the new expiry date and
   * saved to disk.
   *
   * @returns {Promise<Object>} A promise that resolves to an object containing
   * the success status of the renewal. If successful, the object contains
   * `success: true` and a `newExpiry` property; otherwise, it contains
   * `success: false` and an `error` property.
   */
  async renewLicense() {
    try {
      if (!this.currentLicense) {
        throw new Error('No license to renew');
      }

      const response = await this.contactLicenseServer('renew', {
        licenseId: this.currentLicense.id,
        machineId: this.machineId
      });

      // Update license with new expiry
      this.currentLicense.expiry = response.newExpiry;
      this.currentLicense.lastValidation = Date.now();
      
      await this.saveLicense(this.currentLicense);
      
      log.info('License renewed successfully:', { newExpiry: response.newExpiry });
      return { success: true, newExpiry: response.newExpiry };
    } catch (error) {
      log.error('License renewal failed:', error);
      return { success: false, error: error.message };
    }
  }

/**
 * Starts the periodic license validation process.
 *
 * Sets up an interval to verify the license every hour. If the license is not
 * valid during this periodic check, a warning is logged. Errors that occur
 * during the validation process are caught and logged as errors.
 */

  startPeriodicValidation() {
    // Validate license every hour
    this.validationInterval = setInterval(async () => {
      try {
        const isValid = await this.verifyLicense();
        if (!isValid && this.currentLicense) {
          log.warn('License validation failed during periodic check');
        }
      } catch (error) {
        log.error('Periodic license validation error:', error);
      }
    }, 60 * 60 * 1000); // 1 hour
  }

/**
 * Stops the periodic license validation process.
 *
 * Clears the interval set for periodic license validation if it exists,
 * effectively halting further periodic checks. This method ensures that
 * license validation does not continue to run unnecessarily, freeing up
 * resources.
 */

  stopPeriodicValidation() {
    if (this.validationInterval) {
      clearInterval(this.validationInterval);
      this.validationInterval = null;
    }
  }

  // Generate trial license for testing
  generateTrialLicense() {
    const trialExpiry = new Date();
    trialExpiry.setDate(trialExpiry.getDate() + 30); // 30-day trial

    return {
      id: 'TRIAL-' + crypto.randomUUID(),
      type: 'TRIAL',
      machineId: this.machineId,
      expiry: trialExpiry.toISOString(),
      activationDate: new Date().toISOString(),
      isTrial: true,
      features: ['basic_reporting', 'student_management'],
      limits: { students: 50, custom_templates: 1, cloud_sync: false }
    };
  }

  // License analytics
  async getLicenseAnalytics() {
    try {
      if (!this.currentLicense) {
        return null;
      }

      const response = await this.contactLicenseServer('analytics', {
        licenseId: this.currentLicense.id,
        machineId: this.machineId
      });

      return response.analytics;
    } catch (error) {
      log.error('Failed to fetch license analytics:', error);
      return null;
    }
  }

  // Offline validation fallback
  generateOfflineCode() {
    if (!this.currentLicense) {
      return null;
    }

    const data = {
      licenseId: this.currentLicense.id,
      machineId: this.machineId,
      timestamp: Date.now()
    };

    const code = crypto.createHash('sha256')
      .update(JSON.stringify(data))
      .digest('hex')
      .substring(0, 16)
      .toUpperCase();

    return {
      code,
      instructions: 'Contact support with this code for offline activation',
      validFor: '7 days'
    };
  }

  async validateOfflineCode(offlineCode) {
    try {
      // Will impliment this later
      
      const response = await this.contactLicenseServer('offline-validate', {
        offlineCode,
        machineId: this.machineId
      });

      if (response.valid) {
        // Update license with offline validation
        this.currentLicense.lastValidation = Date.now();
        this.currentLicense.offlineValidated = true;
        await this.saveLicense(this.currentLicense);
        
        return { success: true };
      } else {
        return { success: false, error: 'Invalid offline code' };
      }
    } catch (error) {
      log.error('Offline code validation failed:', error);
      return { success: false, error: error.message };
    }
  }

  // Health check
  async performHealthCheck() {
    const health = {
      status: 'healthy',
      license: null,
      warnings: [],
      errors: []
    };

    try {
      // Check license validity
      const licenseInfo = this.getLicenseInfo();
      health.license = licenseInfo;

      if (!licenseInfo.isValid) {
        health.status = 'warning';
        health.warnings.push('License is not valid or has expired');
      }

      // Check expiry warning (30 days)
      if (licenseInfo.daysRemaining !== null && licenseInfo.daysRemaining <= 30) {
        health.warnings.push(`License expires in ${licenseInfo.daysRemaining} days`);
        if (health.status === 'healthy') {
          health.status = 'warning';
        }
      }

      // Check server connectivity
      try {
        await axios.get(`${this.apiEndpoint}/health`, { timeout: 5000 });
      } catch (error) {
        health.warnings.push('Unable to contact license server');
        if (health.status === 'healthy') {
          health.status = 'warning';
        }
      }

    } catch (error) {
      health.status = 'unhealthy';
      health.errors.push(error.message);
    }

    return health;
  }

  /**
   * Cleans up the LicenseManager instance.
   *
   * Stops periodic validation and removes the current license.
   */
  cleanup() {
    this.stopPeriodicValidation();
    this.currentLicense = null;
    log.info('LicenseManager cleanup completed');
  }
}

module.exports = LicenseManager;