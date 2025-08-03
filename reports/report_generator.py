import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
import qrcode
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PySide6.QtCore import QStandardPaths
from PIL import Image as PILImage
import bcrypt
from cryptography.fernet import Fernet
import hashlib

class ReportGenerator:
    """
    A robust report generator for the Marka report card system.
    Handles all report generation operations including PDF creation, templates,
    and bulk report generation.
    """
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.output_dir = None
        self.template_cache = {}
        self.fonts = {}
        self.colors = {
            'primary': colors.HexColor('#1D3557'),
            'secondary': colors.HexColor('#2A9D8F'),
            'accent': colors.HexColor('#F4A261'),
            'success': colors.HexColor('#10B981'),
            'warning': colors.HexColor('#F59E0B'),
            'error': colors.HexColor('#E63946'),
            'text': colors.HexColor('#374151'),
            'text_light': colors.HexColor('#6B7280'),
            'background': colors.HexColor('#F9FAFB')
        }
        self.logger = logging.getLogger('marka.report_generator')
        self.initialize()

    def initialize(self):
        """Initialize the report generator."""
        try:
            # Set output directory
            data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            self.output_dir = Path(data_dir) / 'reports'
            os.makedirs(self.output_dir, exist_ok=True)

            # Load fonts
            self.load_fonts()

            # Load default templates
            self.load_templates()

            self.logger.info('ReportGenerator initialized successfully')
        except Exception as e:
            self.logger.error(f'Failed to initialize ReportGenerator: {str(e)}')
            raise

    def load_fonts(self):
        """Load fonts for PDF generation."""
        try:
            # Register default fonts
            pdfmetrics.registerFont(TTFont('Roboto', 'Roboto-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('Roboto-Bold', 'Roboto-Bold.ttf'))
            pdfmetrics.registerFont(TTFont('Roboto-Italic', 'Roboto-Italic.ttf'))
            pdfmetrics.registerFont(TTFont('Roboto-Light', 'Roboto-Light.ttf'))
            
            self.fonts = {
                'regular': 'Roboto',
                'bold': 'Roboto-Bold',
                'italic': 'Roboto-Italic',
                'light': 'Roboto-Light'
            }
        except Exception as e:
            self.logger.warning(f'Failed to load custom fonts: {str(e)}')
            # Fall back to standard fonts
            self.fonts = {
                'regular': 'Helvetica',
                'bold': 'Helvetica-Bold',
                'italic': 'Helvetica-Oblique',
                'light': 'Helvetica'
            }

    def load_templates(self):
        """Load default report templates."""
        self.template_cache['PLE_STANDARD'] = self.create_ple_template()
        self.template_cache['UCE_STANDARD'] = self.create_uce_template()
        self.template_cache['UACE_STANDARD'] = self.create_uace_template()

    def generate_pdf(self, report_data: Dict[str, Any]) -> str:
        """
        Generate a PDF report based on the given report data.
        
        Args:
            report_data: Dictionary containing report data including:
                - student: Student data dictionary
                - grades: List of grade dictionaries
                - term: Term identifier
                - academic_year: Academic year
                - template: Template name (optional)
                - options: Additional options (optional)
                
        Returns:
            Path to the generated PDF file
        """
        try:
            self.validate_report_data(report_data)
            
            student = report_data['student']
            term = report_data['term']
            academic_year = report_data['academic_year']
            
            # Determine template
            template_type = self.get_template_type(student['class_level'])
            template_key = f"{template_type}_STANDARD"
            template = self.template_cache.get(template_key)
            
            if not template:
                raise ValueError(f"No template found for {template_key}")
            
            # Generate filename
            filename = self.generate_filename(student, term, academic_year)
            filepath = self.output_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=A4,
                leftMargin=20*mm,
                rightMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # Build story (content elements)
            story = []
            self.build_report_content(story, report_data, template)
            
            # Generate PDF
            doc.build(story)
            
            self.logger.info(f'Generated PDF report: {filepath}')
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f'Failed to generate PDF: {str(e)}')
            raise

    def generate_bulk_reports(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate reports for multiple students based on criteria.
        
        Args:
            criteria: Dictionary containing:
                - class_level: Class level to generate reports for
                - term: Term identifier
                - academic_year: Academic year
                - template: Template name (optional)
                - output_format: 'individual' or 'combined' (default: 'individual')
                - options: Additional options (optional)
                
        Returns:
            Dictionary with summary of generation results
        """
        try:
            class_level = criteria['class_level']
            term = criteria['term']
            academic_year = criteria['academic_year']
            template = criteria.get('template', 'STANDARD')
            output_format = criteria.get('output_format', 'individual')
            
            # Get students
            students = self.db.get_students({'class_level': class_level})
            
            if not students:
                raise ValueError('No students found matching criteria')
            
            results = []
            batch_size = 10  # Process in batches to manage memory
            
            for i in range(0, len(students), batch_size):
                batch = students[i:i + batch_size]
                batch_results = []
                
                for student in batch:
                    try:
                        # Get student grades
                        grades = self.db.execute_query(
                            "SELECT g.*, s.name as subject_name FROM grades g "
                            "JOIN subjects s ON g.subject_id = s.id "
                            "WHERE g.student_id = ? AND g.term = ? AND g.academic_year = ?",
                            (student['id'], term, academic_year)
                        )
                        
                        # Generate report
                        filepath = self.generate_pdf({
                            'student': student,
                            'grades': grades,
                            'term': term,
                            'academic_year': academic_year,
                            'template': template,
                            'options': criteria.get('options', {})
                        })
                        
                        batch_results.append({
                            'success': True,
                            'student': student['name'],
                            'filepath': filepath
                        })
                    except Exception as e:
                        self.logger.error(f"Failed to generate report for {student['name']}: {str(e)}")
                        batch_results.append({
                            'success': False,
                            'student': student['name'],
                            'error': str(e)
                        })
                
                results.extend(batch_results)
                self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(students)-1)//batch_size + 1}")
            
            # Create summary
            summary = {
                'total': len(students),
                'successful': sum(1 for r in results if r['success']),
                'failed': sum(1 for r in results if not r['success']),
                'results': results
            }
            
            self.logger.info(f"Bulk report generation completed: {summary['successful']}/{summary['total']} successful")
            return summary
            
        except Exception as e:
            self.logger.error(f'Bulk report generation failed: {str(e)}')
            raise

    def build_report_content(self, story: List, report_data: Dict[str, Any], template: Dict[str, Any]):
        """Build the content of the report."""
        student = report_data['student']
        grades = report_data['grades']
        term = report_data['term']
        academic_year = report_data['academic_year']
        options = report_data.get('options', {})
        
        # Get school info
        school_info = self.get_school_info()
        
        # Add header
        self.add_report_header(story, school_info, options)
        
        # Add student info
        self.add_student_info(story, student, term, academic_year)
        
        # Add grades table
        self.add_grades_table(story, student, grades, template)
        
        # Add performance summary
        self.add_performance_summary(story, student, grades, template)
        
        # Add conduct and attendance
        self.add_conduct_attendance(story, student, term, academic_year)
        
        # Add comments section
        self.add_comments_section(story)
        
        # Add footer
        self.add_report_footer(story, school_info)
        
        # Add QR code
        self.add_qr_code(story, student, term, academic_year)

    def add_report_header(self, story: List, school_info: Dict[str, Any], options: Dict[str, Any]):
        """Add report header to the story."""
        # School logo (if available)
        if school_info.get('logo') and options.get('include_logo', True):
            try:
                logo_img = Image(BytesIO(school_info['logo']), width=20*mm, height=20*mm)
                story.append(logo_img)
            except Exception as e:
                self.logger.warning(f"Failed to add school logo: {str(e)}")
        
        # School information
        styles = self.get_styles()
        
        # School name
        story.append(Paragraph(
            school_info['name'],
            styles['Heading1']
        ))
        
        # School details
        details = [
            school_info['address'],
            f"Tel: {school_info['phone']} | Email: {school_info['email']}"
        ]
        for detail in details:
            story.append(Paragraph(
                detail,
                styles['BodyText']
            ))
        
        # Report title
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph(
            "STUDENT REPORT CARD",
            styles['Heading2']
        ))
        
        # Decorative line
        story.append(Spacer(1, 5*mm))
        line = Table(
            [['']],
            colWidths=[150*mm],
            style=[
                ('LINEABOVE', (0,0), (-1,-1), 1, self.colors['secondary']),
                ('LINEBELOW', (0,0), (-1,-1), 1, self.colors['secondary'])
            ]
        )
        story.append(line)
        story.append(Spacer(1, 10*mm))

    def add_student_info(self, story: List, student: Dict[str, Any], term: str, academic_year: str):
        """Add student information section."""
        styles = self.get_styles()
        
        # Info box
        student_data = [
            ['Student Name:', student['name']],
            ['Student ID:', student['student_id']],
            ['Class:', student['class_level']],
            ['Term:', f"{term.replace('term', 'Term ')} {academic_year}"],
            ['Date of Birth:', student.get('date_of_birth', 'N/A')]
        ]
        
        student_table = Table(
            student_data,
            colWidths=[40*mm, 60*mm],
            style=[
                ('BACKGROUND', (0,0), (-1,-1), self.colors['background']),
                ('BOX', (0,0), (-1,-1), 1, self.colors['secondary']),
                ('FONT', (0,0), (-1,-1), self.fonts['regular']),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,-1), 'RIGHT'),
                ('ALIGN', (1,0), (1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5)
            ]
        )
        
        story.append(student_table)
        story.append(Spacer(1, 10*mm))

    def add_grades_table(self, story: List, student: Dict[str, Any], grades: List[Dict[str, Any]], template: Dict[str, Any]):
        """Add grades table to the report."""
        styles = self.get_styles()
        
        # Process grades
        processed_grades = []
        for grade in grades:
            grade_letter = self.calculate_grade_letter(grade['score'], student['class_level'])
            processed_grades.append([
                grade['subject_name'],
                str(grade['score']),
                grade_letter,
                '',  # Position would be calculated
                self.get_grade_remark(grade['score'])
            ])
        
        # Table header
        header = ['Subject', 'Score', 'Grade', 'Position', 'Remarks']
        
        # Build table data
        table_data = [header] + processed_grades
        
        # Create table
        grades_table = Table(
            table_data,
            colWidths=[70*mm, 25*mm, 25*mm, 25*mm, 45*mm],
            style=[
                ('BACKGROUND', (0,0), (-1,0), self.colors['secondary']),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),
                ('FONT', (0,0), (-1,0), self.fonts['bold']),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
                ('FONT', (0,1), (-1,-1), self.fonts['regular']),
                ('FONTSIZE', (0,1), (-1,-1), 9),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (1,1), (2,-1), 'CENTER'),
                ('TEXTCOLOR', (2,1), (2,-1), self.get_grade_color(processed_grades[0][2])),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [self.colors['background'], colors.white])
            ]
        )
        
        story.append(Paragraph("ACADEMIC PERFORMANCE", styles['Heading3']))
        story.append(Spacer(1, 5*mm))
        story.append(grades_table)
        story.append(Spacer(1, 10*mm))

    def add_performance_summary(self, story: List, student: Dict[str, Any], grades: List[Dict[str, Any]], template: Dict[str, Any]):
        """Add performance summary section."""
        styles = self.get_styles()
        
        # Calculate summary
        summary = self.calculate_performance_summary(grades, student['class_level'])
        
        # Summary data
        summary_data = [
            ['Total Subjects:', str(summary['total_subjects'])],
            ['Average Score:', f"{summary['average_score']}%"],
            ['Overall Grade:', summary['overall_grade']],
            ['Class Position:', summary['class_position'] or 'N/A']
        ]
        
        if student['class_level'] == 'S6':
            summary_data.append(['Total Points:', str(summary['total_points'] or 'N/A')])
        
        # Create summary table
        summary_table = Table(
            summary_data,
            colWidths=[50*mm, 30*mm],
            style=[
                ('BACKGROUND', (0,0), (-1,-1), self.colors['background']),
                ('BOX', (0,0), (-1,-1), 1, self.colors['secondary']),
                ('FONT', (0,0), (-1,-1), self.fonts['regular']),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,-1), 'RIGHT'),
                ('ALIGN', (1,0), (1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5)
            ]
        )
        
        story.append(Paragraph("PERFORMANCE SUMMARY", styles['Heading3']))
        story.append(Spacer(1, 5*mm))
        
        # Create a 2-column layout
        elements = []
        
        # Left column - summary table
        elements.append(summary_table)
        
        # Right column - grade distribution chart
        chart_img = self.create_grade_chart(summary['grade_distribution'])
        if chart_img:
            elements.append(Spacer(1, 10*mm))
            elements.append(chart_img)
        
        # Add both columns to story
        two_col_table = Table(
            [[elements[0], elements[-1]]],
            colWidths=[100*mm, 70*mm],
            style=[
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (0,0), (0,0), 'LEFT'),
                ('ALIGN', (1,0), (1,0), 'RIGHT')
            ]
        )
        
        story.append(two_col_table)
        story.append(Spacer(1, 10*mm))

    def add_conduct_attendance(self, story: List, student: Dict[str, Any], term: str, academic_year: str):
        """Add conduct and attendance section."""
        styles = self.get_styles()
        
        # Get conduct data
        conduct_data = self.get_conduct_data(student['id'], term, academic_year)
        
        # Get attendance data
        attendance_data = self.get_attendance_data(student['id'], term, academic_year)
        
        # Create two-column layout
        elements = []
        
        # Conduct box
        conduct_items = [
            ['Behavior Grade:', conduct_data.get('behavior_grade', 'Good')],
            ['Discipline Score:', f"{conduct_data.get('discipline_score', 4)}/5"],
            ['Punctuality:', conduct_data.get('punctuality', 'Good')]
        ]
        
        conduct_table = Table(
            conduct_items,
            colWidths=[50*mm, 30*mm],
            style=[
                ('BACKGROUND', (0,0), (-1,-1), self.colors['background']),
                ('BOX', (0,0), (-1,-1), 1, self.colors['secondary']),
                ('FONT', (0,0), (-1,-1), self.fonts['regular']),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,-1), 'RIGHT'),
                ('ALIGN', (1,0), (1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5)
            ]
        )
        
        # Attendance box
        attendance_items = [
            ['Days Present:', str(attendance_data.get('present_days', 0))],
            ['Days Absent:', str(attendance_data.get('absent_days', 0))],
            ['Attendance %:', f"{attendance_data.get('attendance_percentage', 100)}%"]
        ]
        
        attendance_table = Table(
            attendance_items,
            colWidths=[50*mm, 30*mm],
            style=[
                ('BACKGROUND', (0,0), (-1,-1), self.colors['background']),
                ('BOX', (0,0), (-1,-1), 1, self.colors['secondary']),
                ('FONT', (0,0), (-1,-1), self.fonts['regular']),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,-1), 'RIGHT'),
                ('ALIGN', (1,0), (1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 5)
            ]
        )
        
        # Add section title
        story.append(Paragraph("CONDUCT & ATTENDANCE", styles['Heading3']))
        story.append(Spacer(1, 5*mm))
        
        # Create two-column table
        two_col_table = Table(
            [[
                Paragraph("CONDUCT & DISCIPLINE", styles['Heading4']),
                Paragraph("ATTENDANCE RECORD", styles['Heading4'])
            ], [
                conduct_table,
                attendance_table
            ]],
            colWidths=[80*mm, 80*mm],
            style=[
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10)
            ]
        )
        
        story.append(two_col_table)
        story.append(Spacer(1, 10*mm))

    def add_comments_section(self, story: List):
        """Add comments section to the report."""
        styles = self.get_styles()
        
        # Comments title
        story.append(Paragraph("TEACHER'S COMMENTS", styles['Heading3']))
        story.append(Spacer(1, 5*mm))
        
        # Comments box with lines
        comments_box = Table(
            [[''], [''], ['']],
            colWidths=[150*mm],
            rowHeights=[15*mm, 15*mm, 15*mm],
            style=[
                ('BOX', (0,0), (-1,-1), 1, self.colors['secondary']),
                ('LINEBELOW', (0,0), (0,0), 1, colors.lightgrey),
                ('LINEBELOW', (0,1), (0,1), 1, colors.lightgrey),
                ('VALIGN', (0,0), (-1,-1), 'TOP')
            ]
        )
        
        story.append(comments_box)
        story.append(Spacer(1, 15*mm))

    def add_report_footer(self, story: List, school_info: Dict[str, Any]):
        """Add report footer with signatures."""
        styles = self.get_styles()
        
        # Signature lines
        footer_data = [
            ['Class Teacher: ___________________', 'Head Teacher: ___________________'],
            ['Date: ___________', 'Date: ___________']
        ]
        
        footer_table = Table(
            footer_data,
            colWidths=[80*mm, 80*mm],
            style=[
                ('FONT', (0,0), (-1,-1), self.fonts['regular']),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ('ALIGN', (1,0), (1,-1), 'RIGHT')
            ]
        )
        
        story.append(footer_table)
        story.append(Spacer(1, 10*mm))
        
        # School motto
        if school_info.get('motto'):
            story.append(Paragraph(
                f'"{school_info["motto"]}"',
                styles['FooterText']
            ))
            story.append(Spacer(1, 5*mm))
        
        # Generation info
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d')} by Marka Report Generator",
            styles['FooterSmall']
        ))

    def add_qr_code(self, story: List, student: Dict[str, Any], term: str, academic_year: str):
        """Add QR code for verification."""
        try:
            # Generate verification data
            verification_data = {
                'student_id': student['student_id'],
                'name': student['name'],
                'class': student['class_level'],
                'term': term,
                'academic_year': academic_year,
                'generated': datetime.now().isoformat(),
                'hash': self.generate_verification_hash(student, term, academic_year)
            }
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(json.dumps(verification_data))
            qr.make(fit=True)
            
            # Create image
            qr_img = qr.make_image(fill_color=self.colors['primary'].hex[1:], back_color="white")
            
            # Convert to bytes
            img_bytes = BytesIO()
            qr_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Add to story
            qr_image = Image(img_bytes, width=30*mm, height=30*mm)
            qr_image.hAlign = 'RIGHT'
            story.append(qr_image)
            
            # Add verification text
            story.append(Paragraph(
                "Scan for verification",
                ParagraphStyle(
                    name='QRText',
                    fontName=self.fonts['regular'],
                    fontSize=6,
                    textColor=self.colors['text_light'],
                    alignment=2  # Right aligned
                )
            ))
            
        except Exception as e:
            self.logger.warning(f"Failed to add QR code: {str(e)}")

    # Helper methods

    def validate_report_data(self, report_data: Dict[str, Any]):
        """Validate report data before generation."""
        required_fields = ['student', 'grades', 'term', 'academic_year']
        for field in required_fields:
            if field not in report_data:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(report_data['grades'], list):
            raise ValueError("Grades must be a list")
        
        if report_data['term'] not in ['term1', 'term2', 'term3']:
            raise ValueError("Invalid term value")

    def get_template_type(self, class_level: str) -> str:
        """Determine template type based on class level."""
        if class_level == 'P7': return 'PLE'
        if class_level == 'S4': return 'UCE'
        if class_level == 'S6': return 'UACE'
        return 'STANDARD'

    def generate_filename(self, student: Dict[str, Any], term: str, academic_year: str) -> str:
        """Generate a unique filename for the report."""
        sanitized_name = ''.join(c if c.isalnum() else '_' for c in student['name'])
        timestamp = datetime.now().strftime('%Y%m%d')
        return f"{sanitized_name}_{student['student_id']}_{term}_{academic_year}_{timestamp}.pdf"

    def get_school_info(self) -> Dict[str, Any]:
        """Get school information from database or defaults."""
        try:
            settings = self.db.get_all_settings()
            return {
                'name': settings.get('school_name', {}).get('value', 'Sample School'),
                'address': settings.get('school_address', {}).get('value', 'School Address'),
                'phone': settings.get('school_phone', {}).get('value', '+256 XXX XXXXXX'),
                'email': settings.get('school_email', {}).get('value', 'info@school.edu'),
                'motto': settings.get('school_motto', {}).get('value', 'Excellence in Education'),
                'logo': settings.get('school_logo', {}).get('value')
            }
        except Exception as e:
            self.logger.error(f"Failed to get school info: {str(e)}")
            return {
                'name': 'Sample School',
                'address': 'School Address',
                'phone': '+256 XXX XXXXXX',
                'email': 'info@school.edu',
                'motto': 'Excellence in Education',
                'logo': None
            }

    def calculate_grade_letter(self, score: float, class_level: str) -> str:
        """Calculate grade letter based on score and class level."""
        if class_level == 'P7':
            # PLE grading system
            if score >= 90: return 'D1'
            if score >= 80: return 'D2'
            if score >= 70: return 'C3'
            if score >= 60: return 'C4'
            if score >= 50: return 'C5'
            if score >= 40: return 'C6'
            return 'P7'
        else:
            # UCE/UACE grading system
            if score >= 85: return 'A'
            if score >= 75: return 'B'
            if score >= 65: return 'C'
            if score >= 55: return 'D'
            if score >= 45: return 'E'
            return 'F'

    def get_grade_color(self, grade: str) -> colors.Color:
        """Get color for a grade letter."""
        grade_colors = {
            'A': self.colors['success'],
            'B': colors.HexColor('#3B82F6'),
            'C': self.colors['warning'],
            'D': self.colors['error'],
            'E': self.colors['error'],
            'F': self.colors['text_light'],
            'D1': self.colors['success'],
            'D2': self.colors['success'],
            'C3': colors.HexColor('#3B82F6'),
            'C4': colors.HexColor('#3B82F6'),
            'C5': self.colors['warning'],
            'C6': self.colors['warning'],
            'P7': self.colors['error']
        }
        return grade_colors.get(grade, self.colors['text'])

    def get_grade_remark(self, score: float) -> str:
        """Get remark for a score."""
        if score >= 85: return 'Excellent'
        if score >= 75: return 'Very Good'
        if score >= 65: return 'Good'
        if score >= 55: return 'Satisfactory'
        if score >= 45: return 'Fair'
        return 'Needs Improvement'

    def calculate_performance_summary(self, grades: List[Dict[str, Any]], class_level: str) -> Dict[str, Any]:
        """Calculate performance summary statistics."""
        total_subjects = len(grades)
        total_score = sum(grade['score'] for grade in grades)
        average_score = round(total_score / total_subjects) if total_subjects > 0 else 0
        
        # Calculate grade distribution
        grade_distribution = {}
        for grade in grades:
            letter = self.calculate_grade_letter(grade['score'], class_level)
            base_letter = letter[0] if len(letter) > 1 else letter
            grade_distribution[base_letter] = grade_distribution.get(base_letter, 0) + 1
        
        return {
            'total_subjects': total_subjects,
            'average_score': average_score,
            'overall_grade': self.calculate_grade_letter(average_score, class_level),
            'grade_distribution': grade_distribution,
            'class_position': None,  # Would need class-wide data
            'total_points': self.calculate_uace_points(grades) if class_level == 'S6' else None
        }

    def calculate_uace_points(self, grades: List[Dict[str, Any]]) -> int:
        """Calculate UACE points."""
        points_map = {'A': 6, 'B': 5, 'C': 4, 'D': 3, 'E': 2, 'O': 1, 'F': 0}
        total_points = 0
        for grade in grades:
            total_points += points_map.get(self.calculate_grade_letter(grade['score'], 'S6'), 0)
        return total_points

    def get_conduct_data(self, student_id: int, term: str, academic_year: str) -> Dict[str, Any]:
        """Get conduct data for a student."""
        try:
            conduct = self.db.execute_query(
                "SELECT * FROM conduct WHERE student_id = ? AND term = ? AND academic_year = ?",
                (student_id, term, academic_year)
            )
            return conduct[0] if conduct else {}
        except Exception as e:
            self.logger.error(f"Failed to get conduct data: {str(e)}")
            return {}

    def get_attendance_data(self, student_id: int, term: str, academic_year: str) -> Dict[str, Any]:
        """Get attendance data for a student."""
        try:
            attendance = self.db.execute_query(
                "SELECT "
                "COUNT(CASE WHEN status = 'Present' THEN 1 END) as present_days, "
                "COUNT(CASE WHEN status = 'Absent' THEN 1 END) as absent_days, "
                "ROUND(COUNT(CASE WHEN status = 'Present' THEN 1 END) * 100.0 / COUNT(*), 1) as attendance_percentage "
                "FROM attendance "
                "WHERE student_id = ? AND term = ? AND academic_year = ?",
                (student_id, term, academic_year)
            )
            return attendance[0] if attendance else {'present_days': 0, 'absent_days': 0, 'attendance_percentage': 100}
        except Exception as e:
            self.logger.error(f"Failed to get attendance data: {str(e)}")
            return {'present_days': 0, 'absent_days': 0, 'attendance_percentage': 100}

    def create_grade_chart(self, grade_distribution: Dict[str, int]) -> Optional[Image]:
        """Create a simple grade distribution chart."""
        try:
            # This would be replaced with actual chart generation
            # For now, we'll return None as reportlab's charting capabilities are limited
            return None
        except Exception as e:
            self.logger.warning(f"Failed to create grade chart: {str(e)}")
            return None

    def generate_verification_hash(self, student: Dict[str, Any], term: str, academic_year: str) -> str:
        """Generate verification hash for QR code."""
        data = f"{student['student_id']}:{term}:{academic_year}:{datetime.now().date()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def get_styles(self) -> Dict[str, ParagraphStyle]:
        """Get predefined paragraph styles."""
        styles = getSampleStyleSheet()
        
        custom_styles = {
            'Heading1': ParagraphStyle(
                'Heading1',
                parent=styles['Heading1'],
                fontName=self.fonts['bold'],
                fontSize=16,
                textColor=self.colors['primary'],
                spaceAfter=12
            ),
            'Heading2': ParagraphStyle(
                'Heading2',
                parent=styles['Heading2'],
                fontName=self.fonts['bold'],
                fontSize=14,
                textColor=self.colors['primary'],
                alignment=1,  # Center aligned
                spaceAfter=12
            ),
            'Heading3': ParagraphStyle(
                'Heading3',
                parent=styles['Heading3'],
                fontName=self.fonts['bold'],
                fontSize=12,
                textColor=self.colors['primary'],
                spaceAfter=6
            ),
            'Heading4': ParagraphStyle(
                'Heading4',
                parent=styles['Heading4'],
                fontName=self.fonts['bold'],
                fontSize=10,
                textColor=self.colors['primary'],
                alignment=1,  # Center aligned
                spaceAfter=6
            ),
            'BodyText': ParagraphStyle(
                'BodyText',
                parent=styles['BodyText'],
                fontName=self.fonts['regular'],
                fontSize=10,
                textColor=self.colors['text'],
                spaceAfter=6
            ),
            'FooterText': ParagraphStyle(
                'FooterText',
                parent=styles['BodyText'],
                fontName=self.fonts['italic'],
                fontSize=10,
                textColor=self.colors['text_light'],
                alignment=1,  # Center aligned
                spaceAfter=6
            ),
            'FooterSmall': ParagraphStyle(
                'FooterSmall',
                parent=styles['BodyText'],
                fontName=self.fonts['light'],
                fontSize=8,
                textColor=self.colors['text_light'],
                alignment=1,  # Center aligned
                spaceAfter=0
            )
        }
        
        return {**styles, **custom_styles}

    # Template creation methods
    def create_ple_template(self) -> Dict[str, Any]:
        """Create PLE standard template."""
        return {
            'name': 'PLE Standard Template',
            'type': 'PLE',
            'grading_system': 'division',
            'subjects': ['English', 'Mathematics', 'Science', 'Social Studies'],
            'show_aggregate': True,
            'show_division': True
        }

    def create_uce_template(self) -> Dict[str, Any]:
        """Create UCE standard template."""
        return {
            'name': 'UCE Standard Template',
            'type': 'UCE',
            'grading_system': 'letter',
            'subjects': ['English', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'History', 'Geography'],
            'show_aggregate': False,
            'show_division': False
        }

    def create_uace_template(self) -> Dict[str, Any]:
        """Create UACE standard template."""
        return {
            'name': 'UACE Standard Template',
            'type': 'UACE',
            'grading_system': 'points',
            'subjects': [],  # Variable based on combination
            'show_points': True,
            'show_university_eligibility': True
        }

    def cleanup(self):
        """Clean up resources."""
        self.template_cache.clear()
        self.logger.info('ReportGenerator cleanup completed')