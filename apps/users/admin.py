from django.contrib import admin
from .models import User
from unfold.admin import ModelAdmin
# Register your models here.

@admin.register(User)
class CustomAdminClass(ModelAdmin):
    pass
