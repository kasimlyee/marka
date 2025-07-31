const crypto = require('crypto');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { app } = require('electron');
const path = require('path');
const fs = require('fs').promises;
const log = require('electron-log');

class SecurityManager {
  /**
   * Constructor for the SecurityManager class.
   * 
   * Initializes the security manager with the default settings. The manager is
   * responsible for managing the encryption key, JWT secret, user sessions, and
   * rate limiting.
   * 
   * @param {Object} [options] - Options to initialize the security manager with.
   * @param {string} [options.encryptionKey] - The key to use for encryption.
   * @param {string} [options.jwtSecret] - The secret to use for signing JWTs.
   * @param {number} [options.saltRounds] - The number of salt rounds to use for hashing.
   * @param {string} [options.tokenExpiry] - The expiry time for the authentication token.
   * @param {number} [options.maxLoginAttempts] - The maximum number of login attempts allowed before the user is locked out.
   * @param {number} [options.lockoutDuration] - The duration of the lockout period in milliseconds.
   * @param {number} [options.sessionTimeout] - The duration of the session timeout in milliseconds.
   */
  constructor() {
    this.encryptionKey = null;
    this.jwtSecret = null;
    this.saltRounds = 12;
    this.tokenExpiry = '1h';
    this.maxLoginAttempts = 5;
    this.lockoutDuration = 15 * 60 * 1000; // 15 minutes
    this.sessionTimeout = 30 * 60 * 1000; // 30 minutes
    this.activeSessions = new Map();
    this.failedAttempts = new Map();
    this.rateLimiters = new Map();
    
    this.initialize();
  }

  /**
   * Initializes the SecurityManager.
   *
   * This function initializes the encryption keys, sets up periodic cleanup
   * tasks for user sessions and rate limiting, and logs a message on successful
   * initialization. If an error occurs during initialization, it logs the error
   * and throws it to be handled by the caller.
   *
   * @returns {Promise<void>} A promise that resolves when the SecurityManager
   * has been successfully initialized.
   * @throws Will throw an error if the initialization process fails.
   */

  async initialize() {
    try {
      // Initialize encryption keys
      await this.initializeKeys();
      
      // Setup session cleanup
      this.setupSessionCleanup();
      
      // Setup rate limiting cleanup
      this.setupRateLimitCleanup();
      
      log.info('SecurityManager initialized successfully');
    } catch (error) {
      log.error('Failed to initialize SecurityManager:', error);
      throw error;
    }
  }

  /**
   * Initializes the encryption keys.
   *
   * This function attempts to load encryption keys from the .marka_keys file in
   * the user data directory. If the file does not exist or the keys are invalid,
   * it generates new keys and saves them to the file. The keys are verified to be
   * valid and secure. If the verification fails, an error is thrown.
   *
   * @returns {Promise<void>} A promise that resolves when the encryption keys
   * have been successfully initialized.
   * @throws Will throw an error if the initialization process fails.
   */
  async initializeKeys() {
    const userData = app.getPath('userData');
    const keyPath = path.join(userData, '.marka_keys');
    
    try {
      // Try to load existing keys
      const keyData = await fs.readFile(keyPath, 'utf8');
      const keys = JSON.parse(keyData);
      
      this.encryptionKey = Buffer.from(keys.encryptionKey, 'hex');
      this.jwtSecret = keys.jwtSecret;
      
      // Verify keys are valid
      await this.verifyKeys();
      
    } catch (error) {
      // Generate new keys if none exist or are invalid
      log.info('Generating new security keys');
      await this.generateNewKeys(keyPath);
    }
  }

  /**
   * Generates new encryption keys and saves them to the given file path.
   *
   * This function generates a 256-bit encryption key and a JWT secret. It then
   * saves the keys to the given file path in a secure manner and verifies that the
   * keys are valid.
   *
   * @param {string} keyPath The file path to save the keys to.
   * @returns {Promise<void>} A promise that resolves when the keys have been
   * successfully generated and saved.
   * @throws Will throw an error if the key generation or saving process fails.
   */
  async generateNewKeys(keyPath) {
    // Generate 256-bit encryption key
    this.encryptionKey = crypto.randomBytes(32);
    
    // Generate JWT secret
    this.jwtSecret = crypto.randomBytes(64).toString('hex');
    
    // Save keys securely
    const keyData = {
      encryptionKey: this.encryptionKey.toString('hex'),
      jwtSecret: this.jwtSecret,
      generated: new Date().toISOString()
    };
    
    await fs.writeFile(keyPath, JSON.stringify(keyData), { mode: 0o600 });
    
    // Verify new keys
    await this.verifyKeys();
  }

  /**
   * Verifies that the encryption keys are valid and working correctly.
   *
   * This function performs two tests to verify the encryption keys:
   * 1. It tests the encryption and decryption functions by encrypting a test
   *    string and then decrypting it to verify that the decrypted string is the
   *    same as the original.
   * 2. It tests the JWT signing and verification functions by generating a test
   *    token and then verifying it to ensure that the verification succeeds and
   *    that the decoded payload contains the expected data.
   *
   * If either of the tests fail, an error is thrown.
   *
   * @returns {Promise<void>} A promise that resolves when the verification is
   * successful, or rejects with an error if the verification fails.
   * @throws Will throw an error if the verification process fails.
   */
  async verifyKeys() {
    // Test encryption/decryption
    const testData = 'test_verification_data';
    const encrypted = await this.encryptData(testData);
    const decrypted = await this.decryptData(encrypted);
    
    if (decrypted !== testData) {
      throw new Error('Key verification failed: encryption/decryption mismatch');
    }
    
    // Test JWT signing
    const testToken = this.generateToken({ test: true }, '1m');
    const verified = this.verifyToken(testToken);
    
    if (!verified || !verified.test) {
      throw new Error('Key verification failed: JWT signing/verification mismatch');
    }
  }

  // Encryption methods
  async encryptData(data, encoding = 'utf8') {
    try {
      if (!data) return null;
      
      const iv = crypto.randomBytes(16);
      const cipher = crypto.createCipher('aes-256-gcm', this.encryptionKey, iv);
      
      let encrypted = cipher.update(data, encoding, 'hex');
      encrypted += cipher.final('hex');
      
      const authTag = cipher.getAuthTag();
      
      // Combine iv, authTag, and encrypted data
      const result = {
        iv: iv.toString('hex'),
        authTag: authTag.toString('hex'),
        data: encrypted
      };
      
      return JSON.stringify(result);
    } catch (error) {
      log.error('Encryption error:', error);
      throw new Error('Failed to encrypt data');
    }
  }

  /**
   * Decrypts encrypted data using the AES-256-GCM algorithm.
   * 
   * The encrypted data should be a string in the format of a JSON object with
   * the following properties:
   * 
   * - iv: The initialization vector used for encryption.
   * - authTag: The authentication tag used to verify the integrity of the data.
   * - data: The encrypted data as a hex string.
   * 
   * @param {string} encryptedData The encrypted data to decrypt.
   * @param {string} [encoding='utf8'] The encoding to use for the decrypted data.
   * @returns {Promise<string>} A promise that resolves with the decrypted data.
   * @throws Will throw an error if the decryption fails.
   */
  async decryptData(encryptedData, encoding = 'utf8') {
    try {
      if (!encryptedData) return null;
      
      const parsed = JSON.parse(encryptedData);
      const iv = Buffer.from(parsed.iv, 'hex');
      const authTag = Buffer.from(parsed.authTag, 'hex');
      
      const decipher = crypto.createDecipher('aes-256-gcm', this.encryptionKey, iv);
      decipher.setAuthTag(authTag);
      
      let decrypted = decipher.update(parsed.data, 'hex', encoding);
      decrypted += decipher.final(encoding);
      
      return decrypted;
    } catch (error) {
      log.error('Decryption error:', error);
      throw new Error('Failed to decrypt data');
    }
  }

  // Password hashing
  async hashPassword(password) {
    try {
      // Add pepper for extra security
      const pepper = process.env.PASSWORD_PEPPER || 'marka_default_pepper_2025';
      const pepperedPassword = password + pepper;
      
      return await bcrypt.hash(pepperedPassword, this.saltRounds);
    } catch (error) {
      log.error('Password hashing error:', error);
      throw new Error('Failed to hash password');
    }
  }

  /**
   * Verifies a password against a hash.
   *
   * This function takes a plaintext password and a hash, and verifies that the
   * password matches the hash. The verification is done using the bcrypt
   * library, and the hash is salted with a pepper value.
   *
   * @param {string} password The plaintext password to verify.
   * @param {string} hash The hash to verify against.
   * @returns {Promise<boolean>} A promise that resolves with true if the
   * password matches the hash, or false if it does not.
   */
  async verifyPassword(password, hash) {
    try {
      const pepper = process.env.PASSWORD_PEPPER || 'marka_default_pepper_2025';
      const pepperedPassword = password + pepper;
      
      return await bcrypt.compare(pepperedPassword, hash);
    } catch (error) {
      log.error('Password verification error:', error);
      return false;
    }
  }

  // JWT token management
  generateToken(payload, expiresIn = null) {
    try {
      const options = {
        expiresIn: expiresIn || this.tokenExpiry,
        issuer: 'marka-app',
        audience: 'marka-users'
      };
      
      const tokenPayload = {
        ...payload,
        iat: Math.floor(Date.now() / 1000),
        jti: crypto.randomUUID() // Unique token ID
      };
      
      return jwt.sign(tokenPayload, this.jwtSecret, options);
    } catch (error) {
      log.error('Token generation error:', error);
      throw new Error('Failed to generate token');
    }
  }

  /**
   * Verifies a JWT token.
   *
   * This function takes a JWT token and verifies it against the configured
   * secret. The verification is done using the jsonwebtoken library, and the
   * token is verified to have been issued by the correct issuer and for the
   * correct audience.
   *
   * @param {string} token The JWT token to verify.
   * @returns {Promise<Object>} A promise that resolves with the decoded token
   * payload if the verification is successful, or rejects with an error if the
   * verification fails.
   */
  verifyToken(token) {
    try {
      const options = {
        issuer: 'marka-app',
        audience: 'marka-users'
      };
      
      return jwt.verify(token, this.jwtSecret, options);
    } catch (error) {
      if (error.name === 'TokenExpiredError') {
        throw new Error('Token has expired');
      } else if (error.name === 'JsonWebTokenError') {
        throw new Error('Invalid token');
      } else {
        log.error('Token verification error:', error);
        throw new Error('Token verification failed');
      }
    }
  }

  /**
   * Refreshes an existing JWT token.
   *
   * This function takes an existing JWT token, verifies it, and generates a new token
   * with the same payload but updated expiry. If the token is invalid or cannot be
   * verified, an error is thrown.
   *
   * @param {string} token The JWT token to refresh.
   * @returns {string} A new JWT token with updated expiry if the original token is valid.
   * @throws Will throw an error if the token is invalid or cannot be verified.
   */

  refreshToken(token) {
    try {
      const decoded = this.verifyToken(token);
      
      // Create new token with updated expiry
      const newPayload = {
        userId: decoded.userId,
        email: decoded.email,
        role: decoded.role
      };
      
      return this.generateToken(newPayload);
    } catch (error) {
      throw new Error('Cannot refresh invalid token');
    }
  }

  // Session management
  createSession(userId, userData) {
    const sessionId = crypto.randomUUID();
    const session = {
      id: sessionId,
      userId,
      userData,
      createdAt: Date.now(),
      lastActivity: Date.now(),
      ipAddress: null, // Would be set from request in web context
      userAgent: null
    };
    
    this.activeSessions.set(sessionId, session);
    
    // Generate session token
    const token = this.generateToken({
      sessionId,
      userId,
      email: userData.email,
      role: userData.role
    });
    
    return { sessionId, token };
  }

  /**
   * Validates a session and returns the session object if it is valid.
   *
   * If the session does not exist or has expired, null is returned.
   *
   * @param {string} sessionId The ID of the session to validate.
   * @returns {?Object} The session object if the session is valid, null otherwise.
   */
  validateSession(sessionId) {
    const session = this.activeSessions.get(sessionId);
    
    if (!session) {
      return null;
    }
    
    // Check if session has expired
    if (Date.now() - session.lastActivity > this.sessionTimeout) {
      this.destroySession(sessionId);
      return null;
    }
    
    // Update last activity
    session.lastActivity = Date.now();
    this.activeSessions.set(sessionId, session);
    
    return session;
  }

  destroySession(sessionId) {
  
/*************  ✨ Windsurf Command ⭐  *************/
/**
 * Destroys a session by its ID.
 *
 * This function removes the session from the active sessions map,
 * effectively logging the user out. If the session ID is found and
 * successfully deleted, the function returns true. Otherwise, it
 * returns false if the session ID does not exist.
 *
 * @param {string} sessionId The ID of the session to destroy.
 * @returns {boolean} True if the session was successfully destroyed, false otherwise.
 */

/*******  723aa5b4-5c16-479a-82c1-02cffca472b5  *******/    return this.activeSessions.delete(sessionId);

  }

  destroyAllUserSessions(userId) {
    let destroyedCount = 0;
    
    for (const [sessionId, session] of this.activeSessions.entries()) {
      if (session.userId === userId) {
        this.activeSessions.delete(sessionId);
        destroyedCount++;
      }
    }
    
    return destroyedCount;
  }

/*************  ✨ Windsurf Command ⭐  *************/
/**
 * Sets up periodic cleanup of expired sessions.
 *
 * This function schedules a cleanup task that runs every 5 minutes. It iterates
 * through all active sessions, checking if each session's last activity exceeds
 * the configured session timeout. If a session is expired, it is removed from
 * the active sessions map. Logs the number of sessions cleaned up if any were removed.
 */

/*******  5aa5b8d8-7029-48f3-b076-fe3ca75c00fb  *******/
  setupSessionCleanup() {
    // Clean up expired sessions every 5 minutes
    setInterval(() => {
      const now = Date.now();
      const expiredSessions = [];
      
      for (const [sessionId, session] of this.activeSessions.entries()) {
        if (now - session.lastActivity > this.sessionTimeout) {
          expiredSessions.push(sessionId);
        }
      }
      
      expiredSessions.forEach(sessionId => {
        this.activeSessions.delete(sessionId);
      });
      
      if (expiredSessions.length > 0) {
        log.info(`Cleaned up ${expiredSessions.length} expired sessions`);
      }
    }, 5 * 60 * 1000);
  }

  // Authentication security
  async checkLoginAttempts(identifier) {
    const attempts = this.failedAttempts.get(identifier);
    
    if (!attempts) {
      return { allowed: true, remainingAttempts: this.maxLoginAttempts };
    }
    
    // Check if account is locked
    if (attempts.lockedUntil && Date.now() < attempts.lockedUntil) {
      const remainingTime = Math.ceil((attempts.lockedUntil - Date.now()) / 1000 / 60);
      return {
        allowed: false,
        locked: true,
        remainingTime: remainingTime,
        message: `Account locked for ${remainingTime} minutes`
      };
    }
    
    // Reset if lockout period has passed
    if (attempts.lockedUntil && Date.now() >= attempts.lockedUntil) {
      this.failedAttempts.delete(identifier);
      return { allowed: true, remainingAttempts: this.maxLoginAttempts };
    }
    
    const remainingAttempts = this.maxLoginAttempts - attempts.count;
    
    if (remainingAttempts <= 0) {
      // Lock the account
      attempts.lockedUntil = Date.now() + this.lockoutDuration;
      this.failedAttempts.set(identifier, attempts);
      
      return {
        allowed: false,
        locked: true,
        remainingTime: Math.ceil(this.lockoutDuration / 1000 / 60),
        message: `Account locked due to too many failed attempts`
      };
    }
    
    return { allowed: true, remainingAttempts };
  }

  recordFailedLoginAttempt(identifier) {
    const attempts = this.failedAttempts.get(identifier) || { count: 0, firstAttempt: Date.now() };
    
    attempts.count++;
    attempts.lastAttempt = Date.now();
    
    this.failedAttempts.set(identifier, attempts);
    
    log.warn(`Failed login attempt for ${identifier}. Count: ${attempts.count}`);
  }

  recordSuccessfulLogin(identifier) {
    // Clear failed attempts on successful login
    this.failedAttempts.delete(identifier);
    log.info(`Successful login for ${identifier}`);
  }

  // Rate limiting
  checkRateLimit(identifier, maxRequests = 100, windowMs = 15 * 60 * 1000) {
    const now = Date.now();
    const windowStart = now - windowMs;
    
    let limiter = this.rateLimiters.get(identifier);
    
    if (!limiter) {
      limiter = { requests: [], firstRequest: now };
      this.rateLimiters.set(identifier, limiter);
    }
    
    // Remove requests outside the window
    limiter.requests = limiter.requests.filter(timestamp => timestamp > windowStart);
    
    if (limiter.requests.length >= maxRequests) {
      const oldestRequest = Math.min(...limiter.requests);
      const resetTime = oldestRequest + windowMs;
      
      return {
        allowed: false,
        limit: maxRequests,
        remaining: 0,
        resetTime: new Date(resetTime),
        retryAfter: Math.ceil((resetTime - now) / 1000)
      };
    }
    
    // Add current request
    limiter.requests.push(now);
    this.rateLimiters.set(identifier, limiter);
    
    return {
      allowed: true,
      limit: maxRequests,
      remaining: maxRequests - limiter.requests.length,
      resetTime: new Date(windowStart + windowMs)
    };
  }

  setupRateLimitCleanup() {
    // Clean up old rate limit data every 10 minutes
    setInterval(() => {
      const now = Date.now();
      const windowMs = 15 * 60 * 1000; // 15 minutes
      let cleanedCount = 0;
      
      for (const [identifier, limiter] of this.rateLimiters.entries()) {
        // Remove old requests
        const originalLength = limiter.requests.length;
        limiter.requests = limiter.requests.filter(timestamp => timestamp > now - windowMs);
        
        // Remove limiter if no recent requests
        if (limiter.requests.length === 0 && now - limiter.firstRequest > windowMs) {
          this.rateLimiters.delete(identifier);
          cleanedCount++;
        } else if (limiter.requests.length < originalLength) {
          this.rateLimiters.set(identifier, limiter);
        }
      }
      
      if (cleanedCount > 0) {
        log.info(`Cleaned up ${cleanedCount} old rate limiters`);
      }
    }, 10 * 60 * 1000);
  }

  // Data sanitization
  sanitizeInput(input, type = 'text') {
    if (typeof input !== 'string') {
      return input;
    }
    
    switch (type) {
      case 'text':
        // Remove potentially dangerous characters
        return input.replace(/[<>\"'&]/g, '').trim();
        
      case 'email':
        // Basic email sanitization
        return input.toLowerCase().trim().replace(/[^a-z0-9@._-]/g, '');
        
      case 'alphanumeric':
        // Allow only letters and numbers
        return input.replace(/[^a-zA-Z0-9]/g, '');
        
      case 'filename':
        // Safe filename characters
        return input.replace(/[^a-zA-Z0-9._-]/g, '').trim();
        
      case 'sql':
        // Escape SQL-like characters (though we use prepared statements)
        return input.replace(/['";\\]/g, '');
        
      default:
        return input.trim();
    }
  }

  validateInput(input, rules) {
    const errors = [];
    
    for (const [field, fieldRules] of Object.entries(rules)) {
      const value = input[field];
      
      // Required check
      if (fieldRules.required && (!value || value.toString().trim() === '')) {
        errors.push(`${field} is required`);
        continue;
      }
      
      // Skip other validations if field is not required and empty
      if (!fieldRules.required && (!value || value.toString().trim() === '')) {
        continue;
      }
      
      // Type validation
      if (fieldRules.type) {
        switch (fieldRules.type) {
          case 'email':
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
              errors.push(`${field} must be a valid email address`);
            }
            break;
            
          case 'number':
            if (isNaN(value)) {
              errors.push(`${field} must be a number`);
            }
            break;
            
          case 'phone':
            const phoneRegex = /^\+?[1-9]\d{1,14}$/;
            if (!phoneRegex.test(value.replace(/\s/g, ''))) {
              errors.push(`${field} must be a valid phone number`);
            }
            break;
            
          case 'url':
            try {
              new URL(value);
            } catch {
              errors.push(`${field} must be a valid URL`);
            }
            break;
        }
      }
      
      // Length validation
      if (fieldRules.minLength && value.length < fieldRules.minLength) {
        errors.push(`${field} must be at least ${fieldRules.minLength} characters long`);
      }
      
      if (fieldRules.maxLength && value.length > fieldRules.maxLength) {
        errors.push(`${field} must be no more than ${fieldRules.maxLength} characters long`);
      }
      
      // Range validation for numbers
      if (fieldRules.min !== undefined && parseFloat(value) < fieldRules.min) {
        errors.push(`${field} must be at least ${fieldRules.min}`);
      }
      
      if (fieldRules.max !== undefined && parseFloat(value) > fieldRules.max) {
        errors.push(`${field} must be no more than ${fieldRules.max}`);
      }
      
      // Pattern validation
      if (fieldRules.pattern && !fieldRules.pattern.test(value)) {
        errors.push(`${field} format is invalid`);
      }
      
      // Custom validation
      if (fieldRules.custom && typeof fieldRules.custom === 'function') {
        const customError = fieldRules.custom(value);
        if (customError) {
          errors.push(customError);
        }
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  // Secure file operations
  validateFilePath(filePath, allowedExtensions = []) {
    // Prevent directory traversal
    const normalizedPath = path.normalize(filePath);
    if (normalizedPath.includes('..')) {
      throw new Error('Invalid file path: directory traversal detected');
    }
    
    // Check file extension if restrictions apply
    if (allowedExtensions.length > 0) {
      const extension = path.extname(normalizedPath).toLowerCase();
      if (!allowedExtensions.includes(extension)) {
        throw new Error(`File type not allowed. Allowed types: ${allowedExtensions.join(', ')}`);
      }
    }
    
    return normalizedPath;
  }

  async secureFileWrite(filePath, data, options = {}) {
    try {
      // Validate file path
      const safePath = this.validateFilePath(filePath, options.allowedExtensions);
      
      // Ensure directory exists
      await fs.mkdir(path.dirname(safePath), { recursive: true });
      
      // Encrypt data if required
      let finalData = data;
      if (options.encrypt) {
        finalData = await this.encryptData(data);
      }
      
      // Write with secure permissions
      await fs.writeFile(safePath, finalData, { 
        mode: options.mode || 0o600,
        ...options 
      });
      
      return safePath;
    } catch (error) {
      log.error('Secure file write error:', error);
      throw error;
    }
  }

  async secureFileRead(filePath, options = {}) {
    try {
      // Validate file path
      const safePath = this.validateFilePath(filePath, options.allowedExtensions);
      
      // Read file
      let data = await fs.readFile(safePath, options.encoding || 'utf8');
      
      // Decrypt if required
      if (options.encrypted) {
        data = await this.decryptData(data);
      }
      
      return data;
    } catch (error) {
      log.error('Secure file read error:', error);
      throw error;
    }
  }

  // Security headers and CSP
  generateCSPHeader() {
    return [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'", // Needed for React development
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "font-src 'self' data:",
      "connect-src 'self' https://api.marka.codewithlyee.com",
      "media-src 'self'",
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'"
    ].join('; ');
  }

  getSecurityHeaders() {
    return {
      'Content-Security-Policy': this.generateCSPHeader(),
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
      'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    };
  }

  // Audit logging security
  createSecureAuditLog(userId, action, details, ipAddress = null) {
    const auditEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      userId,
      action,
      details: this.sanitizeAuditDetails(details),
      ipAddress,
      userAgent: null, // Would be populated in web context
      hash: null // Will be calculated
    };
    
    // Create hash for integrity verification
    const dataToHash = JSON.stringify({
      id: auditEntry.id,
      timestamp: auditEntry.timestamp,
      userId: auditEntry.userId,
      action: auditEntry.action,
      details: auditEntry.details
    });
    
    auditEntry.hash = crypto.createHash('sha256').update(dataToHash).digest('hex');
    
    return auditEntry;
  }

  sanitizeAuditDetails(details) {
    if (typeof details !== 'object' || details === null) {
      return details;
    }
    
    const sanitized = { ...details };
    
    // Remove sensitive fields
    const sensitiveFields = ['password', 'password_hash', 'token', 'secret', 'key'];
    sensitiveFields.forEach(field => {
      if (sanitized[field]) {
        sanitized[field] = '[REDACTED]';
      }
    });
    
    return sanitized;
  }

  verifyAuditLogIntegrity(auditEntry) {
    const { hash, ...dataWithoutHash } = auditEntry;
    const calculatedHash = crypto.createHash('sha256')
      .update(JSON.stringify(dataWithoutHash))
      .digest('hex');
    
    return hash === calculatedHash;
  }

  // Two-factor authentication support
  generateTOTPSecret() {
    return crypto.randomBytes(20).toString('base32');
  }

  generateBackupCodes(count = 10) {
    const codes = [];
    for (let i = 0; i < count; i++) {
      // Generate 8-character alphanumeric codes
      const code = crypto.randomBytes(4).toString('hex').toUpperCase();
      codes.push(code);
    }
    return codes;
  }

  // Machine fingerprinting for license validation
  async generateMachineFingerprint() {
    const os = require('os');
    
    const fingerprint = {
      hostname: os.hostname(),
      platform: os.platform(),
      arch: os.arch(),
      cpus: os.cpus().length,
      memory: os.totalmem(),
      networkInterfaces: Object.keys(os.networkInterfaces()),
      userInfo: os.userInfo().username
    };
    
    // Create hash of fingerprint data
    const fingerprintString = JSON.stringify(fingerprint);
    const hash = crypto.createHash('sha256').update(fingerprintString).digest('hex');
    
    return {
      fingerprint: hash,
      details: fingerprint
    };
  }

  // Secure random generation
  generateSecureRandomString(length = 32, charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') {
    let result = '';
    const charactersLength = charset.length;
    
    for (let i = 0; i < length; i++) {
      const randomIndex = crypto.randomInt(0, charactersLength);
      result += charset.charAt(randomIndex);
    }
    
    return result;
  }

  generateSecurePin(length = 6) {
    let pin = '';
    for (let i = 0; i < length; i++) {
      pin += crypto.randomInt(0, 10).toString();
    }
    return pin;
  }

  // Password strength validation
  validatePasswordStrength(password) {
    const result = {
      score: 0,
      feedback: [],
      isStrong: false
    };
    
    // Length check
    if (password.length >= 8) {
      result.score += 1;
    } else {
      result.feedback.push('Password must be at least 8 characters long');
    }
    
    // Uppercase letter
    if (/[A-Z]/.test(password)) {
      result.score += 1;
    } else {
      result.feedback.push('Password must contain at least one uppercase letter');
    }
    
    // Lowercase letter
    if (/[a-z]/.test(password)) {
      result.score += 1;
    } else {
      result.feedback.push('Password must contain at least one lowercase letter');
    }
    
    // Number
    if (/\d/.test(password)) {
      result.score += 1;
    } else {
      result.feedback.push('Password must contain at least one number');
    }
    
    // Special character
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
      result.score += 1;
    } else {
      result.feedback.push('Password must contain at least one special character');
    }
    
    // No common patterns
    const commonPatterns = ['123456', 'password', 'qwerty', 'abc123', 'admin'];
    const hasCommonPattern = commonPatterns.some(pattern => 
      password.toLowerCase().includes(pattern)
    );
    
    if (hasCommonPattern) {
      result.score -= 2;
      result.feedback.push('Password contains common patterns');
    }
    
    // Determine strength
    result.isStrong = result.score >= 4 && !hasCommonPattern;
    
    return result;
  }

  // Security monitoring
  detectSuspiciousActivity(userId, activity) {
    const suspicious = {
      detected: false,
      reasons: [],
      riskLevel: 'low'
    };
    
    // Multiple failed logins
    const failedAttempts = this.failedAttempts.get(userId);
    if (failedAttempts && failedAttempts.count > 3) {
      suspicious.detected = true;
      suspicious.reasons.push('Multiple failed login attempts');
      suspicious.riskLevel = 'medium';
    }
    
    // Unusual activity patterns could be added here
    // - Login from different locations
    // - Unusual time patterns
    // - Rapid successive actions
    
    if (suspicious.detected) {
      log.warn(`Suspicious activity detected for user ${userId}:`, suspicious);
    }
    
    return suspicious;
  }

  // Data anonymization for exports
  anonymizeData(data, fields = []) {
    if (!Array.isArray(data)) {
      return data;
    }
    
    return data.map(record => {
      const anonymized = { ...record };
      
      fields.forEach(field => {
        if (anonymized[field]) {
          switch (field) {
            case 'email':
              // Keep domain, anonymize local part
              const emailParts = anonymized[field].split('@');
              if (emailParts.length === 2) {
                anonymized[field] = `***@${emailParts[1]}`;
              }
              break;
              
            case 'phone':
              // Keep last 4 digits
              const phone = anonymized[field].toString();
              anonymized[field] = '***' + phone.slice(-4);
              break;
              
            case 'name':
              // Keep first letter and last name
              const nameParts = anonymized[field].split(' ');
              if (nameParts.length > 1) {
                anonymized[field] = nameParts[0][0] + '*** ' + nameParts[nameParts.length - 1];
              } else {
                anonymized[field] = nameParts[0][0] + '***';
              }
              break;
              
            default:
              anonymized[field] = '***';
          }
        }
      });
      
      return anonymized;
    });
  }

  // Security health check
  async performSecurityHealthCheck() {
    const health = {
      status: 'healthy',
      checks: {},
      warnings: [],
      errors: []
    };
    
    try {
      // Check encryption keys
      health.checks.encryptionKeys = await this.testEncryptionKeys();
      
      // Check active sessions
      health.checks.activeSessions = {
        count: this.activeSessions.size,
        status: this.activeSessions.size < 100 ? 'ok' : 'warning'
      };
      
      if (this.activeSessions.size >= 100) {
        health.warnings.push('High number of active sessions');
      }
      
      // Check failed login attempts
      health.checks.failedAttempts = {
        count: this.failedAttempts.size,
        status: this.failedAttempts.size < 50 ? 'ok' : 'warning'
      };
      
      if (this.failedAttempts.size >= 50) {
        health.warnings.push('High number of failed login attempts');
      }
      
      // Check rate limiters
      health.checks.rateLimiters = {
        count: this.rateLimiters.size,
        status: this.rateLimiters.size < 1000 ? 'ok' : 'warning'
      };
      
      // Overall status
      if (health.errors.length > 0) {
        health.status = 'unhealthy';
      } else if (health.warnings.length > 0) {
        health.status = 'warning';
      }
      
    } catch (error) {
      health.status = 'unhealthy';
      health.errors.push(error.message);
    }
    
    return health;
  }

  async testEncryptionKeys() {
    try {
      const testData = 'encryption_test_' + Date.now();
      const encrypted = await this.encryptData(testData);
      const decrypted = await this.decryptData(encrypted);
      
      return {
        status: testData === decrypted ? 'ok' : 'error',
        tested: true
      };
    } catch (error) {
      return {
        status: 'error',
        error: error.message,
        tested: false
      };
    }
  }

  // Cleanup methods
  cleanup() {
    // Clear sensitive data from memory
    if (this.encryptionKey) {
      this.encryptionKey.fill(0);
    }
    
    this.activeSessions.clear();
    this.failedAttempts.clear();
    this.rateLimiters.clear();
    
    log.info('SecurityManager cleanup completed');
  }
}

module.exports = SecurityManager;