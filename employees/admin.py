from django.contrib import admin
from django.urls import path, reverse
from django.http import HttpResponse
from django.shortcuts import render
from .models import Company, Employee
import openpyxl
from datetime import datetime


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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:employee_id>/generate_report/',
                self.admin_site.admin_view(self.generate_report_view),
                name='employee-generate-report',
            ),
        ]
        return custom_urls + urls

    def generate_report_view(self, request, employee_id):
        employee = self.get_object(request, employee_id)
        from activities.models import DailyActivity
        import pytz
        from django.utils import timezone
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        if request.method == 'POST':
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            # Parse dates
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except Exception:
                return render(request, 'admin/employee_generate_report.html', {'employee': employee, 'error': 'Invalid date format.'})

            # Query all daily activities for this employee in the date range
            activities = DailyActivity.objects.filter(
                user=employee.user,
                date__gte=start_date_obj,
                date__lte=end_date_obj
            ).prefetch_related('planned_activities', 'daily_goals', 'additional_activities').order_by('date')

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=activity_report_{employee.full_name}_{start_date}_to_{end_date}.xlsx'

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Daily Activities'

            # Header
            ws.append([
                'Date', 'Status', 'Attendance', 'Check-in', 'Check-out', 'Work Duration',
                'Morning Problems', 'Afternoon Problems', 'Notes',
                'Planned Activities', 'Activity Status', 'Activity Priority', 'Activity Reasons',
                'Daily Goals', 'Goal Status', 'Goal Priority', 'Target', 'Achieved', 'Completion %', 'Goal Reasons',
                'Additional Activities', 'Add. Category', 'Add. Status', 'Add. Duration', 'Add. Impact'
            ])

            for activity in activities:
                planned_activities = list(activity.planned_activities.all())
                daily_goals = list(activity.daily_goals.all())
                additional_activities = list(activity.additional_activities.all())

                # Convert check-in/out to Asia/Jakarta
                if activity.checkin_time:
                    checkin_local = timezone.localtime(activity.checkin_time, jakarta_tz)
                    checkin_str = checkin_local.strftime('%H:%M')
                else:
                    checkin_str = ''
                if activity.checkout_time:
                    checkout_local = timezone.localtime(activity.checkout_time, jakarta_tz)
                    checkout_str = checkout_local.strftime('%H:%M')
                else:
                    checkout_str = ''

                max_rows = max(1, len(planned_activities), len(daily_goals), len(additional_activities))
                for i in range(max_rows):
                    pa = planned_activities[i] if i < len(planned_activities) else None
                    dg = daily_goals[i] if i < len(daily_goals) else None
                    aa = additional_activities[i] if i < len(additional_activities) else None
                    ws.append([
                        activity.date.strftime('%Y-%m-%d') if i == 0 else '',
                        activity.get_status_display() if i == 0 else '',
                        activity.get_attendance_status_display() if i == 0 else '',
                        checkin_str if i == 0 else '',
                        checkout_str if i == 0 else '',
                        str(activity.work_duration) if i == 0 and activity.work_duration else '',
                        activity.morning_problems if i == 0 else '',
                        activity.afternoon_problems if i == 0 else '',
                        activity.notes if i == 0 else '',
                        pa.title if pa else '',
                        pa.get_status_display() if pa else '',
                        pa.get_priority_display() if pa else '',
                        pa.reasons if pa else '',
                        dg.title if dg else '',
                        dg.get_status_display() if dg else '',
                        dg.get_priority_display() if dg else '',
                        dg.target_value if dg else '',
                        dg.achieved_value if dg else '',
                        dg.completion_percentage if dg else '',
                        dg.reasons if dg else '',
                        aa.title if aa else '',
                        aa.get_category_display() if aa else '',
                        aa.get_status_display() if aa else '',
                        str(aa.duration) if aa and aa.duration else '',
                        aa.impact_on_planned_work if aa else '',
                    ])

            wb.save(response)
            return response
        return render(request, 'admin/employee_generate_report.html', {'employee': employee})

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['generate_report_url'] = reverse(
            'admin:employee-generate-report',
            args=[object_id]
        )
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
