from django.urls import path
from . import views

urlpatterns = [
    path('', views.first, name="first"),
    path('home/', views.stu_dashboard, name="stu_dashboard"),
    #path('register/', views.register_student, name="register_student"),
    path('login_student/', views.login_student, name="login_student"),
    path('myactivity/', views.stu_myactivity, name="stu_myactivity"),
    path('portfolio/', views.stu_portfolio, name="stu_portfolio"),
    path('scoreboard/', views.stu_scoreboard, name="stu_scoreboard"),
    path('logout_student/', views.logout_student, name="logout_student"),
    path('logout_faculty/', views.logout_faculty, name="logout_faculty"),
    path('login_faculty/', views.login_faculty, name="login_faculty"),
    path('faculty_dashboard/', views.faculty_dashboard, name="faculty_dashboard"),
    path('faculty_approvals/', views.faculty_approvals, name='faculty_approvals'),
    path('faculty_students/', views.faculty_students, name='faculty_students'),
    path('fac_reports/', views.fac_reports, name='fac_reports'),
    path('results/', views.student_results, name='student_results'),
    path('download_naac_report/', views.download_naac_report, name='download_naac_report'),
    path('download_cv_pdf/', views.download_cv_pdf, name='download_cv_pdf'),
    path('register_facu/', views.register_facu, name='register_facu'),
    path('register_student/', views.register_student, name='register_student'),
    path('attendance/', views.attendance_dashboard, name='attendance_dashboard'),
    path('get_student_profile/', views.get_student_profile, name='get_student_profile'),
    path('download_student_profile_pdf/', views.download_student_profile_pdf, name='download_student_profile_pdf'),
]