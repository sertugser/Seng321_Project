import csv
from io import StringIO, BytesIO
from flask import make_response
from models.entities import Submission, Grade, User
from datetime import datetime, timedelta, timezone
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class ReportService:
    @staticmethod
    def _utc_to_gmt3(utc_dt):
        """Convert UTC datetime to GMT+3 timezone"""
        if utc_dt is None:
            return None
        # GMT+3 is UTC+3
        gmt3_offset = timedelta(hours=3)
        if utc_dt.tzinfo is None:
            # If naive datetime, assume it's UTC
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        return (utc_dt + gmt3_offset).replace(tzinfo=None)
    
    @staticmethod
    def _get_gmt3_now():
        """Get current time in GMT+3"""
        return ReportService._utc_to_gmt3(datetime.utcnow())
    
    @staticmethod
    def generate_pdf(student_id=None):
        """
        Generate PDF report using ReportLab
        Returns PDF bytes
        """
        if not REPORTLAB_AVAILABLE:
            # Fallback: return text representation
            return b"PDF generation requires reportlab library. Please install with: pip install reportlab"
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define consistent font sizes for all elements
        TITLE_FONT_SIZE = 18
        DATE_FONT_SIZE = 11
        INFO_FONT_SIZE = 11
        SUMMARY_FONT_SIZE = 11
        HEADER_FONT_SIZE = 11
        DATA_FONT_SIZE = 10
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=TITLE_FONT_SIZE,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Title
        title = Paragraph("Student Performance Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Report date - use GMT+3
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=DATE_FONT_SIZE,
            textColor=colors.HexColor('#64748b'),
            alignment=1
        )
        generated_time = ReportService._get_gmt3_now()
        date_text = Paragraph(f"Generated on: {generated_time.strftime('%B %d, %Y at %I:%M %p')} (GMT+3)", date_style)
        elements.append(date_text)
        elements.append(Spacer(1, 0.3*inch))
        
        # Get data - sorted chronologically (oldest first)
        if student_id:
            submissions = Submission.query.filter_by(student_id=student_id).order_by(Submission.created_at.asc()).all()
            student = User.query.get(student_id)
            student_name = student.username if student else 'Unknown'
            
            # Student info
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontSize=INFO_FONT_SIZE,
                textColor=colors.HexColor('#334155'),
                leftIndent=20
            )
            elements.append(Paragraph(f"<b>Student:</b> {student_name}", info_style))
            elements.append(Paragraph(f"<b>Email:</b> {student.email if student else 'N/A'}", info_style))
            elements.append(Paragraph(f"<b>Total Submissions:</b> {len(submissions)}", info_style))
            elements.append(Spacer(1, 0.2*inch))
        else:
            submissions = Submission.query.order_by(Submission.created_at.asc()).all()
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontSize=INFO_FONT_SIZE,
                textColor=colors.HexColor('#334155'),
                leftIndent=20
            )
            elements.append(Paragraph(f"<b>Total Submissions:</b> {len(submissions)}", info_style))
            elements.append(Spacer(1, 0.2*inch))
        
        if not submissions:
            no_data_style = ParagraphStyle(
                'NoDataStyle',
                parent=styles['Normal'],
                fontSize=INFO_FONT_SIZE,
                textColor=colors.HexColor('#334155'),
                alignment=1
            )
            elements.append(Paragraph("No submissions found.", no_data_style))
        else:
            # Prepare table data without evaluated at column
            table_data = [['Submission Date', 'Type', 'Score', 'Status']]
            
            graded_count = 0
            total_score = 0
            
            for sub in submissions:
                # Convert submission date to GMT+3
                sub_date_gmt3 = ReportService._utc_to_gmt3(sub.created_at)
                date_str = sub_date_gmt3.strftime('%Y-%m-%d %H:%M') if sub_date_gmt3 else 'N/A'
                sub_type = sub.submission_type
                
                if sub.grade:
                    score = sub.grade.score
                    status = 'Graded' if sub.grade.instructor_approved else 'Pending'
                    graded_count += 1
                    total_score += score
                else:
                    score = 'N/A'
                    status = 'No Grade'
                
                table_data.append([date_str, sub_type, str(score), status])
            
            # Create table with adjusted column widths (removed evaluated at column)
            # Use consistent font sizes for better aesthetics (defined at top of function)
            table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), HEADER_FONT_SIZE),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), DATA_FONT_SIZE),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Summary statistics
            if graded_count > 0:
                avg_score = round(total_score / graded_count, 1)
                summary_style = ParagraphStyle(
                    'SummaryStyle',
                    parent=styles['Normal'],
                    fontSize=SUMMARY_FONT_SIZE,
                    textColor=colors.HexColor('#334155'),
                    leftIndent=20
                )
                elements.append(Paragraph("<b>Summary:</b>", summary_style))
                elements.append(Paragraph(f"Average Score: {avg_score}", summary_style))
                elements.append(Paragraph(f"Graded Submissions: {graded_count} / {len(submissions)}", summary_style))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def generate_csv(student_id=None):
        """
        Generate CSV report of submissions and grades
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Clean, readable headers in English
        if student_id:
            # For single student, no need for student info
            writer.writerow(['Date', 'Submission Type', 'Score', 'Status', 'Feedback'])
        else:
            # For all students, include student name
            writer.writerow(['Student', 'Date', 'Submission Type', 'Score', 'Status', 'Feedback'])
        
        if student_id:
            submissions = Submission.query.filter_by(student_id=student_id).order_by(Submission.created_at.asc()).all()
        else:
            submissions = Submission.query.order_by(Submission.created_at.asc()).all()
        
        # Type mapping for readability in English
        type_map = {
            'WRITING': 'Writing',
            'SPEAKING': 'Speaking',
            'HANDWRITTEN': 'Handwritten',
            'QUIZ': 'Quiz'
        }
        
        for sub in submissions:
            # Format score
            if sub.grade and sub.grade.score is not None:
                score = f"{sub.grade.score:.1f}"
                status = 'Graded' if sub.grade.instructor_approved else 'Pending'
            else:
                score = '-'
                status = 'Not Graded'
            
            # Format submission date to GMT+3 - more readable format
            sub_date_gmt3 = ReportService._utc_to_gmt3(sub.created_at)
            date_str = sub_date_gmt3.strftime('%Y-%m-%d %H:%M') if sub_date_gmt3 else 'N/A'
            
            # Format submission type
            submission_type = type_map.get(sub.submission_type, sub.submission_type.capitalize())
            
            # Format feedback - clean and concise
            if sub.grade and sub.grade.general_feedback:
                feedback = sub.grade.general_feedback.strip()
                # Limit to 150 characters for readability
                if len(feedback) > 150:
                    feedback = feedback[:147] + '...'
            else:
                feedback = '-'
            
            if student_id:
                # Single student - no student name column
                writer.writerow([
                    date_str,
                    submission_type,
                    score,
                    status,
                    feedback
                ])
            else:
                # All students - include student name
                student_name = sub.student.username if sub.student else 'Unknown'
                writer.writerow([
                    student_name,
                    date_str,
                    submission_type,
                    score,
                    status,
                    feedback
                ])
        
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def export_report(student_id=None, format='csv'):
        """
        Export report in specified format
        """
        if format == 'csv':
            return ReportService.generate_csv(student_id)
        elif format == 'pdf':
            return ReportService.generate_pdf(student_id)
        else:
            return None







