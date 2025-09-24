# student_portal/utils.py
from .models import Student

def get_student_name_by_email(email):
    try:
        student = Student.objects.get(email=email)
        return f"{student.first_name} {student.last_name}"
    except Student.DoesNotExist:
        return None