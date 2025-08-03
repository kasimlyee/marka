import os
import csv
import json
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime
from io import BytesIO, StringIO
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import hashlib
import pandas as pd
from PyPDF2 import PdfWriter, PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from PySide6.QtCore import QStandardPaths
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

class FileManager:
    """Handles file operations including import/export, encryption, and compression."""
    
    def __init__(self, options: Optional[Dict] = None):
        """
        Initialize FileManager with configuration options.
        
        Args:
            options: Dictionary of configuration options including:
                - upload_dir: Directory for uploads
                - max_file_size: Maximum allowed file size in bytes
                - allowed_extensions: List of allowed file extensions
                - encryption_key: Key for file encryption
        """
        self.options = {
            'upload_dir': Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'uploads',
            'max_file_size': 50 * 1024 * 1024,  # 50MB
            'allowed_extensions': ['.csv', '.xlsx', '.xls', '.pdf', '.jpg', '.png'],
            'encryption_key': os.getenv('FILE_ENCRYPTION_KEY', 'default-file-key').encode(),
            **(options or {})
        }
        
        # Ensure encryption key is 32 bytes
        self.encryption_key = hashlib.sha256(self.options['encryption_key']).digest()
        self.fernet = Fernet(Fernet.generate_key())  # Not using the key directly
        
        # Thread safety
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize directories
        self.ensure_directories()
        self.logger = logging.getLogger('marka.file_manager')
        
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        try:
            self.options['upload_dir'].mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f'Failed to create upload directory: {str(e)}')
            raise

    async def import_students(self, file_path: Union[str, Path], format: Optional[str] = None) -> List[Dict]:
        """
        Import student data from a file.
        
        Args:
            file_path: Path to the import file
            format: File format (csv, excel), auto-detected if None
            
        Returns:
            List of dictionaries containing student data
        """
        with self.lock:
            try:
                file_path = Path(file_path)
                await self.validate_file(file_path)
                
                # Determine format if not provided
                file_format = format or self.detect_file_format(file_path)
                
                if file_format == 'csv':
                    return await self.import_csv(file_path)
                elif file_format == 'excel':
                    return await self.import_excel(file_path)
                else:
                    raise ValueError(f'Unsupported file format: {file_format}')
                
            except Exception as e:
                self.logger.error(f'Failed to import students: {str(e)}')
                raise

    async def export_students(self, 
                            output_path: Union[str, Path], 
                            data: List[Dict], 
                            format: str = 'csv') -> Path:
        """
        Export student data to a file.
        
        Args:
            output_path: Path to save the exported file
            data: List of student data dictionaries
            format: Export format (csv, xlsx, pdf, zip)
            
        Returns:
            Path to the exported file
        """
        with self.lock:
            try:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                if format.lower() == 'csv':
                    return await self.export_csv(output_path, data)
                elif format.lower() == 'xlsx':
                    return await self.export_excel(output_path, data)
                elif format.lower() == 'pdf':
                    return await self.export_pdf(output_path, data)
                elif format.lower() == 'zip':
                    return await self.export_zip(output_path, data)
                else:
                    raise ValueError(f'Unsupported export format: {format}')
                
            except Exception as e:
                self.logger.error(f'Failed to export students: {str(e)}')
                raise

    async def import_csv(self, file_path: Path) -> List[Dict]:
        """Import data from CSV file."""
        try:
            # Using pandas for robust CSV handling
            df = pd.read_csv(file_path, dtype=str)
            data = df.where(pd.notnull(df), None).to_dict('records')
            self.logger.info(f'Imported {len(data)} records from CSV: {file_path}')
            return data
        except Exception as e:
            self.logger.error(f'CSV import failed: {str(e)}')
            raise

    async def import_excel(self, file_path: Path) -> List[Dict]:
        """Import data from Excel file."""
        try:
            # Using pandas for Excel import
            df = pd.read_excel(file_path, dtype=str)
            data = df.where(pd.notnull(df), None).to_dict('records')
            self.logger.info(f'Imported {len(data)} records from Excel: {file_path}')
            return data
        except Exception as e:
            self.logger.error(f'Excel import failed: {str(e)}')
            raise

    async def export_csv(self, output_path: Path, data: List[Dict]) -> Path:
        """Export data to CSV file."""
        try:
            if not data:
                raise ValueError('No data to export')
                
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False)
            self.logger.info(f'Exported {len(data)} records to CSV: {output_path}')
            return output_path
        except Exception as e:
            self.logger.error(f'CSV export failed: {str(e)}')
            raise

    async def export_excel(self, output_path: Path, data: List[Dict]) -> Path:
        """Export data to Excel file."""
        try:
            if not data:
                raise ValueError('No data to export')
                
            df = pd.DataFrame(data)
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Students')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Students']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2) * 1.2
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                    
            self.logger.info(f'Exported {len(data)} records to Excel: {output_path}')
            return output_path
        except Exception as e:
            self.logger.error(f'Excel export failed: {str(e)}')
            raise

    async def export_pdf(self, output_path: Path, data: List[Dict]) -> Path:
        """Export data to PDF file."""
        try:
            if not data:
                raise ValueError('No data to export')
                
            doc = SimpleDocTemplate(str(output_path), pagesize=letter)
            elements = []
            
            # Title
            styles = getSampleStyleSheet()
            elements.append(Paragraph("Student Records", styles['Title']))
            
            # Prepare table data
            headers = list(data[0].keys())
            table_data = [headers]
            
            for item in data:
                row = [str(item.get(header, '')) for header in headers]
                table_data.append(row)
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            doc.build(elements)
            
            self.logger.info(f'Exported {len(data)} records to PDF: {output_path}')
            return output_path
        except Exception as e:
            self.logger.error(f'PDF export failed: {str(e)}')
            raise

    async def export_zip(self, output_path: Path, data: List[Dict]) -> Path:
        """Export data to ZIP archive containing multiple formats."""
        try:
            if not data:
                raise ValueError('No data to export')
                
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add CSV
                csv_buffer = StringIO()
                pd.DataFrame(data).to_csv(csv_buffer, index=False)
                zipf.writestr('students.csv', csv_buffer.getvalue())
                
                # Add JSON
                json_buffer = StringIO()
                json.dump(data, json_buffer, indent=2)
                zipf.writestr('students.json', json_buffer.getvalue())
                
                # Add PDF
                pdf_buffer = BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
                elements = self._create_pdf_elements(data)
                doc.build(elements)
                zipf.writestr('students.pdf', pdf_buffer.getvalue())
                
            self.logger.info(f'Exported {len(data)} records to ZIP: {output_path}')
            return output_path
        except Exception as e:
            self.logger.error(f'ZIP export failed: {str(e)}')
            raise

    def _create_pdf_elements(self, data: List[Dict]):
        """Helper to create PDF elements for export."""
        styles = getSampleStyleSheet()
        elements = [Paragraph("Student Records", styles['Title'])]
        
        if data:
            headers = list(data[0].keys())
            table_data = [headers]
            
            for item in data:
                row = [str(item.get(header, '')) for header in headers]
                table_data.append(row)
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            
        return elements

    async def validate_file(self, file_path: Path) -> None:
        """Validate file before processing."""
        if not file_path.exists():
            raise FileNotFoundError(f'File does not exist: {file_path}')
            
        file_size = file_path.stat().st_size
        if file_size > self.options['max_file_size']:
            raise ValueError(f'File size {file_size} exceeds limit of {self.options["max_file_size"]}')
            
        ext = file_path.suffix.lower()
        if ext not in self.options['allowed_extensions']:
            raise ValueError(f'File type {ext} is not allowed')

    def detect_file_format(self, file_path: Path) -> str:
        """Detect file format from extension."""
        ext = file_path.suffix.lower()
        if ext == '.csv':
            return 'csv'
        elif ext in ('.xlsx', '.xls'):
            return 'excel'
        else:
            raise ValueError(f'Cannot detect format for file extension {ext}')

    async def create_zip_archive(self, output_path: Path, files: List[Dict[str, str]]) -> Path:
        """
        Create a ZIP archive containing multiple files.
        
        Args:
            output_path: Path to output ZIP file
            files: List of dictionaries with 'path' and 'name' keys
            
        Returns:
            Path to created ZIP file
        """
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_info in files:
                    zipf.write(file_info['path'], arcname=file_info['name'])
                    
            self.logger.info(f'Created ZIP archive with {len(files)} files: {output_path}')
            return output_path
        except Exception as e:
            self.logger.error(f'Failed to create ZIP archive: {str(e)}')
            raise

    async def extract_zip_archive(self, zip_path: Path, extract_dir: Path) -> List[Path]:
        """
        Extract a ZIP archive to a directory.
        
        Args:
            zip_path: Path to ZIP file
            extract_dir: Directory to extract to
            
        Returns:
            List of paths to extracted files
        """
        try:
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(extract_dir)
                extracted_files = zipf.namelist()
                
            self.logger.info(f'Extracted {len(extracted_files)} files from {zip_path}')
            return [extract_dir / f for f in extracted_files]
        except Exception as e:
            self.logger.error(f'Failed to extract ZIP archive: {str(e)}')
            raise

    async def encrypt_file(self, input_path: Path, output_path: Path) -> Path:
        """
        Encrypt a file using AES-256.
        
        Args:
            input_path: Path to input file
            output_path: Path to output encrypted file
            
        Returns:
            Path to encrypted file
        """
        try:
            # Generate a random IV
            iv = os.urandom(16)
            
            # Create cipher object
            cipher = Cipher(
                algorithms.AES(self.encryption_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Create padder for PKCS7 padding
            padder = padding.PKCS7(128).padder()
            
            with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                # Write IV first
                outfile.write(iv)
                
                # Encrypt in chunks
                while True:
                    chunk = infile.read(64 * 1024)  # 64KB chunks
                    if not chunk:
                        break
                        
                    padded_data = padder.update(chunk)
                    encrypted_chunk = encryptor.update(padded_data)
                    outfile.write(encrypted_chunk)
                
                # Finalize
                final_padded = padder.finalize()
                outfile.write(encryptor.update(final_padded))
                outfile.write(encryptor.finalize())
                
            self.logger.info(f'Encrypted file saved to: {output_path}')
            return output_path
        except Exception as e:
            self.logger.error(f'File encryption failed: {str(e)}')
            raise

    async def decrypt_file(self, input_path: Path, output_path: Path) -> Path:
        """
        Decrypt a file encrypted with AES-256.
        
        Args:
            input_path: Path to encrypted file
            output_path: Path to decrypted file
            
        Returns:
            Path to decrypted file
        """
        try:
            with open(input_path, 'rb') as infile:
                # Read IV from first 16 bytes
                iv = infile.read(16)
                
                # Create cipher object
                cipher = Cipher(
                    algorithms.AES(self.encryption_key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                
                # Create unpadder for PKCS7 padding
                unpadder = padding.PKCS7(128).unpadder()
                
                with open(output_path, 'wb') as outfile:
                    # Decrypt in chunks
                    while True:
                        chunk = infile.read(64 * 1024)  # 64KB chunks
                        if not chunk:
                            break
                            
                        decrypted_chunk = decryptor.update(chunk)
                        unpadded_data = unpadder.update(decrypted_chunk)
                        outfile.write(unpadded_data)
                    
                    # Finalize
                    final_unpadded = unpadder.finalize()
                    outfile.write(final_unpadded)
                    outfile.write(decryptor.finalize())
                    
            self.logger.info(f'Decrypted file saved to: {output_path}')
            return output_path
        except Exception as e:
            self.logger.error(f'File decryption failed: {str(e)}')
            raise

    async def get_file_info(self, file_path: Path) -> Dict:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing:
                - size: File size in bytes
                - mtime: Last modification time
                - type: File extension
        """
        try:
            stat = file_path.stat()
            return {
                'size': stat.st_size,
                'mtime': datetime.fromtimestamp(stat.st_mtime),
                'type': file_path.suffix.lower().lstrip('.')
            }
        except Exception as e:
            self.logger.error(f'Failed to get file info: {str(e)}')
            raise

    def cleanup(self) -> None:
        """Clean up resources."""
        self.executor.shutdown(wait=True)
        self.logger.info('FileManager cleanup completed')