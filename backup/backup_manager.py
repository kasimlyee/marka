import os
import json
import logging
import hashlib
import zlib
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from PySide6.QtCore import QObject, Signal
from cryptography.fernet import Fernet
from google.cloud import storage
import boto3

class BackupManager(QObject):
    """
    Manages database backups including local and cloud storage, encryption, and compression.
    """
    
    backup_progress = Signal(str, int)  # (message, progress)
    backup_complete = Signal(str, bool)  # (backup_path, success)
    
    def __init__(self, database_manager, app_data_dir: str, options: Optional[dict] = None):
        super().__init__()
        self.logger = logging.getLogger('marka.backup')
        self.database_manager = database_manager
        self.app_data_dir = Path(app_data_dir)
        
        # Configuration options
        self.options = {
            'encryption_key': os.getenv('BACKUP_ENCRYPTION_KEY', 'default-encryption-key'),
            'backup_dir': str(self.app_data_dir / 'backups'),
            'retention_days': 30,
            'max_backups': 10,
            'cloud_providers': [],
            **(options or {})
        }
        
        # Initialize cloud clients
        self.cloud_clients = self._initialize_cloud_clients()
        
        # Ensure backup directory exists
        self._ensure_backup_dir()
    
    def _initialize_cloud_clients(self) -> dict:
        """Initialize cloud storage clients based on configuration."""
        clients = {}
        
        if 'gcp' in self.options['cloud_providers'] and os.getenv('GCP_PROJECT_ID'):
            clients['gcp'] = storage.Client(
                project=os.getenv('GCP_PROJECT_ID'),
                credentials=os.getenv('GCP_KEY_FILE')
            )
        
        if 'aws' in self.options['cloud_providers'] and os.getenv('AWS_ACCESS_KEY_ID'):
            clients['aws'] = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_REGION')
            )
        
        return clients
    
    def _ensure_backup_dir(self) -> None:
        """Ensure the backup directory exists."""
        try:
            os.makedirs(self.options['backup_dir'], exist_ok=True, mode=0o700)
        except Exception as e:
            self.logger.error(f"Failed to create backup directory: {e}")
            raise
    
    async def create_backup(self, options: Optional[dict] = None) -> str:
        """
        Create a backup of the database.
        
        Args:
            options: {
                'encrypt': bool (default True),
                'compress': bool (default True),
                'automatic': bool (default False)
            }
            
        Returns:
            str: Path to the created backup file
        """
        opts = {
            'encrypt': True,
            'compress': True,
            'automatic': False,
            **(options or {})
        }
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_name = f"marka-backup-{timestamp}{'-auto' if opts['automatic'] else ''}.marka"
        backup_path = str(Path(self.options['backup_dir'])) / backup_name
        temp_path = f"{backup_path}.tmp"
        
        try:
            self.backup_progress.emit("Starting backup...", 0)
            self.logger.info(f"Creating backup at {backup_path}", extra={'options': opts})
            
            # Step 1: Create temporary backup
            self.backup_progress.emit("Creating temporary backup...", 10)
            await self._create_temp_backup(temp_path)
            
            # Step 2: Process the backup (compress and/or encrypt)
            self.backup_progress.emit("Processing backup...", 30)
            await self._process_backup(temp_path, backup_path, opts)
            
            # Step 3: Clean up temporary file
            self.backup_progress.emit("Cleaning up...", 70)
            try:
                os.unlink(temp_path)
            except:
                pass
            
            # Step 4: Upload to cloud if configured
            self.backup_progress.emit("Uploading to cloud...", 80)
            await self._upload_to_cloud(backup_path, backup_name)
            
            # Step 5: Record backup in database
            self.backup_progress.emit("Recording backup...", 90)
            await self.database_manager.create_backup_info(
                backup_path, 
                'automatic' if opts['automatic'] else 'manual'
            )
            
            # Step 6: Apply retention policy
            self.backup_progress.emit("Applying retention policy...", 95)
            await self._apply_retention_policy()
            
            self.backup_progress.emit("Backup complete", 100)
            self.backup_complete.emit(backup_path, True)
            self.logger.info("Backup created successfully")
            return backup_path
            
        except Exception as e:
            self.logger.error("Backup creation failed:", exc_info=True)
            self.backup_complete.emit(backup_path, False)
            
            # Clean up any partial files
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass
            
            raise
    
    async def _create_temp_backup(self, temp_path: str) -> None:
        """Create a temporary backup file (tarball of the database)."""
        try:
            with tarfile.open(temp_path, 'w') as tar:
                tar.add(self.database_manager.db_path, arcname=os.path.basename(self.database_manager.db_path))
        except Exception as e:
            self.logger.error("Failed to create temporary backup:", exc_info=True)
            raise ValueError("Failed to create database tarball") from e
    
    async def _process_backup(self, source_path: str, dest_path: str, options: dict) -> None:
        """Process the backup file with compression and/or encryption."""
        try:
            # Read the source file
            with open(source_path, 'rb') as src_file:
                data = src_file.read()
            
            # Apply compression if requested
            if options['compress']:
                data = zlib.compress(data)
            
            # Apply encryption if requested
            if options['encrypt']:
                f = Fernet(self.options['encryption_key'].encode())
                data = f.encrypt(data)
            
            # Write the processed data
            with open(dest_path, 'wb') as dest_file:
                dest_file.write(data)
                
        except Exception as e:
            self.logger.error("Backup processing failed:", exc_info=True)
            raise ValueError("Failed to process backup file") from e
    
    async def _upload_to_cloud(self, backup_path: str, backup_name: str) -> None:
        """Upload the backup to configured cloud providers."""
        upload_tasks = []
        
        # Upload to GCP if configured
        if 'gcp' in self.cloud_clients and os.getenv('GCP_BUCKET_NAME'):
            try:
                bucket = self.cloud_clients['gcp'].bucket(os.getenv('GCP_BUCKET_NAME'))
                blob = bucket.blob(f"backups/{backup_name}")
                upload_tasks.append(blob.upload_from_filename(backup_path))
            except Exception as e:
                self.logger.error("GCP upload failed:", exc_info=True)
                raise
        
        # Upload to AWS if configured
        if 'aws' in self.cloud_clients and os.getenv('AWS_BUCKET_NAME'):
            try:
                with open(backup_path, 'rb') as data:
                    upload_tasks.append(
                        self.cloud_clients['aws'].upload_fileobj(
                            data,
                            os.getenv('AWS_BUCKET_NAME'),
                            f"backups/{backup_name}",
                            ExtraArgs={
                                'ContentType': 'application/octet-stream',
                                'Metadata': {
                                    'source': 'marka-desktop',
                                    'timestamp': datetime.utcnow().isoformat()
                                }
                            }
                        )
                    )
            except Exception as e:
                self.logger.error("AWS upload failed:", exc_info=True)
                raise
        
        # Wait for all uploads to complete
        if upload_tasks:
            await asyncio.gather(*upload_tasks)
            self.logger.info("Cloud backup uploads completed")
    
    async def _apply_retention_policy(self) -> None:
        """Apply backup retention policy (max backups and age)."""
        try:
            backup_files = []
            
            # List all backup files
            for file in os.listdir(self.options['backup_dir']):
                if file.endswith('.marka'):
                    file_path = os.path.join(self.options['backup_dir'], file)
                    stat = os.stat(file_path)
                    backup_files.append({
                        'name': file,
                        'path': file_path,
                        'time': stat.st_mtime
                    })
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x['time'], reverse=True)
            
            # Delete files beyond max_backups count
            if len(backup_files) > self.options['max_backups']:
                for file in backup_files[self.options['max_backups']:]:
                    try:
                        os.unlink(file['path'])
                        self.logger.info(f"Deleted old backup: {file['name']}")
                    except Exception as e:
                        self.logger.error(f"Failed to delete old backup {file['name']}:", exc_info=True)
            
            # Delete files older than retention_days
            cutoff_time = (datetime.now() - timedelta(days=self.options['retention_days'])).timestamp()
            for file in backup_files:
                if file['time'] < cutoff_time:
                    try:
                        os.unlink(file['path'])
                        self.logger.info(f"Deleted expired backup: {file['name']}")
                    except Exception as e:
                        self.logger.error(f"Failed to delete expired backup {file['name']}:", exc_info=True)
                        
        except Exception as e:
            self.logger.error("Failed to apply retention policy:", exc_info=True)
            raise
    
    async def restore_backup(self, backup_path: str) -> None:
        """
        Restore the database from a backup file.
        
        Args:
            backup_path: Path to the backup file to restore from
        """
        try:
            self.backup_progress.emit("Starting restore...", 0)
            self.logger.info(f"Starting restore from backup: {backup_path}")
            
            # Step 1: Verify backup file
            self.backup_progress.emit("Verifying backup...", 10)
            await self._verify_backup_file(backup_path)
            
            # Step 2: Create restore directory
            self.backup_progress.emit("Preparing restore...", 20)
            restore_dir = os.path.join(self.options['backup_dir'], 'restore')
            os.makedirs(restore_dir, exist_ok=True)
            
            # Step 3: Process the backup file
            self.backup_progress.emit("Processing backup...", 40)
            extracted_path = await self._process_restore(backup_path, restore_dir)
            
            # Step 4: Verify the extracted database
            self.backup_progress.emit("Verifying database...", 70)
            await self._verify_database_file(extracted_path)
            
            # Step 5: Replace current database
            self.backup_progress.emit("Replacing database...", 90)
            await self._replace_database(extracted_path)
            
            # Step 6: Clean up
            self.backup_progress.emit("Cleaning up...", 95)
            try:
                import shutil
                shutil.rmtree(restore_dir)
            except:
                pass
            
            self.backup_progress.emit("Restore complete", 100)
            self.logger.info("Database restore completed successfully")
            
        except Exception as e:
            self.logger.error("Restore failed:", exc_info=True)
            raise
    
    async def _verify_backup_file(self, backup_path: str) -> None:
        """Verify the backup file is valid."""
        try:
            if os.path.getsize(backup_path) == 0:
                raise ValueError("Backup file is empty")
        except Exception as e:
            self.logger.error("Backup file verification failed:", exc_info=True)
            raise ValueError("Invalid backup file") from e
    
    async def _process_restore(self, backup_path: str, restore_dir: str) -> str:
        """Process the backup file for restoration (decrypt and decompress)."""
        try:
            # Read the backup file
            with open(backup_path, 'rb') as f:
                data = f.read()
            
            # Check if file is encrypted by trying to decrypt
            is_encrypted = True
            try:
                f = Fernet(self.options['encryption_key'].encode())
                decrypted_data = f.decrypt(data)
                data = decrypted_data
            except:
                is_encrypted = False
            
            # Decompress if needed
            try:
                data = zlib.decompress(data)
            except:
                pass  # Not compressed
            
            # Extract the tarball
            temp_tar = os.path.join(restore_dir, 'temp.tar')
            with open(temp_tar, 'wb') as f:
                f.write(data)
            
            with tarfile.open(temp_tar, 'r') as tar:
                tar.extractall(path=restore_dir)
            
            os.unlink(temp_tar)
            
            return os.path.join(restore_dir, os.path.basename(self.database_manager.db_path))
            
        except Exception as e:
            self.logger.error("Backup processing failed during restore:", exc_info=True)
            raise ValueError("Failed to process backup file for restore") from e
    
    async def _verify_database_file(self, db_path: str) -> None:
        """Verify the integrity of the database file."""
        try:
            # Quick integrity check
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] != 'ok':
                raise ValueError("Database integrity check failed")
                
        except Exception as e:
            self.logger.error("Database verification failed:", exc_info=True)
            raise ValueError("Invalid database file in backup") from e
    
    async def _replace_database(self, new_db_path: str) -> None:
        """Replace the current database with the restored one."""
        try:
            # Close existing database connections
            await self.database_manager.close()
            
            # Backup current database in case restore fails
            backup_current_path = f"{self.database_manager.db_path}.pre-restore"
            import shutil
            shutil.copy2(self.database_manager.db_path, backup_current_path)
            
            try:
                # Replace the database file
                shutil.copy2(new_db_path, self.database_manager.db_path)
                
                # Reinitialize the database
                await self.database_manager.initialize()
            except Exception as e:
                # Restore original database if replacement failed
                self.logger.error("Restore failed, reverting to original database:", exc_info=True)
                shutil.copy2(backup_current_path, self.database_manager.db_path)
                await self.database_manager.initialize()
                raise
            finally:
                # Clean up the backup
                try:
                    os.unlink(backup_current_path)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error("Database replacement failed:", exc_info=True)
            raise ValueError("Failed to replace database file") from e
    
    async def list_backups(self) -> List[dict]:
        """
        List available backups.
        
        Returns:
            List[dict]: {
                'name': str,
                'path': str,
                'size': int,
                'modified': datetime
            }
        """
        try:
            backups = []
            
            for file in os.listdir(self.options['backup_dir']):
                if file.endswith('.marka'):
                    file_path = os.path.join(self.options['backup_dir'], file)
                    stat = os.stat(file_path)
                    backups.append({
                        'name': file,
                        'path': file_path,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    })
            
            return sorted(backups, key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            self.logger.error("Failed to list backups:", exc_info=True)
            raise
    
    async def download_from_cloud(self, backup_name: str, provider: str) -> str:
        """
        Download a backup from cloud storage.
        
        Args:
            backup_name: Name of the backup to download
            provider: Cloud provider ('aws' or 'gcp')
            
        Returns:
            str: Path to the downloaded backup file
        """
        if provider not in self.cloud_clients:
            raise ValueError(f"Cloud provider {provider} not configured")
        
        dest_path = os.path.join(self.options['backup_dir'], backup_name)
        
        try:
            if provider == 'gcp':
                bucket = self.cloud_clients['gcp'].bucket(os.getenv('GCP_BUCKET_NAME'))
                blob = bucket.blob(f"backups/{backup_name}")
                blob.download_to_filename(dest_path)
            elif provider == 'aws':
                with open(dest_path, 'wb') as f:
                    self.cloud_clients['aws'].download_fileobj(
                        os.getenv('AWS_BUCKET_NAME'),
                        f"backups/{backup_name}",
                        f
                    )
            
            return dest_path
            
        except Exception as e:
            self.logger.error(f"Failed to download backup from {provider}:", exc_info=True)
            raise