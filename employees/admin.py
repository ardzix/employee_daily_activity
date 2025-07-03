from django.contrib import admin
from .models import Company, Employee


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'work_start_time', 'work_end_time', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        ('Work Hours', {
            'fields': ('work_start_time', 'work_end_time', 'timezone')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_id', 'user', 'company', 'position', 'employment_status', 'hire_date')
    list_filter = ('employment_status', 'work_type', 'company', 'hire_date')
    search_fields = ('full_name', 'employee_id', 'user__email', 'user__sso_id', 'position')
    ordering = ('full_name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'employee_id', 'full_name', 'phone')
        }),
        ('Company & Position', {
            'fields': ('company', 'position', 'department', 'manager')
        }),
        ('Work Configuration', {
            'fields': ('work_type', 'employment_status', 'work_start_time', 'work_end_time')
        }),
        ('Dates', {
            'fields': ('hire_date', 'termination_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        # Sync with Django User model
        if obj.user:
            if obj.full_name:
                name_parts = obj.full_name.split(' ')
                obj.user.first_name = name_parts[0]
                obj.user.last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            obj.user.save()
        
        super().save_model(request, obj, form, change)
