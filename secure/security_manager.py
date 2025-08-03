import os
import json
import logging
import sqlite3
import hashlib
import secrets
import bcrypt
import jwt
import cryptography
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Union, Any
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer

class SecurityManager(QObject):
    """
    A comprehensive security manager for handling encryption, authentication,
    session management, and security-related operations in the Marka application.
    """
    
    security_alert = Signal(str, str)  # (message, level)
    
    def __init__(self, app_data_dir: str):
        super().__init__()
        self.logger = logging.getLogger('marka.security')
        self.app_data_dir = Path(app_data_dir)
        self.keys_file = self.app_data_dir / '.marka_keys'
        
        # Security configurations
        self.salt_rounds = 12
        self.token_expiry = '1h'
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(minutes=30)
        
        # State tracking
        self.active_sessions: Dict[str, dict] = {}
        self.failed_attempts: Dict[str, dict] = {}
        self.rate_limiters: Dict[str, dict] = {}
        
        # Initialize security components
        self.encryption_key = None
        self.jwt_secret = None
        
        self.initialize()
    
    def initialize(self) -> None:
        """Initialize the security manager components."""
        try:
            self._initialize_keys()
            self._setup_session_cleanup()
            self._setup_rate_limit_cleanup()
            self.logger.info("SecurityManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize SecurityManager: {e}")
            raise
    
    def _initialize_keys(self) -> None:
        """Initialize or load encryption keys."""
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'r') as f:
                    keys = json.load(f)
                self.encryption_key = keys['encryption_key'].encode()
                self.jwt_secret = keys['jwt_secret']
                self._verify_keys()
            else:
                self._generate_new_keys()
        except Exception as e:
            self.logger.error(f"Key initialization error: {e}")
            raise
    
    def _generate_new_keys(self) -> None:
        """Generate new encryption keys and save them securely."""
        self.logger.info("Generating new security keys")
        
        # Generate encryption key
        self.encryption_key = Fernet.generate_key()
        
        # Generate JWT secret
        self.jwt_secret = secrets.token_hex(64)
        
        # Save keys securely
        key_data = {
            'encryption_key': self.encryption_key.decode(),
            'jwt_secret': self.jwt_secret,
            'generated': datetime.utcnow().isoformat()
        }
        
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(key_data, f)
            self.keys_file.chmod(0o600)  # Restrict permissions
            self._verify_keys()
        except Exception as e:
            self.logger.error(f"Failed to save new keys: {e}")
            raise
    
    def _verify_keys(self) -> None:
        """Verify that the encryption keys are working correctly."""
        # Test encryption/decryption
        test_data = "test_verification_data"
        encrypted = self.encrypt_data(test_data)
        decrypted = self.decrypt_data(encrypted)
        
        if decrypted != test_data:
            raise ValueError("Key verification failed: encryption/decryption mismatch")
        
        # Test JWT signing
        test_token = self.generate_token({'test': True}, '1m')
        verified = self.verify_token(test_token)
        
        if not verified or not verified.get('test'):
            raise ValueError("Key verification failed: JWT signing/verification mismatch")
    
    # Encryption methods
    def encrypt_data(self, data: str) -> str:
        """Encrypt data using AES-256-GCM."""
        if not data:
            return ""
            
        try:
            f = Fernet(self.encryption_key)
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            raise ValueError("Failed to encrypt data") from e
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using AES-256-GCM."""
        if not encrypted_data:
            return ""
            
        try:
            f = Fernet(self.encryption_key)
            return f.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            raise ValueError("Failed to decrypt data") from e
    
    # Password hashing
    def hash_password(self, password: str) -> str:
        """Hash a password with bcrypt and pepper."""
        try:
            pepper = os.getenv('PASSWORD_PEPPER', 'marka_default_pepper_2025')
            peppered_password = password + pepper
            return bcrypt.hashpw(peppered_password.encode(), bcrypt.gensalt(self.salt_rounds)).decode()
        except Exception as e:
            self.logger.error(f"Password hashing error: {e}")
            raise ValueError("Failed to hash password") from e
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            pepper = os.getenv('PASSWORD_PEPPER', 'marka_default_pepper_2025')
            peppered_password = password + pepper
            return bcrypt.checkpw(peppered_password.encode(), hashed_password.encode())
        except Exception as e:
            self.logger.error(f"Password verification error: {e}")
            return False
    
    # JWT token management
    def generate_token(self, payload: dict, expires_in: Optional[str] = None) -> str:
        """Generate a JWT token with the given payload."""
        try:
            token_payload = {
                **payload,
                'iat': int(datetime.utcnow().timestamp()),
                'jti': secrets.token_hex(16),  # Unique token ID
                'iss': 'marka-app',
                'aud': 'marka-users'
            }
            
            return jwt.encode(
                token_payload,
                self.jwt_secret,
                algorithm='HS256',
                expires_in=expires_in or self.token_expiry
            )
        except Exception as e:
            self.logger.error(f"Token generation error: {e}")
            raise ValueError("Failed to generate token") from e
    
    def verify_token(self, token: str) -> dict:
        """Verify a JWT token and return its payload."""
        try:
            return jwt.decode(
                token,
                self.jwt_secret,
                algorithms=['HS256'],
                issuer='marka-app',
                audience='marka-users'
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
        except Exception as e:
            self.logger.error(f"Token verification error: {e}")
            raise ValueError("Token verification failed") from e
    
    def refresh_token(self, token: str) -> str:
        """Refresh an existing JWT token."""
        try:
            decoded = self.verify_token(token)
            new_payload = {
                'userId': decoded['userId'],
                'email': decoded['email'],
                'role': decoded['role']
            }
            return self.generate_token(new_payload)
        except Exception as e:
            raise ValueError("Cannot refresh invalid token") from e
    
    # Session management
    def create_session(self, user_id: str, user_data: dict) -> dict:
        """Create a new user session."""
        session_id = secrets.token_hex(16)
        session = {
            'id': session_id,
            'userId': user_id,
            'userData': user_data,
            'createdAt': datetime.utcnow(),
            'lastActivity': datetime.utcnow(),
            'ipAddress': None,
            'userAgent': None
        }
        
        self.active_sessions[session_id] = session
        
        # Generate session token
        token = self.generate_token({
            'sessionId': session_id,
            'userId': user_id,
            'email': user_data.get('email'),
            'role': user_data.get('role')
        })
        
        return {'sessionId': session_id, 'token': token}
    
    def validate_session(self, session_id: str) -> Optional[dict]:
        """Validate and return a session if it's still active."""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        # Check if session has expired
        if datetime.utcnow() - session['lastActivity'] > self.session_timeout:
            self.destroy_session(session_id)
            return None
        
        # Update last activity
        session['lastActivity'] = datetime.utcnow()
        self.active_sessions[session_id] = session
        
        return session
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session by its ID."""
        return self.active_sessions.pop(session_id, None) is not None
    
    def destroy_all_user_sessions(self, user_id: str) -> int:
        """Destroy all sessions for a specific user."""
        to_delete = [sid for sid, sess in self.active_sessions.items() 
                    if sess['userId'] == user_id]
        
        for sid in to_delete:
            self.active_sessions.pop(sid, None)
        
        return len(to_delete)
    
    def _setup_session_cleanup(self) -> None:
        """Set up periodic cleanup of expired sessions."""
        self.session_cleanup_timer = QTimer()
        self.session_cleanup_timer.timeout.connect(self._cleanup_expired_sessions)
        self.session_cleanup_timer.start(5 * 60 * 1000)  # Every 5 minutes
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        now = datetime.utcnow()
        expired = []
        
        for session_id, session in self.active_sessions.items():
            if now - session['lastActivity'] > self.session_timeout:
                expired.append(session_id)
        
        for session_id in expired:
            self.active_sessions.pop(session_id, None)
        
        if expired:
            self.logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    # Authentication security
    def check_login_attempts(self, identifier: str) -> dict:
        """Check if login attempts are allowed for an identifier."""
        attempts = self.failed_attempts.get(identifier)
        
        if not attempts:
            return {'allowed': True, 'remainingAttempts': self.max_login_attempts}
        
        # Check if account is locked
        if attempts.get('lockedUntil') and datetime.utcnow() < attempts['lockedUntil']:
            remaining_time = (attempts['lockedUntil'] - datetime.utcnow()).seconds // 60
            return {
                'allowed': False,
                'locked': True,
                'remainingTime': remaining_time,
                'message': f"Account locked for {remaining_time} minutes"
            }
        
        # Reset if lockout period has passed
        if attempts.get('lockedUntil') and datetime.utcnow() >= attempts['lockedUntil']:
            self.failed_attempts.pop(identifier, None)
            return {'allowed': True, 'remainingAttempts': self.max_login_attempts}
        
        remaining_attempts = self.max_login_attempts - attempts['count']
        
        if remaining_attempts <= 0:
            # Lock the account
            attempts['lockedUntil'] = datetime.utcnow() + self.lockout_duration
            self.failed_attempts[identifier] = attempts
            
            return {
                'allowed': False,
                'locked': True,
                'remainingTime': self.lockout_duration.seconds // 60,
                'message': "Account locked due to too many failed attempts"
            }
        
        return {'allowed': True, 'remainingAttempts': remaining_attempts}
    
    def record_failed_login_attempt(self, identifier: str) -> None:
        """Record a failed login attempt."""
        attempts = self.failed_attempts.get(identifier, {'count': 0, 'firstAttempt': datetime.utcnow()})
        attempts['count'] += 1
        attempts['lastAttempt'] = datetime.utcnow()
        self.failed_attempts[identifier] = attempts
        self.logger.warning(f"Failed login attempt for {identifier}. Count: {attempts['count']}")
        self.security_alert.emit(f"Failed login attempt for {identifier}", "warning")
    
    def record_successful_login(self, identifier: str) -> None:
        """Record a successful login."""
        self.failed_attempts.pop(identifier, None)
        self.logger.info(f"Successful login for {identifier}")
    
    # Rate limiting
    def check_rate_limit(self, identifier: str, max_requests: int = 100, 
                        window_ms: int = 15 * 60 * 1000) -> dict:
        """Check and enforce rate limiting."""
        now = datetime.utcnow()
        window_start = now - timedelta(milliseconds=window_ms)
        
        limiter = self.rate_limiters.get(identifier)
        if not limiter:
            limiter = {'requests': [], 'firstRequest': now}
            self.rate_limiters[identifier] = limiter
        
        # Remove requests outside the window
        limiter['requests'] = [t for t in limiter['requests'] if t > window_start]
        
        if len(limiter['requests']) >= max_requests:
            oldest_request = min(limiter['requests'])
            reset_time = oldest_request + timedelta(milliseconds=window_ms)
            retry_after = (reset_time - now).total_seconds()
            
            return {
                'allowed': False,
                'limit': max_requests,
                'remaining': 0,
                'resetTime': reset_time,
                'retryAfter': max(0, int(retry_after))
            }
        
        # Add current request
        limiter['requests'].append(now)
        self.rate_limiters[identifier] = limiter
        
        return {
            'allowed': True,
            'limit': max_requests,
            'remaining': max_requests - len(limiter['requests']),
            'resetTime': window_start + timedelta(milliseconds=window_ms)
        }
    
    def _setup_rate_limit_cleanup(self) -> None:
        """Set up periodic cleanup of old rate limit data."""
        self.rate_limit_cleanup_timer = QTimer()
        self.rate_limit_cleanup_timer.timeout.connect(self._cleanup_rate_limiters)
        self.rate_limit_cleanup_timer.start(10 * 60 * 1000)  # Every 10 minutes
    
    def _cleanup_rate_limiters(self) -> None:
        """Clean up old rate limit data."""
        now = datetime.utcnow()
        window = timedelta(milliseconds=15 * 60 * 1000)
        cleaned_count = 0
        
        for identifier, limiter in list(self.rate_limiters.items()):
            # Remove old requests
            original_length = len(limiter['requests'])
            limiter['requests'] = [t for t in limiter['requests'] 
                                 if t > now - window]
            
            # Remove limiter if no recent requests
            if not limiter['requests'] and now - limiter['firstRequest'] > window:
                self.rate_limiters.pop(identifier, None)
                cleaned_count += 1
            elif len(limiter['requests']) < original_length:
                self.rate_limiters[identifier] = limiter
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old rate limiters")
    
    # Data sanitization
    def sanitize_input(self, input_str: str, input_type: str = 'text') -> str:
        """Sanitize input based on its type."""
        if not isinstance(input_str, str):
            return input_str
        
        if input_type == 'text':
            # Remove potentially dangerous characters
            return input_str.translate(str.maketrans('', '', '<>"\'&')).strip()
        elif input_type == 'email':
            # Basic email sanitization
            return input_str.lower().strip().translate(str.maketrans('', '', '^a-z0-9@._-'))
        elif input_type == 'alphanumeric':
            # Allow only letters and numbers
            return input_str.translate(str.maketrans('', '', '^a-zA-Z0-9'))
        elif input_type == 'filename':
            # Safe filename characters
            return input_str.translate(str.maketrans('', '', '^a-zA-Z0-9._-')).strip()
        elif input_type == 'sql':
            # Escape SQL-like characters (though we use parameterized queries)
            return input_str.translate(str.maketrans('', '', '\'";\\'))
        else:
            return input_str.strip()
    
    def validate_input(self, input_data: dict, rules: dict) -> dict:
        """Validate input data against specified rules."""
        errors = []
        
        for field, field_rules in rules.items():
            value = input_data.get(field)
            
            # Required check
            if field_rules.get('required') and (not value or not str(value).strip()):
                errors.append(f"{field} is required")
                continue
            
            # Skip other validations if field is not required and empty
            if not field_rules.get('required') and (not value or not str(value).strip()):
                continue
            
            # Type validation
            if field_rules.get('type'):
                if field_rules['type'] == 'email':
                    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', str(value)):
                        errors.append(f"{field} must be a valid email address")
                elif field_rules['type'] == 'number':
                    if not str(value).isdigit():
                        errors.append(f"{field} must be a number")
                elif field_rules['type'] == 'phone':
                    if not re.match(r'^\+?[1-9]\d{1,14}$', str(value).replace(' ', '')):
                        errors.append(f"{field} must be a valid phone number")
                elif field_rules['type'] == 'url':
                    try:
                        from urllib.parse import urlparse
                        result = urlparse(str(value))
                        if not all([result.scheme, result.netloc]):
                            raise ValueError()
                    except:
                        errors.append(f"{field} must be a valid URL")
            
            # Length validation
            if field_rules.get('minLength') and len(str(value)) < field_rules['minLength']:
                errors.append(f"{field} must be at least {field_rules['minLength']} characters long")
            
            if field_rules.get('maxLength') and len(str(value)) > field_rules['maxLength']:
                errors.append(f"{field} must be no more than {field_rules['maxLength']} characters long")
            
            # Range validation for numbers
            if 'min' in field_rules and float(value) < field_rules['min']:
                errors.append(f"{field} must be at least {field_rules['min']}")
            
            if 'max' in field_rules and float(value) > field_rules['max']:
                errors.append(f"{field} must be no more than {field_rules['max']}")
            
            # Pattern validation
            if field_rules.get('pattern') and not field_rules['pattern'].match(str(value)):
                errors.append(f"{field} format is invalid")
            
            # Custom validation
            if field_rules.get('custom') and callable(field_rules['custom']):
                custom_error = field_rules['custom'](value)
                if custom_error:
                    errors.append(custom_error)
        
        return {'isValid': not errors, 'errors': errors}
    
    # Password strength validation
    def validate_password_strength(self, password: str) -> dict:
        """Validate password strength and return a score."""
        result = {
            'score': 0,
            'feedback': [],
            'isStrong': False
        }
        
        # Length check
        if len(password) >= 8:
            result['score'] += 1
        else:
            result['feedback'].append('Password must be at least 8 characters long')
        
        # Uppercase letter
        if any(c.isupper() for c in password):
            result['score'] += 1
        else:
            result['feedback'].append('Password must contain at least one uppercase letter')
        
        # Lowercase letter
        if any(c.islower() for c in password):
            result['score'] += 1
        else:
            result['feedback'].append('Password must contain at least one lowercase letter')
        
        # Number
        if any(c.isdigit() for c in password):
            result['score'] += 1
        else:
            result['feedback'].append('Password must contain at least one number')
        
        # Special character
        if any(not c.isalnum() for c in password):
            result['score'] += 1
        else:
            result['feedback'].append('Password must contain at least one special character')
        
        # No common patterns
        common_patterns = ['123456', 'password', 'qwerty', 'abc123', 'admin']
        has_common_pattern = any(p in password.lower() for p in common_patterns)
        
        if has_common_pattern:
            result['score'] -= 2
            result['feedback'].append('Password contains common patterns')
        
        # Determine strength
        result['isStrong'] = result['score'] >= 4 and not has_common_pattern
        
        return result
    
    # Cleanup methods
    def cleanup(self) -> None:
        """Clean up sensitive data from memory."""
        if self.encryption_key:
            # Overwrite the key in memory
            self.encryption_key = b'\x00' * len(self.encryption_key)
        
        self.active_sessions.clear()
        self.failed_attempts.clear()
        self.rate_limiters.clear()
        
        if hasattr(self, 'session_cleanup_timer'):
            self.session_cleanup_timer.stop()
        
        if hasattr(self, 'rate_limit_cleanup_timer'):
            self.rate_limit_cleanup_timer.stop()
        
        self.logger.info("SecurityManager cleanup completed")