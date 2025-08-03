import os
import json
import logging
import hashlib
import uuid
import jwt
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Union
from PySide6.QtCore import QObject, Signal, QTimer
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

class LicenseManager(QObject):
    """
    Manages license validation, activation, and feature checks for the Marka application.
    """
    
    license_status_changed = Signal(dict)  # Emits current license info when status changes
    
    def __init__(self, app):
        super().__init__()
        self.logger = logging.getLogger('marka.license')
        self.app = app
        self.user_data_dir = Path(app.get_user_data_dir())
        self.license_file = self.user_data_dir / '.marka_license'
        
        # License types and their features
        self.license_types = {
            'STANDARD': {
                'name': 'Standard',
                'features': ['basic_reporting', 'student_management', 'grade_entry'],
                'limits': {'students': 1000, 'custom_templates': 2, 'cloud_sync': False}
            },
            'PRO': {
                'name': 'Pro',
                'features': ['basic_reporting', 'student_management', 'grade_entry', 
                           'advanced_analytics', 'bulk_operations'],
                'limits': {'students': 5000, 'custom_templates': 10, 'cloud_sync': False}
            },
            'ENTERPRISE': {
                'name': 'Enterprise',
                'features': ['basic_reporting', 'student_management', 'grade_entry', 
                           'advanced_analytics', 'bulk_operations', 'cloud_sync', 
                           'multi_user', 'api_access'],
                'limits': {'students': -1, 'custom_templates': -1, 'cloud_sync': True}
            },
            'LIFETIME': {
                'name': 'Lifetime',
                'features': ['basic_reporting', 'student_management', 'grade_entry', 
                           'advanced_analytics', 'bulk_operations', 'cloud_sync', 
                           'multi_user', 'api_access', 'priority_support'],
                'limits': {'students': -1, 'custom_templates': -1, 'cloud_sync': True}
            }
        }
        
        # Server configuration
        self.api_endpoint = 'https://api.marka.codewithlyee.com/license'
        self.public_key = None
        self.validation_interval = None
        
        # Current state
        self.current_license = None
        self.machine_id = self._get_machine_id()
        
        self.initialize()
    
    def initialize(self) -> None:
        """Initialize the license manager."""
        try:
            self._load_public_key()
            self._load_license()
            self._start_periodic_validation()
            self.logger.info("LicenseManager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize LicenseManager: {e}")
            # Allow app to run with limited functionality
    
    def _get_machine_id(self) -> str:
        """Generate a unique machine ID for hardware fingerprinting."""
        try:
            # This is a simplified approach - in production you might want to use
            # a more robust method that combines multiple hardware identifiers
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()
        except:
            # Fallback to a random ID if we can't get the machine ID
            return str(uuid.uuid4())
    
    def _load_public_key(self) -> None:
        """Load the RSA public key for license verification."""
        # In production, this would be embedded or downloaded from a secure source
        public_key_pem = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuGbXWiK3dQTyCbX5xdE4
yCuYp0nt7S130Z1vUNiQVlelJdxHPdHgzN+2eAx+SdB7QaWdyocjg3w4bUKOcGhO
mDDz+kc4Hnn2vBPLHFsYwBNlLrLa5AV3T7LlC8pJtUjH8FtGqQ1YLSi5fvq9SV7E
a9B7c0hRq7x2N4BLe8Z1a1v3XqAZx5h8k6GbzY8OB9oGJW0kEsw4yCKsJo6FZTrv
4cOEp8m6ykTk7xd3fGk2Y3tUeNe8JoB6tBKP4KcYGQJkO5jW5hcJnxoD4eJtXqLi
wL9dL6UX1SeL4Qk6sKOzE5RFp8VNJtUl5jM7y9xPV4cQ1pAQKhJtbK5GYJFDfB
QIDAQAB
-----END PUBLIC KEY-----"""
        
        try:
            self.public_key = serialization.load_pem_public_key(public_key_pem.encode())
        except Exception as e:
            self.logger.error(f"Failed to load public key: {e}")
            raise
    
    def _load_license(self) -> None:
        """Load the license file if it exists."""
        try:
            if not self.license_file.exists():
                self.logger.info("No license file found, running in trial mode")
                return
            
            with open(self.license_file, 'r') as f:
                license_data = json.load(f)
            
            # Verify license signature
            if not self._verify_license_signature(license_data):
                self.logger.warning("Invalid license signature detected")
                return
            
            self.current_license = license_data
            self.logger.info("License loaded successfully", extra={
                'type': license_data.get('type'),
                'expiry': license_data.get('expiry'),
                'machineId': license_data.get('machineId')
            })
            
            # Notify about license status change
            self.license_status_changed.emit(self.get_license_info())
            
        except Exception as e:
            self.logger.info(f"No valid license file found, running in trial mode: {e}")
    
    def _save_license(self, license_data: dict) -> None:
        """Save license data to file."""
        try:
            with open(self.license_file, 'w') as f:
                json.dump(license_data, f, indent=2)
            self.license_file.chmod(0o600)  # Restrict permissions
            self.logger.info("License saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save license: {e}")
            raise
    
    def activate_license(self, license_key: str) -> dict:
        """
        Activate a license with the given key.
        
        Args:
            license_key: The license key to activate
            
        Returns:
            dict: {
                'success': bool,
                'license': dict (if successful),
                'error': str (if failed)
            }
        """
        try:
            # Validate license key format
            if not self._validate_license_key_format(license_key):
                raise ValueError("Invalid license key format")
            
            # Contact license server for activation
            activation_data = self._contact_license_server('activate', {
                'licenseKey': license_key,
                'machineId': self.machine_id,
                'appVersion': self.app.get_version(),
                'platform': os.name,
                'arch': os.uname().machine
            })
            
            # Verify the received license
            if not self._verify_license_signature(activation_data):
                raise ValueError("Received invalid license from server")
            
            # Save and load the new license
            self._save_license(activation_data)
            self.current_license = activation_data
            
            self.logger.info("License activated successfully", extra={
                'type': activation_data.get('type'),
                'expiry': activation_data.get('expiry')
            })
            
            # Notify about license status change
            self.license_status_changed.emit(self.get_license_info())
            
            return {
                'success': True,
                'license': self.get_license_info()
            }
            
        except Exception as e:
            self.logger.error(f"License activation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_license(self) -> bool:
        """Verify the current license is valid."""
        try:
            if not self.current_license:
                return False
            
            # Check basic validity
            if not self._is_license_valid():
                return False
            
            # Periodic server validation (every 24 hours)
            last_validation = self.current_license.get('lastValidation', 0)
            now = datetime.utcnow().timestamp() * 1000  # JS timestamp in ms
            validation_interval = 24 * 60 * 60 * 1000  # 24 hours
            
            if now - last_validation > validation_interval:
                server_valid = self._validate_with_server()
                if server_valid:
                    self.current_license['lastValidation'] = now
                    self._save_license(self.current_license)
                else:
                    self.logger.warning("Server validation failed for license")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"License verification error: {e}")
            return False
    
    def _is_license_valid(self) -> bool:
        """Check if the current license is valid."""
        if not self.current_license:
            return False
        
        # Check expiry
        expiry = self.current_license.get('expiry')
        if expiry != 'never' and datetime.utcnow() > datetime.fromisoformat(expiry):
            self.logger.info("License has expired")
            return False
        
        # Check machine ID (hardware fingerprint)
        if self.current_license.get('machineId') != self.machine_id:
            self.logger.warning("License machine ID mismatch")
            return False
        
        # Check license type
        if not self.license_types.get(self.current_license.get('type')):
            self.logger.warning(f"Unknown license type: {self.current_license.get('type')}")
            return False
        
        return True
    
    def _verify_license_signature(self, license_data: dict) -> bool:
        """Verify the signature of license data."""
        try:
            if not license_data.get('signature') or not self.public_key:
                return False
            
            # Create data string for verification (excluding signature)
            data_to_verify = {k: v for k, v in license_data.items() if k != 'signature'}
            data_str = json.dumps(data_to_verify, sort_keys=True)
            
            # Verify signature
            self.public_key.verify(
                license_data['signature'].encode(),
                data_str.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Signature verification error: {e}")
            return False
    
    def _validate_license_key_format(self, license_key: str) -> bool:
        """Validate the format of a license key."""
        # Expected format: MARKA-XXXXX-XXXXX-XXXXX-XXXXX
        pattern = r'^MARKA-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$'
        return bool(re.match(pattern, license_key))
    
    def _contact_license_server(self, action: str, data: dict) -> dict:
        """
        Contact the license server with the given action and data.
        
        Args:
            action: The action to perform (activate, validate, etc.)
            data: The data to send
            
        Returns:
            dict: The response from the server
            
        Raises:
            Exception: If the request fails
        """
        try:
            response = requests.post(
                f"{self.api_endpoint}/{action}",
                json=data,
                timeout=30,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': f"Marka/{self.app.get_version()} ({os.name})"
                }
            )
            
            if response.status_code == 200 and response.json().get('success'):
                return response.json().get('license', response.json())
            else:
                error = response.json().get('error', 'Server request failed')
                raise Exception(error)
                
        except requests.exceptions.RequestException as e:
            if e.response:
                error = e.response.json().get('error', 'Server error')
                raise Exception(error)
            elif e.request:
                raise Exception("Unable to contact license server. Please check your internet connection.")
            else:
                raise e
    
    def _validate_with_server(self) -> bool:
        """Validate the current license with the server."""
        try:
            response = self._contact_license_server('validate', {
                'licenseId': self.current_license['id'],
                'machineId': self.machine_id,
                'checksum': self._calculate_license_checksum()
            })
            
            return response.get('valid', False)
            
        except Exception as e:
            self.logger.warning(f"Server validation failed: {e}")
            # Return True for offline validation if server is unreachable
            return "contact license server" in str(e).lower()
    
    def _calculate_license_checksum(self) -> str:
        """Calculate a checksum of the current license data."""
        if not self.current_license:
            return ""
            
        data = {
            'id': self.current_license.get('id'),
            'type': self.current_license.get('type'),
            'machineId': self.current_license.get('machineId'),
            'expiry': self.current_license.get('expiry')
        }
        
        return hashlib.sha256(json.dumps(data).encode()).hexdigest()
    
    def get_license_info(self) -> dict:
        """Get information about the current license."""
        if not self.current_license:
            return {
                'type': 'TRIAL',
                'status': 'trial',
                'features': ['basic_reporting', 'student_management'],
                'limits': {'students': 50, 'custom_templates': 1, 'cloud_sync': False},
                'expiry': None,
                'daysRemaining': None,
                'isValid': False
            }
        
        license_type = self.license_types.get(self.current_license.get('type', {}))
        now = datetime.utcnow()
        expiry = None if self.current_license.get('expiry') == 'never' else datetime.fromisoformat(self.current_license['expiry'])
        
        days_remaining = None
        if expiry:
            days_remaining = max(0, (expiry - now).days)
        
        return {
            'type': self.current_license.get('type'),
            'name': license_type.get('name'),
            'status': 'active' if self._is_license_valid() else 'invalid',
            'features': license_type.get('features', []),
            'limits': license_type.get('limits', {}),
            'expiry': self.current_license.get('expiry'),
            'daysRemaining': days_remaining,
            'isValid': self._is_license_valid(),
            'machineId': self.current_license.get('machineId'),
            'activationDate': self.current_license.get('activationDate'),
            'lastValidation': self.current_license.get('lastValidation')
        }
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if the current license has a specific feature."""
        license_info = self.get_license_info()
        return feature_name in license_info.get('features', [])
    
    def check_limit(self, limit_name: str, current_value: int) -> dict:
        """
        Check if current usage is within the specified limit.
        
        Returns:
            dict: {
                'allowed': bool,
                'remaining': int (-1 for unlimited),
                'limit': int
            }
        """
        license_info = self.get_license_info()
        limit = license_info['limits'].get(limit_name, 0)
        
        if limit == -1:
            return {'allowed': True, 'remaining': -1, 'limit': -1}
        
        return {
            'allowed': current_value < limit,
            'remaining': max(0, limit - current_value),
            'limit': limit
        }
    
    def deactivate_license(self) -> dict:
        """Deactivate the current license."""
        try:
            if self.current_license:
                # Notify server about deactivation
                self._contact_license_server('deactivate', {
                    'licenseId': self.current_license['id'],
                    'machineId': self.machine_id
                })
            
            # Remove local license file
            try:
                self.license_file.unlink()
            except:
                pass
            
            self.current_license = None
            self.logger.info("License deactivated successfully")
            
            # Notify about license status change
            self.license_status_changed.emit(self.get_license_info())
            
            return {'success': True}
            
        except Exception as e:
            self.logger.error(f"License deactivation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def transfer_license(self, new_machine_id: str) -> dict:
        """Transfer the license to a new machine."""
        try:
            if not self.current_license:
                raise ValueError("No active license to transfer")
            
            response = self._contact_license_server('transfer', {
                'licenseId': self.current_license['id'],
                'oldMachineId': self.machine_id,
                'newMachineId': new_machine_id
            })
            
            self.logger.info("License transfer initiated")
            return {'success': True, 'transferId': response.get('transferId')}
            
        except Exception as e:
            self.logger.error(f"License transfer failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def renew_license(self) -> dict:
        """Renew the current license."""
        try:
            if not self.current_license:
                raise ValueError("No license to renew")
            
            response = self._contact_license_server('renew', {
                'licenseId': self.current_license['id'],
                'machineId': self.machine_id
            })
            
            # Update license with new expiry
            self.current_license['expiry'] = response['newExpiry']
            self.current_license['lastValidation'] = datetime.utcnow().timestamp() * 1000
            self._save_license(self.current_license)
            
            self.logger.info("License renewed successfully", extra={
                'newExpiry': response['newExpiry']
            })
            
            # Notify about license status change
            self.license_status_changed.emit(self.get_license_info())
            
            return {'success': True, 'newExpiry': response['newExpiry']}
            
        except Exception as e:
            self.logger.error(f"License renewal failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _start_periodic_validation(self) -> None:
        """Start periodic license validation."""
        self.validation_timer = QTimer()
        self.validation_timer.timeout.connect(self._periodic_validation)
        self.validation_timer.start(60 * 60 * 1000)  # Every hour
    
    def _periodic_validation(self) -> None:
        """Periodic license validation check."""
        try:
            is_valid = self.verify_license()
            if not is_valid and self.current_license:
                self.logger.warning("License validation failed during periodic check")
                # Notify about license status change
                self.license_status_changed.emit(self.get_license_info())
        except Exception as e:
            self.logger.error(f"Periodic license validation error: {e}")
    
    def cleanup(self) -> None:
        """Clean up the license manager."""
        if hasattr(self, 'validation_timer'):
            self.validation_timer.stop()
        
        self.current_license = None
        self.logger.info("LicenseManager cleanup completed")