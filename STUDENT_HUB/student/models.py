from django.db import models
from django.utils import timezone

# Create your models here.
class Student(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50,null=True)
    email = models.EmailField(primary_key=True,unique=True,null=False)
    password = models.CharField(max_length=16)
    dateofbirth = models.DateField(null=True)
    gender = models.CharField(max_length=10)
    roll_no = models.CharField(max_length=20,null=False)
    contact = models.CharField(max_length=12)
    branch = models.CharField(max_length=50)
    session = models.CharField(max_length=15,null=True)
    degree = models.CharField(max_length=100)
    register_date = models.DateField(auto_now_add=True)
    College_name = models.CharField(max_length=150,null=True)
    city = models.CharField(max_length=50,null=True)
    state = models.CharField(max_length=50,null=True)
    linkedin_url = models.URLField(max_length=200,null=True,blank=True)
    github_url = models.URLField(max_length=200,null=True,blank=True)
    def __str__(self):
        return self.email
    
    
class Faculty(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150,null=True)
    email = models.EmailField(unique=True,primary_key=True)
    password = models.CharField(max_length=16)
    gender = models.CharField(max_length=10)
    contact = models.CharField(max_length=12)
    department = models.CharField(max_length=50)
    register_date = models.DateField(auto_now_add=True)
    College_name = models.CharField(max_length=100,null=True)
    city = models.CharField(max_length=50,null=True)
    state = models.CharField(max_length=50,null=True)
    def __str__(self):
        return self.email
    
class Certificate(models.Model):
    certificate_name = models.CharField(max_length=100)
    student_email = models.ForeignKey(Student, verbose_name=("email"), on_delete=models.CASCADE, related_name='certificates')
    organization = models.CharField(max_length=150)
    issue_date = models.DateField()
    document = models.FileField(upload_to="certificates/",null=True,blank=True)
    status = models.CharField(default="pending")
    credit = models.IntegerField(default=0)
    submission_date = models.DateField(auto_now_add=True)
    remark = models.TextField(max_length=500)
    def __str__(self):
        return self.certificate_name
    
    
class Projects(models.Model):
    project_name = models.CharField(max_length=150)
    student_email = models.ForeignKey(Student, verbose_name=("email"), on_delete=models.CASCADE, related_name='projects')
    subject = models.CharField(max_length=200)
    date = models.DateField(null=True)
    project_url = models.URLField()
    status = models.CharField(default="pending")
    credit = models.IntegerField(default=0)
    submission_date = models.DateField(auto_now_add=True)
    remark = models.TextField(max_length=500)
    def __str__(self):
        return self.project_name
    
    
class Activities(models.Model):
    activity_name = models.CharField(max_length=150)
    student_email = models.ForeignKey(Student, verbose_name=("email"), on_delete=models.CASCADE, related_name='activities')
    subject = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=100)
    date = models.DateField(null=True)
    project_url = models.URLField(null=True,blank=True)
    status = models.CharField(default="pending")
    credit = models.IntegerField(default=0)
    submission_date = models.DateField(auto_now_add=True)
    remark = models.TextField(max_length=500)
    def __str__(self):
        return self.activity_name
    

class Results(models.Model):
    student_email = models.ForeignKey(Student, verbose_name=("email") , on_delete=models.CASCADE)
    semester = models.IntegerField()
    sgpa = models.FloatField()
    cgpa = models.FloatField()
    document = models.FileField(upload_to="results/",null=True,blank=True)
    def __str__(self):
        return self.student_email.email + " Sem:" + str(self.semester)
    
    
class Subject(models.Model):
    subject_code = models.CharField(max_length=50)
    subject_name = models.CharField(max_length=200)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    
    def _str_(self):
        return f"{self.subject_name} ({self.subject_code})"
    
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=[('Present', 'Present'), ('Absent', 'Absent')])
    
    class Meta:
        # Ensures a student's attendance is only recorded once per subject per day
        unique_together = ('student', 'subject', 'date') 
    
    def _str_(self):
        return f"{self.student.email} - {self.subject.subject_name} ({self.status}) on {self.date}"