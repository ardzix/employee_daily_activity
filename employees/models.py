from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


class Company(models.Model):
    """Client company model"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=10, unique=True, help_text="Short code for the company")
    description = models.TextField(blank=True, null=True)
    
    # Work hours configuration
    work_start_time = models.TimeField(default='09:00', help_text="Default work start time")
    work_end_time = models.TimeField(default='17:00', help_text="Default work end time")
    
    # Timezone
    timezone = models.CharField(
        max_length=50, 
        default='Asia/Jakarta',
        help_text="Company timezone"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Employee(models.Model):
    """Employee profile model - OneToOne with User"""
    
    EMPLOYMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]
    
    WORK_TYPE_CHOICES = [
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ]
    
    # Link to Custom User (OneToOneField)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    
    # Basic Information
    employee_id = models.CharField(
        max_length=20, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9]+$', 'Employee ID must contain only uppercase letters and numbers')]
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Company Assignment
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    
    # Work Configuration
    work_type = models.CharField(max_length=10, choices=WORK_TYPE_CHOICES, default='onsite')
    employment_status = models.CharField(max_length=15, choices=EMPLOYMENT_STATUS_CHOICES, default='active')
    
    # Work Hours (can override company defaults)
    work_start_time = models.TimeField(blank=True, null=True, help_text="Leave blank to use company default")
    work_end_time = models.TimeField(blank=True, null=True, help_text="Leave blank to use company default")
    
    # Position and Department
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    # Manager
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='subordinates')
    
    # Dates
    hire_date = models.DateField()
    termination_date = models.DateField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"
    
    @property
    def effective_work_start_time(self):
        """Return work start time, using company default if not set"""
        return self.work_start_time or self.company.work_start_time
    
    @property
    def effective_work_end_time(self):
        """Return work end time, using company default if not set"""
        return self.work_end_time or self.company.work_end_time
    
    @property
    def is_active_employee(self):
        """Check if employee is currently active"""
        return self.employment_status == 'active'
