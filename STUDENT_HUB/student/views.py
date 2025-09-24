from django.http import FileResponse
import io
from reportlab.pdfgen import canvas

# PDF download for student profile (modal content)
def download_student_profile_pdf(request):
    email = request.GET.get("email")
    if not email:
        return HttpResponse("No email provided", status=400)
    try:
        student = Student.objects.get(email=email)
    except Student.DoesNotExist:
        return HttpResponse("Student not found", status=404)
    attended_classes = Attendance.objects.filter(student=student, status='Present').count()
    total_classes = Attendance.objects.filter(student=student).count()
    attendance_percent = round((attended_classes / total_classes) * 100, 1) if total_classes else 0
    activities = Activities.objects.filter(student_email=student).order_by('-date')[:4]
    latest_result = Results.objects.filter(student_email=student).order_by('-semester').first()
    cgpa = latest_result.cgpa if latest_result else 0.0
    linkedin = student.linkedin_url or "N/A"
    github = student.github_url or "N/A"

    import datetime
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    # Title and date/time
    p.setFont("Helvetica-Bold", 26)
    p.setFillColorRGB(0.1,0.2,0.4)
    p.drawString(50, y, "Student Report")
    p.setFont("Helvetica", 12)
    p.setFillColorRGB(0.2,0.2,0.2)
    now = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
    p.drawRightString(width-50, y, f"Generated: {now}")
    y -= 40

    # Student Info Card
    p.setFillColorRGB(0.23,0.51,0.96)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, y, f"{student.first_name} {student.last_name}")
    p.setFont("Helvetica", 14)
    p.setFillColorRGB(0,0,0)
    y -= 28
    p.drawString(50, y, f"{student.branch} Engineering")
    y -= 20
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Email: {student.email}")
    y -= 16
    p.drawString(50, y, f"Phone: {student.contact}")
    y -= 16
    p.drawString(50, y, f"CGPA: {cgpa}")
    y -= 16
    p.drawString(50, y, f"LinkedIn: {linkedin}")
    y -= 16
    p.drawString(50, y, f"GitHub: {github}")

    # Divider
    y -= 18
    p.setStrokeColorRGB(0.7,0.7,0.7)
    p.setLineWidth(1)
    p.line(50, y, width-50, y)
    y -= 28

    # Attendance Overview
    p.setFont("Helvetica-Bold", 15)
    p.setFillColorRGB(0.12,0.16,0.68)
    p.drawString(50, y, "Attendance Overview")
    p.setFont("Helvetica", 12)
    p.setFillColorRGB(0,0,0)
    y -= 20
    p.drawString(60, y, f"Overall Attendance: {attendance_percent}%")
    y -= 16
    p.drawString(60, y, f"Classes Attended: {attended_classes} of {total_classes}")
    y -= 16
    p.drawString(60, y, f"Active Subjects: 4")

    # Divider
    y -= 18
    p.setStrokeColorRGB(0.7,0.7,0.7)
    p.setLineWidth(1)
    p.line(50, y, width-50, y)
    y -= 28

    # Recent Activities
    p.setFont("Helvetica-Bold", 15)
    p.setFillColorRGB(0.12,0.16,0.68)
    p.drawString(50, y, "Recent Activities")
    p.setFont("Helvetica", 12)
    p.setFillColorRGB(0,0,0)
    y -= 20
    for act in activities:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(60, y, f"{act.activity_name}")
        y -= 14
        p.setFont("Helvetica", 12)
        p.drawString(80, y, f"{act.activity_type} • {act.date}")
        y -= 18
        if y < 100:
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()
    buffer.seek(0)
    safe_name = f"{student.first_name}_{student.last_name}_report".replace(" ", "_")
    filename = f"{safe_name}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


from django.db.models import Count, Q, Sum, Avg
from django.db.models.functions import TruncMonth, Coalesce
from datetime import timedelta, date
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Attendance, Subject, Student, Certificate, Projects, Activities, Faculty, Results
from .utils import get_student_name_by_email
# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

def first(request):
    return render(request, 'first.html')

def attendance_dashboard(request):
    student_email = request.session.get('student_email')
    student = Student.objects.get(email=student_email)

    # Overall stats
    total_classes = Attendance.objects.filter(student=student).count()
    attended_classes = Attendance.objects.filter(student=student, status='Present').count()
    overall_percent = round((attended_classes / total_classes) * 100, 1) if total_classes else 0

    # RTU performance = overall class attendance for all subjects
    rtu_total = total_classes
    rtu_attended = attended_classes
    rtu_absent = rtu_total - rtu_attended
    rtu_percent = overall_percent

    # Active courses
    active_courses = Attendance.objects.filter(student=student).values('subject').distinct().count()

    # Subject-wise stats
    subjects = Subject.objects.all()
    subject_stats = []
    for subject in subjects:
        sub_total = Attendance.objects.filter(student=student, subject=subject).count()
        sub_attended = Attendance.objects.filter(student=student, subject=subject, status='Present').count()
        percent = round((sub_attended / sub_total) * 100, 1) if sub_total else 0
        subject_stats.append({
            'name': subject.subject_name,
            'total': sub_total,
            'attended': sub_attended,
            'percent': percent,
        })

    # Monthly stats
    monthly_stats = Attendance.objects.filter(student=student).annotate(month=TruncMonth('date')).values('month').annotate(
        total=Count('id'),
        attended=Count('id', filter=Q(status='Present'))
    ).order_by('month')
    monthly_data = []
    for m in monthly_stats:
        percent = round((m['attended'] / m['total']) * 100, 1) if m['total'] else 0
        monthly_data.append({
            'month': m['month'].strftime('%b %Y'),
            'total': m['total'],
            'attended': m['attended'],
            'percent': percent,
        })

    # Daily records (last 7 days)
    today = date.today()
    records = Attendance.objects.filter(student=student, date__gte=today-timedelta(days=7)).order_by('-date')

    context = {
        'student': student,
        'overall_percent': overall_percent,
        'attended_classes': attended_classes,
        'total_classes': total_classes,
        'active_courses': active_courses,
        'subject_stats': subject_stats,
        'monthly_data': monthly_data,
        'records': records,
        'rtu_percent': rtu_percent,
        'rtu_attended': rtu_attended,
        'rtu_absent': rtu_absent,
    }
    return render(request, 'attendance.html', context)
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# CV PDF Download View
def download_cv_pdf(request):
    student_email = request.session.get("student_email")
    if not student_email:
        return redirect("login_student")
    try:
        student = Student.objects.get(email=student_email)
    except Student.DoesNotExist:
        return redirect("login_student")

    # Get approved items
    certs = Certificate.objects.filter(student_email=student, status="approved")
    projects = Projects.objects.filter(student_email=student, status="approved")
    activities = Activities.objects.filter(student_email=student, status="approved")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="cv_portfolio.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - inch

    # Professional Header
    # Professional Header (no time/date)
    p.setFont("Helvetica-Bold", 26)
    p.setFillColorRGB(0.1,0.2,0.4)
    p.drawString(inch, y, "Curriculum Vitae")
    y -= 0.45 * inch
    p.setStrokeColorRGB(0.15,0.15,0.5)
    p.setLineWidth(2)
    p.line(inch, y, width-inch, y)
    y -= 0.35 * inch

    # Name & Contact
    p.setFont("Helvetica-Bold", 18)
    p.setFillColorRGB(0,0,0)
    p.drawString(inch, y, f"{student.first_name} {student.last_name}")
    p.setFont("Helvetica", 13)
    p.drawString(inch, y-0.22*inch, f"{student.branch}")
    p.setFont("Helvetica", 12)
    p.drawString(inch, y-0.38*inch, f"Email: {student.email} | Phone: {student.contact}")
    y -= 0.7 * inch
    p.setStrokeColorRGB(0.7,0.7,0.7)
    p.setLineWidth(1)
    p.line(inch, y, width-inch, y)
    y -= 0.25 * inch

    # Section: Education
    p.setFont("Helvetica-Bold", 15)
    p.setFillColorRGB(0.1,0.2,0.4)
    p.drawString(inch, y, "Education")
    p.setFillColorRGB(0,0,0)
    y -= 0.22 * inch
    p.setFont("Helvetica", 12)
    p.drawString(inch+0.2*inch, y, f"Bachelor of Technology in {student.branch}")
    y -= 0.17 * inch
    p.drawString(inch+0.2*inch, y, f"{getattr(student, 'College_name', '')} | Session: {getattr(student, 'session', '')} | CGPA: {getattr(student, 'cgpa', '')}")
    y -= 0.25 * inch
    p.setStrokeColorRGB(0.85,0.85,0.85)
    p.setLineWidth(1)
    p.line(inch, y, width-inch, y)
    y -= 0.22 * inch

    # Section: Certifications
    if certs.exists():
        p.setFont("Helvetica-Bold", 15)
        p.setFillColorRGB(0.1,0.2,0.4)
        p.drawString(inch, y, "Certifications")
        p.setFillColorRGB(0,0,0)
        y -= 0.22 * inch
        p.setFont("Helvetica", 12)
        for cert in certs:
            p.drawString(inch+0.2*inch, y, f"{cert.certificate_name} from {cert.organization} ({cert.issue_date.year})")
            y -= 0.17 * inch
            if y < inch:
                p.showPage(); y = height - inch
        y -= 0.22 * inch
        p.setStrokeColorRGB(0.85,0.85,0.85)
        p.setLineWidth(1)
        p.line(inch, y, width-inch, y)
        y -= 0.22 * inch

    # Section: Projects
    if projects.exists():
        p.setFont("Helvetica-Bold", 15)
        p.setFillColorRGB(0.1,0.2,0.4)
        p.drawString(inch, y, "Projects")
        p.setFillColorRGB(0,0,0)
        y -= 0.22 * inch
        p.setFont("Helvetica", 12)
        for proj in projects:
            p.drawString(inch+0.2*inch, y, f"{proj.project_name} - Subject: {proj.subject}")
            y -= 0.17 * inch
            if y < inch:
                p.showPage(); y = height - inch
        y -= 0.22 * inch
        p.setStrokeColorRGB(0.85,0.85,0.85)
        p.setLineWidth(1)
        p.line(inch, y, width-inch, y)
        y -= 0.22 * inch

    # Section: Activities
    if activities.exists():
        p.setFont("Helvetica-Bold", 15)
        p.setFillColorRGB(0.1,0.2,0.4)
        p.drawString(inch, y, "Activities & Accomplishments")
        p.setFillColorRGB(0,0,0)
        y -= 0.22 * inch
        p.setFont("Helvetica", 12)
        for act in activities:
            p.drawString(inch+0.2*inch, y, f"{act.activity_name} - Type: {act.activity_type}")
            y -= 0.17 * inch
            if y < inch:
                p.showPage(); y = height - inch
        y -= 0.22 * inch
        p.setStrokeColorRGB(0.85,0.85,0.85)
        p.setLineWidth(1)
        p.line(inch, y, width-inch, y)
        y -= 0.22 * inch

    # Section: Technical Skills
    p.setFont("Helvetica-Bold", 15)
    p.setFillColorRGB(0.1,0.2,0.4)
    p.drawString(inch, y, "Technical Skills")
    p.setFillColorRGB(0,0,0)
    y -= 0.22 * inch
    p.setFont("Helvetica", 12)
    p.drawString(inch+0.2*inch, y, "Programming Languages: Python, Java, HTML/CSS, etc.")
    y -= 0.35 * inch

    p.save()
    return response

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# NAAC PDF Report Download View
def download_naac_report(request):

    faculty_email = request.session.get("faculty_email")
    if not faculty_email:
        return HttpResponse("Unauthorized", status=403)


    # Example: Generate NAAC report for all students and their approved items
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="naac_report.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - inch

    p.setFont("Helvetica-Bold", 22)
    p.setFillColorRGB(0.1,0.2,0.4)
    p.drawString(inch, y, "NAAC Report - Approved Items")
    y -= 0.45 * inch
    p.setStrokeColorRGB(0.15,0.15,0.5)
    p.setLineWidth(2)
    p.line(inch, y, width-inch, y)
    y -= 0.35 * inch

    students = Student.objects.all()
    for student in students:
        p.setFont("Helvetica-Bold", 16)
        p.setFillColorRGB(0,0,0)
        p.drawString(inch, y, f"{student.first_name} {student.last_name} ({student.branch})")
        y -= 0.22 * inch
        p.setFont("Helvetica", 12)
        p.drawString(inch, y, f"Email: {student.email} | Phone: {student.contact}")
        y -= 0.22 * inch

        # Certificates
        certs = Certificate.objects.filter(student_email=student, status="approved")
        if certs.exists():
            p.setFont("Helvetica-Bold", 13)
            p.drawString(inch, y, "Certificates:")
            y -= 0.18 * inch
            p.setFont("Helvetica", 11)
            for cert in certs:
                p.drawString(inch+0.2*inch, y, f"{cert.certificate_name} from {cert.organization} ({cert.issue_date.year})")
                y -= 0.16 * inch
                if y < inch:
                    p.showPage(); y = height - inch
            y -= 0.12 * inch

        # Projects
        projects = Projects.objects.filter(student_email=student, status="approved")
        if projects.exists():
            p.setFont("Helvetica-Bold", 13)
            p.drawString(inch, y, "Projects:")
            y -= 0.18 * inch
            p.setFont("Helvetica", 11)
            for proj in projects:
                p.drawString(inch+0.2*inch, y, f"{proj.project_name} - Subject: {proj.subject}")
                y -= 0.16 * inch
                if y < inch:
                    p.showPage(); y = height - inch
            y -= 0.12 * inch

        # Activities
        acts = Activities.objects.filter(student_email=student, status="approved")
        if acts.exists():
            p.setFont("Helvetica-Bold", 13)
            p.drawString(inch, y, "Activities:")
            y -= 0.18 * inch
            p.setFont("Helvetica", 11)
            for act in acts:
                p.drawString(inch+0.2*inch, y, f"{act.activity_name} - Type: {act.activity_type}")
                y -= 0.16 * inch
                if y < inch:
                    p.showPage(); y = height - inch
            y -= 0.12 * inch

        # Separator line between students
        p.setStrokeColorRGB(0.7,0.7,0.7)
        p.setLineWidth(1)
        p.line(inch, y, width-inch, y)
        y -= 0.22 * inch
        if y < inch:
            p.showPage(); y = height - inch

    p.save()
    return response

def login_student(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            student = Student.objects.get(email=email, password=password)

            request.session["student_email"] = student.email  

            messages.success(request, f"Welcome {student.first_name}!")
            return redirect("stu_dashboard")
        except Student.DoesNotExist:
            messages.error(request, "Invalid email or password")
    return render(request, 'student_login.html')

def stu_myactivity(request):
    """
    Handles both displaying and adding student activities.
    - On GET: Fetches all activities, projects, and certificates,
      combines them into a single list, sorts by date, and displays them.
    - On POST: Handles the submission from the unified "Add New Activity" form,
      creates the correct type of activity, and redirects back to the page.
    """
    student_email = request.session.get("student_email")
    if not student_email:
        messages.error(request, "You must be logged in to view this page.")
        return redirect("login_student")
    
    try:
        # Get the student object associated with the logged-in user
        student = Student.objects.get(email=student_email)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found. Please log in again.")
        return redirect("login_student")

    # --- Handle Form Submission (POST Request) ---
    if request.method == "POST":
        category = request.POST.get("activity_type")
        title = request.POST.get("title")
        activity_date = request.POST.get("date")

        try:
            # Create a Certificate if that was the chosen category
            if category == "certificate":
                Certificate.objects.create(
                    student_email=student,
                    certificate_name=title,
                    organization=request.POST.get("organization"),
                    issue_date=activity_date,
                    document=request.FILES.get("document") # Use request.FILES for file uploads
                )
            
            # Create a Project
            elif category == "project":
                Projects.objects.create(
                    student_email=student,
                    project_name=title,
                    subject=request.POST.get("subject"),
                    date=activity_date,
                    project_url=request.POST.get("project_url")
                )

            # Create an "Other Activity"
            elif category == "activity":
                Activities.objects.create(
                    student_email=student,
                    activity_name=title,
                    subject=request.POST.get("activity_subject"),
                    activity_type=request.POST.get("activity_type_name"),
                    date=activity_date,
                    project_url=request.POST.get("activity_url")
                )

            messages.success(request, f"Successfully added '{title}' to your activities!")
        except Exception as e:
            # Catch potential errors during database creation
            messages.error(request, f"There was an error adding your activity: {e}")
        
        # Redirect back to the same page to show the updated list
        return redirect("stu_myactivity")

    # --- Display Activities (GET Request) ---
    activities_list = []

    # 1. Fetch Certificates
    for c in Certificate.objects.filter(student_email=student):
        activities_list.append({
            "title": c.certificate_name, "organization": c.organization, "date": c.issue_date,
            "description": f"Certificate issued by {c.organization}", "category": "Certificate",
            "url": c.document.url if c.document else None, "status": c.status,
        })

    # 2. Fetch Projects
    for p in Projects.objects.filter(student_email=student):
        activities_list.append({
            "title": p.project_name, "organization": p.subject, "date": p.date,
            "description": f"Project related to {p.subject}", "category": "Project",
            "url": p.project_url, "status": p.status,
        })

    # 3. Fetch Other Activities
    for a in Activities.objects.filter(student_email=student):
        activities_list.append({
            "title": a.activity_name, "organization": a.subject, "date": a.date,
            "description": f"Activity type: {a.activity_type}", "category": "Activity",
            "url": a.project_url, "status": a.status,
        })

    # Sort the combined list by date, with the newest items first
    # Use 'date.min' as a fallback for any items that might not have a date
    activities_list.sort(key=lambda x: x["date"] or date.min, reverse=True)

    # Pass the final list to the template for rendering
    context = {
        "student": student,
        "activities": activities_list
    }
    return render(request, "stu-myactivity.html", context)


def stu_portfolio(request):
    """
    Handles displaying the student's portfolio page, including all data
    needed for the stat cards and the dynamic CV generation modal.
    """
    # 1. AUTHENTICATION: Ensure a student is logged in
    student_email = request.session.get("student_email")
    if not student_email:
        messages.error(request, "Please log in to view your portfolio.")
        return redirect("login_student")

    try:
        student = Student.objects.get(email=student_email)
    except Student.DoesNotExist:
        messages.error(request, "Student not found. Please log in again.")
        return redirect("login_student")

    # 2. FETCH DATA: Get all approved activities for the student
    approved_certs = Certificate.objects.filter(student_email=student, status="approved")
    approved_projects = Projects.objects.filter(student_email=student, status="approved")
    approved_activities = Activities.objects.filter(student_email=student, status="approved")

    # 3. CALCULATE STATS: Compute the numbers for the top cards
    total_activities_count = (
        approved_certs.count() +
        approved_projects.count() +
        approved_activities.count()
    )

    total_credits = (
        approved_certs.aggregate(total=Coalesce(Sum('credit'), 0))['total'] +
        approved_projects.aggregate(total=Coalesce(Sum('credit'), 0))['total'] +
        approved_activities.aggregate(total=Coalesce(Sum('credit'), 0))['total']
    )

    # Calculate the number of categories the student is active in
    category_count = 0
    if approved_certs.exists():
        category_count += 1
    if approved_projects.exists():
        category_count += 1
    if approved_activities.exists():
        category_count += 1

    # Determine a grade based on a simple credit threshold
    overall_grade = "N/A"
    if total_credits >= 150:
        overall_grade = "A+"
    elif total_credits >= 120:
        overall_grade = "A"
    elif total_credits >= 90:
        overall_grade = "B+"
    elif total_credits >= 60:
        overall_grade = "B"
    elif total_credits > 0:
        overall_grade = "C"
    latest_result = Results.objects.filter(student_email=student).order_by('-semester').first()
    latest_cgpa = latest_result.cgpa if latest_result else 0.0 

    # 4. PREPARE CONTEXT: Package all data to send to the template
    context = {
        'student': student,
        'total_activities': total_activities_count,
        'total_credits': total_credits,
        'category_count': category_count,
        'overall_grade': overall_grade,
        
        # Counts for the portfolio preview list
        'cert_count': approved_certs.count(),
        'proj_count': approved_projects.count(),
        'other_activities_count': approved_activities.count(),
        
        # Detailed lists of approved items for the dynamic CV modal
        'approved_certificates': approved_certs,
        'approved_projects': approved_projects,
        'approved_activities': approved_activities,
        'latest_cgpa': latest_cgpa,
    }
    
    return render(request, 'stu-portfolio.html', context)
    
    

def stu_scoreboard(request):
    student_email = request.session.get("student_email")
    if not student_email:
        return redirect("login_student")
    
    try:
        student = Student.objects.get(email=student_email)
    except Student.DoesNotExist:
        return redirect("login_student")

    # --- 1. Get Approved Items ---
    approved_certs = Certificate.objects.filter(student_email=student, status="approved")
    approved_projects = Projects.objects.filter(student_email=student, status="approved")
    approved_activities = Activities.objects.filter(student_email=student, status="approved")
    
    # --- 2. Calculate Overall Stats & Class Rank ---
    total_credits = (
        approved_certs.aggregate(sum=Coalesce(Sum('credit'), 0))['sum'] +
        approved_projects.aggregate(sum=Coalesce(Sum('credit'), 0))['sum'] +
        approved_activities.aggregate(sum=Coalesce(Sum('credit'), 0))['sum']
    )
    total_activities_count = approved_certs.count() + approved_projects.count() + approved_activities.count()

    # IMPORTANT: Ensure the related_names in your models match the names used here.
    # For example, in your Certificate model, the ForeignKey to Student should have related_name='certificate'.
    students_with_credits = Student.objects.annotate(
        total_credits=Coalesce(Sum('certificates__credit', filter=Q(certificates__status='approved')), 0) +
                      Coalesce(Sum('projects__credit', filter=Q(projects__status='approved')), 0) +
                      Coalesce(Sum('activities__credit', filter=Q(activities__status='approved')), 0)
    ).order_by('-total_credits')

    class_rank = 0
    # Find the student's rank in the ordered list
    for i, s in enumerate(students_with_credits):
        if s.email == student.email:
            class_rank = i + 1
            break
            
    total_students = Student.objects.count()
    class_avg_credits = students_with_credits.aggregate(avg=Avg('total_credits'))['avg']
    if class_avg_credits is None:
        class_avg_credits = 0.0
    
    # --- CORRECTED FORMULA for "Top %" ---
    # Top % means: what percent of students have less or equal credits than this student
    # Example: If class_rank=1, student is top 1 out of N, so top 100%. If class_rank=N, student is last, so top 1%.
    rank_top_percent = ((total_students - class_rank + 1) / total_students) * 100 if total_students > 0 else 0

    # --- 3. Data for the Four Detailed Cards ---
    detail_card_data = {}
    # (The rest of this section is unchanged)
    detail_card_data['certificates'] = {
        'count': approved_certs.count(),
        'credits': approved_certs.aggregate(sum=Coalesce(Sum('credit'), 0))['sum'],
        'recent_items': approved_certs.order_by('-issue_date')[:4]
    }
    detail_card_data['projects'] = {
        'count': approved_projects.count(),
        'credits': approved_projects.aggregate(sum=Coalesce(Sum('credit'), 0))['sum'],
        'recent_items': approved_projects.order_by('-date')[:4]
    }
    detail_card_data['activities'] = {
        'count': approved_activities.count(),
        'credits': approved_activities.aggregate(sum=Coalesce(Sum('credit'), 0))['sum'],
        'recent_items': approved_activities.order_by('-date')[:4]
    }
    student_results = Results.objects.filter(student_email=student).order_by('-semester')
    latest_result = student_results.first()
    detail_card_data['results'] = {
        'cgpa': latest_result.cgpa if latest_result else 0.0,
        'sgpa': latest_result.sgpa if latest_result else 0.0,
        'recent_items': student_results[:4]
    }

    # --- 4. Calculate Attendance ---
    all_attendance_records = Attendance.objects.filter(student=student)
    attended_classes = all_attendance_records.filter(status='Present').count()
    total_classes = all_attendance_records.count()
    
    if total_classes > 0:
        percentage = round((attended_classes / total_classes) * 100, 1)
        absent_classes = total_classes - attended_classes
    else:
        percentage = 0
        absent_classes = 0

    attendance_data = {
        'percentage': percentage,
        'attended': attended_classes,
        'absent': absent_classes
    }

    # --- 5. Build Final Context ---
    context = {
        'student': student,
        'total_credits': total_credits,
        'total_activities': total_activities_count,
        'class_rank': class_rank,
        'total_students': total_students,
        'class_avg_credits': class_avg_credits,
        'rank_top_percent': rank_top_percent,
        'detail_card_data': detail_card_data,
        'attendance_data': attendance_data,
    }
    return render(request, 'stu-scoreboard.html', context)


# Student logout
def logout_student(request):
    try:
        request.session.flush()
        messages.success(request, "You have been logged out successfully.")
    except Exception as e:
        messages.error(request, "An error occurred while logging out.")
    return redirect("first")

# Faculty logout
def logout_faculty(request):
    try:
        request.session.flush()
        messages.success(request, "You have been logged out successfully.")
    except Exception as e:
        messages.error(request, "An error occurred while logging out.")
    return redirect("first")

def login_faculty(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        try:
            faculty = Faculty.objects.get(email=email, password=password)

            request.session["faculty_email"] = faculty.email  

            messages.success(request, f"Welcome {faculty.first_name}!")
            return redirect("faculty_dashboard")
        except Faculty.DoesNotExist:
            messages.error(request, "Invalid email or password")
    return render(request, 'facul_login.html')


def faculty_dashboard(request):
    faculty_email = request.session.get("faculty_email")
    if not faculty_email:
        messages.error(request, "Please log in as a faculty member.")
        return redirect("login_student") 

    try:
        faculty = Faculty.objects.get(email=faculty_email)
    except Faculty.DoesNotExist:
        messages.error(request, "Faculty profile not found.")
        return redirect("login_student")

    faculty_department = faculty.department

    # --- 1. Calculate Stats for the Cards (Now Filtered) ---
    pending_count = (
        Certificate.objects.filter(status="pending", student_email__branch=faculty_department).count() + # <-- FILTER ADDED
        Projects.objects.filter(status="pending", student_email__branch=faculty_department).count() +    # <-- FILTER ADDED
        Activities.objects.filter(status="pending", student_email__branch=faculty_department).count()  # <-- FILTER ADDED
    )
    student_count = Student.objects.filter(branch=faculty_department).count() # <-- FILTER ADDED

    verified_count = (
        Certificate.objects.filter(status="approved", student_email__branch=faculty_department).count() + # <-- FILTER ADDED
        Projects.objects.filter(status="approved", student_email__branch=faculty_department).count() +    # <-- FILTER ADDED
        Activities.objects.filter(status="approved", student_email__branch=faculty_department).count()  # <-- FILTER ADDED
    )

    # --- 2. Calculate System Alerts (Now Filtered) ---
    two_days_ago = timezone.now().date() - timedelta(days=2)
    high_priority_alert_count = (
        Certificate.objects.filter(status="pending", issue_date__lt=two_days_ago, student_email__branch=faculty_department).count() + # <-- FILTER ADDED
        Projects.objects.filter(status="pending", date__lt=two_days_ago, student_email__branch=faculty_department).count() +    # <-- FILTER ADDED
        Activities.objects.filter(status="pending", date__lt=two_days_ago, student_email__branch=faculty_department).count()  # <-- FILTER ADDED
    )

    # --- 3. Fetch Recent Submissions (Now Filtered) ---
    all_submissions = []
    
    # Get and standardize data only from students in the faculty's department
    certs = Certificate.objects.filter(student_email__branch=faculty_department).order_by('-issue_date') # <-- FILTER ADDED
    for cert in certs:
        all_submissions.append({
            'student_name': f"{cert.student_email.first_name} {cert.student_email.last_name or ''}",
            'student_initials': f"{cert.student_email.first_name[0]}{(cert.student_email.last_name[0] if cert.student_email.last_name else '')}",
            'title': cert.certificate_name,
            'date': cert.issue_date,
            'status': cert.status,
            'type': 'Certificate'
        })
    
    # Do the same for Projects and Activities
    projects = Projects.objects.filter(student_email__branch=faculty_department).order_by('-date') # <-- FILTER ADDED
    for proj in projects:
        all_submissions.append({
            'student_name': f"{proj.student_email.first_name} {proj.student_email.last_name or ''}",
            'student_initials': f"{proj.student_email.first_name[0]}{(proj.student_email.last_name[0] if proj.student_email.last_name else '')}",
            'title': proj.project_name,
            'date': proj.date,
            'status': proj.status,
            'type': 'Project'
        })

    activities = Activities.objects.filter(student_email__branch=faculty_department).order_by('-date') # <-- FILTER ADDED
    for act in activities:
         all_submissions.append({
            'student_name': f"{act.student_email.first_name} {act.student_email.last_name or ''}",
            'student_initials': f"{act.student_email.first_name[0]}{(act.student_email.last_name[0] if act.student_email.last_name else '')}",
            'title': act.activity_name,
            'date': act.date,
            'status': act.status,
            'type': 'Activity'
        })

    all_submissions.sort(key=lambda x: x['date'], reverse=True)
    recent_submissions = all_submissions[:5]

    # --- 4. Prepare Context for the Template ---
    context = {
        'faculty': faculty,
        'pending_count': pending_count,
        'student_count': student_count,
        'verified_count': verified_count,
        'high_priority_alert_count': high_priority_alert_count,
        'recent_submissions': recent_submissions,
    }

    return render(request, 'dash_faculty.html', context)



def faculty_approvals(request):
    # --- Authentication ---
    faculty_email = request.session.get("faculty_email")
    if not faculty_email:
        messages.error(request, "Please log in as a faculty member to view this page.")
        return redirect("login_student")

    try:
        faculty = Faculty.objects.get(email=faculty_email)
    except Faculty.DoesNotExist:
        messages.error(request, "Faculty profile not found.")
        return redirect("login_student")

    # --- Handle POST Requests (From Approve/Reject Modals) ---
    if request.method == "POST":
        activity_pk = request.POST.get('activity_pk')
        model_type = request.POST.get('model_type')
        action = request.POST.get('action') # This will be 'approve' or 'reject'

        model_map = {
            'certificate': Certificate,
            'project': Projects,
            'activity': Activities
        }
        Model = model_map.get(model_type)

        if not Model or not activity_pk:
            messages.error(request, "Invalid submission data.")
            return redirect('faculty_approvals')

        try:
            # Get the specific activity object
            activity = Model.objects.get(pk=activity_pk)

            if action == 'approve':
                # Get credit points and remark from the form
                credit_points = request.POST.get('credit_points', 0)
                remark = request.POST.get('remark', '')

                activity.status = 'approved'
                activity.credit = int(credit_points)
                activity.remark = remark
                messages.success(request, f"Activity '{activity}' has been approved.")

            elif action == 'reject':
                # Get the mandatory reason from the form
                remark = request.POST.get('remark')
                if not remark:
                    messages.error(request, "A reason is required to reject an activity.")
                    return redirect('faculty_approvals')

                activity.status = 'rejected'
                activity.credit = 0 # Reset credits on rejection
                activity.remark = remark
                messages.success(request, f"Activity '{activity}' has been rejected.")

            activity.save() # Save the changes to the database

        except Model.DoesNotExist:
            messages.error(request, "The activity you tried to update was not found.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid credit points value provided.")
            
        # Redirect back to the approvals page, preserving the current filter
        current_filter = request.GET.get('status', 'all')
        return redirect(f"{request.path}?status={current_filter}")


    # --- Handle GET Requests (Displaying the list) ---
    faculty_department = faculty.department
    status_filter = request.GET.get('status', 'all')

    # Base querysets filtered by department
    certs_qs = Certificate.objects.filter(student_email__branch=faculty_department)
    proj_qs = Projects.objects.filter(student_email__branch=faculty_department)
    act_qs = Activities.objects.filter(student_email__branch=faculty_department)

    # Apply the status filter if one is selected
    if status_filter in ['pending', 'approved', 'rejected']:
        certs_qs = certs_qs.filter(status=status_filter)
        proj_qs = proj_qs.filter(status=status_filter)
        act_qs = act_qs.filter(status=status_filter)

    # Combine the filtered results into a single list
    combined_list = []
    
    for item in certs_qs:
        combined_list.append({
            'pk': item.pk, 'model_type': 'certificate', 'title': item.certificate_name, 
            'student': item.student_email, 'date': item.issue_date, 'credit': item.credit, 
            'url': item.document.url if item.document else None, 'submission_date': item.submission_date, 
            'status': item.status, 'remark': item.remark
        })
    for item in proj_qs:
        combined_list.append({
            'pk': item.pk, 'model_type': 'project', 'title': item.project_name, 
            'student': item.student_email, 'date': item.date, 'credit': item.credit, 
            'url': item.project_url, 'submission_date': item.submission_date, 
            'status': item.status, 'remark': item.remark
        })
    for item in act_qs:
        combined_list.append({
            'pk': item.pk, 'model_type': 'activity', 'title': item.activity_name,
            'student': item.student_email, 'date': item.date, 'credit': item.credit,
            'url': item.project_url, 'submission_date': item.submission_date, 
            'status': item.status, 'remark': item.remark
        })
    
    # Sort the final list
    if combined_list:
        combined_list.sort(key=lambda x: x.get('submission_date') or date.min, reverse=True)

    from django.core.paginator import Paginator
    paginator = Paginator(combined_list, 10)  # Show 10 activities per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'faculty': faculty,
        'activity_list': combined_list,
        'active_filter': status_filter,
        'page_obj': page_obj,
    }
    return render(request, 'fac_approval.html', context)





def fac_reports(request):
    faculty_email = request.session.get("faculty_email")
    faculty = None
    if faculty_email:
        try:
            faculty = Faculty.objects.get(email=faculty_email)
        except Faculty.DoesNotExist:
            faculty = None
    return render(request, 'fac_reports.html', {"faculty": faculty})



# In student/views.py

# Faculty: List students by branch (for facu_students.html)
from django.http import JsonResponse

def faculty_students(request):
    faculty_email = request.session.get("faculty_email")
    debug_msg = ""
    if not faculty_email:
        debug_msg = "No faculty_email in session."
        return render(request, "facu_students.html", {"students": [], "debug_msg": debug_msg})
    try:
        faculty = Faculty.objects.get(email=faculty_email)
    except Faculty.DoesNotExist:
        debug_msg = f"Faculty not found for email: {faculty_email}"
        return render(request, "facu_students.html", {"students": [], "debug_msg": debug_msg})
    branch = faculty.department
    students = Student.objects.filter(branch=branch)
    student_data = []
    for student in students:
        activities_count = Activities.objects.filter(student_email=student, status='approved').count()
        credits = (
            Certificate.objects.filter(student_email=student, status='approved').aggregate(sum=Coalesce(Sum('credit'), 0))["sum"] +
            Projects.objects.filter(student_email=student, status='approved').aggregate(sum=Coalesce(Sum('credit'), 0))["sum"] +
            Activities.objects.filter(student_email=student, status='approved').aggregate(sum=Coalesce(Sum('credit'), 0))["sum"]
        )
        attended_classes = Attendance.objects.filter(student=student, status='Present').count()
        total_classes = Attendance.objects.filter(student=student).count()
        attendance_percent = round((attended_classes / total_classes) * 100, 1) if total_classes else 0
        student_data.append({
            "student": student,
            "activities_count": activities_count,
            "credits": credits,
            "attendance_percent": attendance_percent,
        })
    if not students.exists():
        debug_msg = f"No students found for branch: {branch}"
    context = {
        "students": student_data,
        "faculty": faculty,
        "debug_msg": debug_msg,
    }
    return render(request, "facu_students.html", context)

# API: Get individual student profile data (AJAX)
def get_student_profile(request):
    email = request.GET.get("email")
    if not email:
        return JsonResponse({"error": "No email provided"}, status=400)
    try:
        student = Student.objects.get(email=email)
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)
    # Example: Attendance, activities, certificates, projects, results
    attended_classes = Attendance.objects.filter(student=student, status='Present').count()
    total_classes = Attendance.objects.filter(student=student).count()
    attendance_percent = round((attended_classes / total_classes) * 100, 1) if total_classes else 0
    activities = list(Activities.objects.filter(student_email=student).values('activity_name', 'activity_type', 'date'))
    certificates = list(Certificate.objects.filter(student_email=student, status='approved').values('certificate_name', 'organization', 'issue_date'))
    projects = list(Projects.objects.filter(student_email=student, status='approved').values('project_name', 'subject', 'date'))
    latest_result = Results.objects.filter(student_email=student).order_by('-semester').first()
    cgpa = latest_result.cgpa if latest_result else 0.0
    # Social links
    linkedin = student.linkedin_url or ""
    github = student.github_url or ""
    # Compose response
    data = {
        "name": f"{student.first_name} {student.last_name or ''}",
        "initials": f"{student.first_name[0]}{(student.last_name[0] if student.last_name else '')}",
        "department": student.branch,
        "email": student.email,
        "contact": student.contact,
        "cgpa": cgpa,
        "attendance": attendance_percent,
        "attended_classes": attended_classes,
        "total_classes": total_classes,
        "activities": activities,
        "certificates": certificates,
        "projects": projects,
        "linkedin": linkedin,
        "github": github,
        "college": student.College_name,
        "session": student.session,
    }
    return JsonResponse(data)
def student_results(request):
    student_email = request.session.get("student_email")
    if not student_email:
        return redirect("login_student")

    try:
        student = Student.objects.get(email=student_email)
    except Student.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect("login_student")

    if request.method == "POST":
        semester = request.POST.get('semester')
        sgpa = request.POST.get('sgpa')
        cgpa = request.POST.get('cgpa')
        document = request.FILES.get('document')

        # Add this check to ensure a file was uploaded
        if not document:
            messages.error(request, "A result document is required. Please upload a file.")
            # Redirect back to the results page to show the error
            return redirect('student_results')

        # Create the new result object in the database
        Results.objects.create(
            student_email=student,
            semester=semester,
            sgpa=sgpa,
            cgpa=cgpa,
            document=document
        )
        messages.success(request, f"Result for Semester {semester} has been added successfully!")
        return redirect('student_results')

    # --- Display Data (GET Request) ---
    # Get all results for the student, newest first
    results = Results.objects.filter(student_email=student).order_by('-semester')
    
    # Get the CGPA from the most recent semester
    current_cgpa = results.first().cgpa if results.exists() else 0.0

    # Prepare data for the bar chart (oldest first)
    # Prepare data for the bar chart (oldest first)
    chart_data = []
    # Get results sorted by semester for the chart
    results_for_chart = results.order_by('semester')

    for result in results_for_chart:
        chart_data.append({
            'semester': result.semester,
            'cgpa': result.cgpa,
            'bar_height': result.cgpa * 10  # Calculate height (e.g., 8.6 CGPA -> 86%)
        })

    context = {
        'student': student,
        'results': results,          # For the semester boxes (newest first)
        'current_cgpa': current_cgpa,
        'chart_data': chart_data,    # For the trend chart (oldest first)
    }
    
    return render(request, 'stu-result.html', context)

def register_facu(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        gender = request.POST.get("gender")
        contact = request.POST.get("contact")
        department = request.POST.get("department")
        College = request.POST.get("College")
        city = request.POST.get("city")
        state = request.POST.get("state")

        if Faculty.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register_faculty")

        Faculty.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            gender=gender,
            contact=contact,
            department=department,
            College_name=College,
            city=city,
            state=state
        )
        messages.success(request, "Registration successful. Please log in.")
        return redirect("login_faculty") 

    return render(request, 'register_facu.html')

def register_student(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        date_of_birth = request.POST.get("date_of_birth")
        gender = request.POST.get("gender")
        rollno = request.POST.get("rollno")
        contact = request.POST.get("contact")
        branch = request.POST.get("branch")
        session = request.POST.get("session")
        degree = request.POST.get("degree")
        College = request.POST.get("College")
        city = request.POST.get("city")
        state = request.POST.get("state")
        
        if Student.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register_student")
        
        Student.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            dateofbirth=date_of_birth,
            gender = gender,
            roll_no = rollno,
            contact=contact,
            branch=branch,
            session=session,
            degree=degree,
            College_name=College,
            city=city,
            state=state
        )
        messages.success(request, "Registration successful. Please log in.")
        return redirect("login_student")
    return render(request, 'register_student.html')

def student_profile_view(request):
    # Assuming you get the student's email from the session or request
    student_email = request.session.get('user_email')

    try:
        student = Student.objects.get(email=student_email)
        full_name = f"{student.first_name} {student.last_name}"
    except Student.DoesNotExist:
        full_name = "Student not found"

    context = {
        'student_name': full_name
    }
    return render(request, 'student_profile.html',context)

from .utils import get_student_name_by_email
def dashboard_view(request):
    # Retrieve the email from the user's session after they log in
    current_user_email = request.session.get('student_email')
    
    # Use the utility function to get the student's full name
    student_name = get_student_name_by_email(current_user_email)

    context = {
        'student_name': student_name,
        # Other data like attendance stats, etc.
    }
    
    return render(request, 'attendance.html',context)

def stu_dashboard(request):
    """
    Provides the data for the main student dashboard, including stats
    and a list of recent activities.
    """
    # --- 1. Get the logged-in student ---
    student_email = request.session.get("student_email")
    if not student_email:
        # Redirect to login if the user is not logged in
        return redirect("login_student") 
    
    try:
        student = Student.objects.get(email=student_email)
    except Student.DoesNotExist:
        # Log out or handle the case where the student profile is not found
        return redirect("login_student")

    # --- 2. Query all items for the student ---
    # --- 2. Query all items for the student (all statuses) ---
    certificates = Certificate.objects.filter(student_email=student)
    projects = Projects.objects.filter(student_email=student)
    activities = Activities.objects.filter(student_email=student)

    # --- 3. Calculate Overall Stats ---
    total_credits = (
        certificates.filter(status="approved").aggregate(sum=Coalesce(Sum('credit'), 0))["sum"] +
        projects.filter(status="approved").aggregate(sum=Coalesce(Sum('credit'), 0))["sum"] +
        activities.filter(status="approved").aggregate(sum=Coalesce(Sum('credit'), 0))["sum"]
    )
    completed_activities = certificates.filter(status="approved").count() + projects.filter(status="approved").count() + activities.filter(status="approved").count()
    pending_activities = (
        certificates.filter(status="pending").count() +
        projects.filter(status="pending").count() +
        activities.filter(status="pending").count()
    )
    certificates_earned = certificates.filter(status="approved").count()

    # --- 4. Get Recent Activities (all statuses) ---
    recent_items = []
    for cert in certificates.order_by('-issue_date')[:5]:
        recent_items.append({
            'title': cert.certificate_name,
            'status': cert.status,
            'credit': cert.credit
        })
    for proj in projects.order_by('-date')[:5]:
        recent_items.append({
            'title': proj.project_name,
            'status': proj.status,
            'credit': proj.credit
        })
    for act in activities.order_by('-date')[:5]:
        recent_items.append({
            'title': act.activity_name,
            'status': act.status,
            'credit': act.credit
        })
    # Sort by date/issue_date
    def get_activity_date(x):
        obj = None
        # Find the object in certificates, projects, or activities
        cert_obj = certificates.filter(certificate_name=x['title']).first()
        if cert_obj:
            obj = cert_obj
            return getattr(obj, 'issue_date', None)
        proj_obj = projects.filter(project_name=x['title']).first()
        if proj_obj:
            obj = proj_obj
            return getattr(obj, 'date', None)
        act_obj = activities.filter(activity_name=x['title']).first()
        if act_obj:
            obj = act_obj
            return getattr(obj, 'date', None)
        return None
    recent_items.sort(key=get_activity_date, reverse=True)
    recent_items = recent_items[:3]

    # --- 5. Build the context dictionary ---
    context = {
        'student': student,
        'total_credits': total_credits,
        'completed_activities': completed_activities,
        'pending_activities': pending_activities,
        'certificates_earned': certificates_earned,
        'recent_activities': recent_items,
    }
    return render(request, 'stu-dashboard.html', context)

    
# def stu_dashboard(request):
#     """
#     Provides data for the main student dashboard, including stats and recent activities.
#     """
#     student_email = request.session.get("student_email")
#     if not student_email:
#         return redirect("login_student")
#     try:
#         student = Student.objects.get(email=student_email)
#     except Student.DoesNotExist:
#         return redirect("login_student")

#     # Query all items for the student (all statuses)
#     certificates = Certificate.objects.filter(student_email=student)
#     projects = Projects.objects.filter(student_email=student)
#     activities = Activities.objects.filter(student_email=student)

#     # Calculate Overall Stats
#     total_credits = (
#         certificates.filter(status="approved").aggregate(sum=Coalesce(Sum('credit'), 0))["sum"] +
#         projects.filter(status="approved").aggregate(sum=Coalesce(Sum('credit'), 0))["sum"] +
#         activities.filter(status="approved").aggregate(sum=Coalesce(Sum('credit'), 0))["sum"]
#     )
#     completed_activities = certificates.filter(status="approved").count() + projects.filter(status="approved").count() + activities.filter(status="approved").count()
#     pending_activities = (
#         certificates.filter(status="pending").count() +
#         projects.filter(status="pending").count() +
#         activities.filter(status="pending").count()
#     )
#     certificates_earned = certificates.filter(status="approved").count()

#     # Get Recent Activities (all statuses)
#     recent_items = []
#     # Note: Using your defined related_name from models.py
#     for item in student.certificates.order_by('-submission_date')[:5]:
#         recent_items.append(item)
#     for item in student.projects.order_by('-submission_date')[:5]:
#         recent_items.append(item)
#     for item in student.activities.order_by('-submission_date')[:5]:
#         recent_items.append(item)
    
#     # Sort the combined list by submission date
#     recent_items.sort(key=lambda x: x.submission_date, reverse=True)
#     recent_activities = recent_items[:4] # Get the top 4 overall

#     context = {
#         'student': student,
#         'total_credits': total_credits,
#         'completed_activities': completed_activities,
#         'pending_activities': pending_activities,
#         'certificates_earned': certificates_earned,
#         'recent_activities': recent_activities, # Pass the sorted model objects directly
#     }
#     return render(request, 'stu-dashboard.html', context)
