import csv
from io import StringIO, BytesIO
from flask import make_response
from models.entities import Submission, Grade, User
from datetime import datetime
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
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Title
        title = Paragraph("Student Performance Report", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Report date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            alignment=1
        )
        date_text = Paragraph(f"Generated on: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}", date_style)
        elements.append(date_text)
        elements.append(Spacer(1, 0.3*inch))
        
        # Get data
        if student_id:
            submissions = Submission.query.filter_by(student_id=student_id).order_by(Submission.created_at.desc()).all()
            student = User.query.get(student_id)
            student_name = student.username if student else 'Unknown'
            
            # Student info
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#334155'),
                leftIndent=20
            )
            elements.append(Paragraph(f"<b>Student:</b> {student_name}", info_style))
            elements.append(Paragraph(f"<b>Email:</b> {student.email if student else 'N/A'}", info_style))
            elements.append(Paragraph(f"<b>Total Submissions:</b> {len(submissions)}", info_style))
            elements.append(Spacer(1, 0.2*inch))
        else:
            submissions = Submission.query.order_by(Submission.created_at.desc()).all()
            elements.append(Paragraph(f"<b>Total Submissions:</b> {len(submissions)}", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        if not submissions:
            elements.append(Paragraph("No submissions found.", styles['Normal']))
        else:
            # Prepare table data
            table_data = [['Date', 'Type', 'Score', 'Status']]
            
            graded_count = 0
            total_score = 0
            
            for sub in submissions:
                date_str = sub.created_at.strftime('%Y-%m-%d')
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
            
            # Create table
            table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Summary statistics
            if graded_count > 0:
                avg_score = round(total_score / graded_count, 1)
                summary_style = ParagraphStyle(
                    'SummaryStyle',
                    parent=styles['Normal'],
                    fontSize=11,
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
        
        # Write header
        writer.writerow(['Student ID', 'Student Name', 'Submission Type', 'Score', 'Date', 'Feedback'])
        
        if student_id:
            submissions = Submission.query.filter_by(student_id=student_id).all()
        else:
            submissions = Submission.query.all()
        
        for sub in submissions:
            student_name = sub.student.username if sub.student else 'Unknown'
            score = sub.grade.score if sub.grade else 'N/A'
            feedback = sub.grade.general_feedback[:50] if sub.grade and sub.grade.general_feedback else 'N/A'
            
            writer.writerow([
                sub.student_id,
                student_name,
                sub.submission_type,
                score,
                sub.created_at.strftime('%Y-%m-%d %H:%M:%S'),
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







