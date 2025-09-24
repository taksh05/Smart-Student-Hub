from django.contrib import admin
from .models import Student , Faculty , Certificate , Projects , Activities , Results
# Register your models here.
admin.site.register(Student)
admin.site.register(Faculty)
admin.site.register(Projects)
admin.site.register(Certificate)
admin.site.register(Activities)
admin.site.register(Results)