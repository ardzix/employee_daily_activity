from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, datetime, timedelta
from activities.models import DailyActivity
from employees.models import Employee, Company
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
# import datetime
import pytz

User = get_user_model()


def is_admin_or_hr(user):
    """Check if user is admin or HR"""
    return user.is_staff or user.is_superuser


@login_required
def index_view(request):
    """Main dashboard view - works with or without employee profile"""
    today = date.today()
    
    # Get today's activity for the user
    today_activity = DailyActivity.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    # Get recent activities
    recent_activities = DailyActivity.objects.filter(
        user=request.user
    ).order_by('-date')[:7]
    
    # Calculate stats
    this_week_start = today - timedelta(days=today.weekday())
    this_week_activities = DailyActivity.objects.filter(
        user=request.user,
        date__gte=this_week_start
    )
    
    stats = {
        'total_activities': recent_activities.count(),
        'completed_this_week': this_week_activities.filter(status='completed').count(),
        'on_time_this_week': this_week_activities.filter(attendance_status='on_time').count(),
        'late_this_week': this_week_activities.filter(attendance_status='late').count(),
    }
    
    # Check if user has employee profile
    has_employee_profile = hasattr(request.user, 'employee_profile')
    
    context = {
        'user': request.user,
        'today_activity': today_activity,
        'recent_activities': recent_activities,
        'stats': stats,
        'is_admin': is_admin_or_hr(request.user),
        'has_employee_profile': has_employee_profile,
    }
    
    if has_employee_profile:
        context['employee'] = request.user.employee_profile
        return render(request, 'dashboard/employee_dashboard.html', context)
    else:
        context['message'] = 'Welcome! Your employee profile is being set up by HR. You can still clock in/out.'
        return render(request, 'dashboard/simple_dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_hr)
def admin_dashboard_view(request):
    """Admin dashboard with analytics"""
    
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday())
    this_month_start = today.replace(day=1)
    
    # Get filter parameters
    company_filter = request.GET.get('company', '')
    employee_filter = request.GET.get('employee', '')
    date_filter = request.GET.get('date_range', 'week')
    
    # Base queryset
    activities_qs = DailyActivity.objects.all()
    employees_qs = Employee.objects.filter(employment_status='active')
    
    # Apply company filter
    if company_filter:
        activities_qs = activities_qs.filter(user__employee_profile__company_id=company_filter)
        employees_qs = employees_qs.filter(company_id=company_filter)
    
    # Apply employee filter
    if employee_filter:
        activities_qs = activities_qs.filter(user__employee_profile__id=employee_filter)
    
    # Apply date filter
    if date_filter == 'today':
        activities_qs = activities_qs.filter(date=today)
    elif date_filter == 'week':
        activities_qs = activities_qs.filter(date__gte=this_week_start)
    elif date_filter == 'month':
        activities_qs = activities_qs.filter(date__gte=this_month_start)
    
    # Calculate statistics
    total_employees = employees_qs.count()
    
    # Calculate total active users based on filters
    if company_filter:
        total_active_users = User.objects.filter(
            is_active=True,
            employee_profile__company_id=company_filter
        ).count()
    else:
        total_active_users = User.objects.filter(is_active=True).count()
    
    # Today's attendance
    today_activities = activities_qs.filter(date=today)
    today_stats = {
        'total_expected': total_active_users,
        'checked_in': today_activities.filter(checkin_time__isnull=False).count(),
        'checked_out': today_activities.filter(checkout_time__isnull=False).count(),
        'on_time': today_activities.filter(attendance_status='on_time').count(),
        'late': today_activities.filter(attendance_status='late').count(),
        'absent': total_active_users - today_activities.filter(checkin_time__isnull=False).count(),
    }
    
    # Attendance trends
    attendance_stats = activities_qs.aggregate(
        total_activities=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        on_time=Count('id', filter=Q(attendance_status='on_time')),
        late=Count('id', filter=Q(attendance_status='late')),
        absent=Count('id', filter=Q(attendance_status='absent')),
    )
    
    # Recent activities
    recent_activities = activities_qs.order_by('-date', '-checkin_time')[:20]
    
    # Late arrivals today
    late_today = today_activities.filter(attendance_status='late').select_related('user')
    
    # Absent users today
    checked_in_user_ids = today_activities.filter(
        checkin_time__isnull=False
    ).values_list('user_id', flat=True)
    
    absent_today = User.objects.filter(is_active=True).exclude(id__in=checked_in_user_ids)
    
    if company_filter:
        absent_today = absent_today.filter(
            employee_profile__company_id=company_filter
        )
    
    if employee_filter:
        absent_today = absent_today.filter(
            employee_profile__id=employee_filter
        )
    
    # Companies for filter
    companies = Company.objects.filter(is_active=True)
    
    # Prepare context
    context = {
        'today_stats': today_stats,
        'attendance_stats': attendance_stats,
        'recent_activities': recent_activities,
        'late_today': late_today,
        'absent_today': absent_today,
        'companies': companies,
        'employees': employees_qs,  # For employee filter dropdown
        'selected_company': company_filter,
        'selected_employee': employee_filter,  # To keep selected employee in filter
        'selected_date_range': date_filter,
        'total_employees': total_employees,
        'total_active_users': total_active_users,
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)

# @login_required
# @user_passes_test(is_admin_or_hr)
# def export_admin_dashboard(request):
#     """Export filtered dashboard data to Excel"""
    
#     # Get filter parameters
#     company_filter = request.GET.get('company', '')
#     employee_filter = request.GET.get('employee', '')
#     date_filter = request.GET.get('date_range', 'week')
    
#     # Timezone for GMT+7
#     tz = pytz.timezone('Asia/Jakarta')  # GMT+7
    
#     # Base queryset
#     activities_qs = DailyActivity.objects.all()
#     employees_qs = Employee.objects.filter(employment_status='active')
    
#     # Apply company filter
#     if company_filter:
#         activities_qs = activities_qs.filter(user__employee_profile__company_id=company_filter)
#         employees_qs = employees_qs.filter(company_id=company_filter)
    
#     # Apply employee filter
#     if employee_filter:
#         activities_qs = activities_qs.filter(user__employee_profile__id=employee_filter)
    
#     # Apply date filter
#     today = date.today()
#     this_week_start = today - timedelta(days=today.weekday())
#     this_month_start = today.replace(day=1)
    
#     if date_filter == 'today':
#         activities_qs = activities_qs.filter(date=today)
#     elif date_filter == 'week':
#         activities_qs = activities_qs.filter(date__gte=this_week_start)
#     elif date_filter == 'month':
#         activities_qs = activities_qs.filter(date__gte=this_month_start)
    
#     # Calculate statistics (same as dashboard)
#     total_employees = employees_qs.count()
    
#     if company_filter:
#         total_active_users = User.objects.filter(
#             is_active=True,
#             employee_profile__company_id=company_filter
#         ).count()
#     else:
#         total_active_users = User.objects.filter(is_active=True).count()
    
#     # Today's attendance
#     today_activities = activities_qs.filter(date=today)
#     today_stats = {
#         'total_expected': total_active_users,
#         'checked_in': today_activities.filter(checkin_time__isnull=False).count(),
#         'checked_out': today_activities.filter(checkout_time__isnull=False).count(),
#         'on_time': today_activities.filter(attendance_status='on_time').count(),
#         'late': today_activities.filter(attendance_status='late').count(),
#         'absent': total_active_users - today_activities.filter(checkin_time__isnull=False).count(),
#     }
    
#     # Attendance trends
#     attendance_stats = activities_qs.aggregate(
#         total_activities=Count('id'),
#         completed=Count('id', filter=Q(status='completed')),
#         on_time=Count('id', filter=Q(attendance_status='on_time')),
#         late=Count('id', filter=Q(attendance_status='late')),
#         absent=Count('id', filter=Q(attendance_status='absent')),
#     )
    
#     # Completion rate
#     completion_rate = 0.0
#     if attendance_stats['total_activities'] and attendance_stats['completed']:
#         completion_rate = (attendance_stats['completed'] / attendance_stats['total_activities']) * 100
    
#     # Late today
#     late_today = today_activities.filter(attendance_status='late').select_related('user')
    
#     # Absent today
#     checked_in_user_ids = today_activities.filter(
#         checkin_time__isnull=False
#     ).values_list('user_id', flat=True)
    
#     absent_today = User.objects.filter(is_active=True).exclude(id__in=checked_in_user_ids)
#     if company_filter:
#         absent_today = absent_today.filter(
#             employee_profile__company_id=company_filter
#         )
#     if employee_filter:
#         absent_today = absent_today.filter(
#             employee_profile__id=employee_filter
#         )
    
#     # Recent activities
#     recent_activities = activities_qs.order_by('-date', '-checkin_time')
    
#     # Create workbook with multiple sheets
#     wb = Workbook()
    
#     # Sheet 1: Dashboard Summary
#     ws_summary = wb.active
#     ws_summary.title = "Dashboard Summary"
    
#     # Write summary header
#     ws_summary.append(["ADMIN DASHBOARD EXPORT"])
#     ws_summary.append([f"Exported at: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')}"])
#     ws_summary.append([f"Filters: Company={company_filter}, Employee={employee_filter}, Date Range={date_filter}"])
#     ws_summary.append([])
    
#     # Write summary cards data
#     ws_summary.append(["SUMMARY STATISTICS"])
#     ws_summary.append(["Metric", "Value"])
#     ws_summary.append(["Total Employees", total_employees])
#     ws_summary.append(["Total Active Users", total_active_users])
#     ws_summary.append(["Today's Attendance", f"{today_stats['checked_in']}/{today_stats['total_expected']}"])
#     ws_summary.append(["On Time Today", today_stats['on_time']])
#     ws_summary.append(["Late Today", today_stats['late']])
#     ws_summary.append(["Absent Today", today_stats['absent']])
#     ws_summary.append(["Completed Activities", attendance_stats['completed']])
#     ws_summary.append(["Total Activities", attendance_stats['total_activities']])
#     ws_summary.append(["Completion Rate", f"{completion_rate:.2f}%"])
#     ws_summary.append(["On Time Total", attendance_stats['on_time']])
#     ws_summary.append(["Late Total", attendance_stats['late']])
#     ws_summary.append([])
    
#     # Sheet 2: Late Arrivals Today
#     ws_late = wb.create_sheet("Late Today")
#     ws_late.append(["LATE ARRIVALS TODAY"])
#     ws_late.append(["Employee", "Position", "Company", "Check-in Time (GMT+7)"])
    
#     for activity in late_today:
#         checkin_time_str = ""
#         if activity.checkin_time:
#             # PERBAIKAN: Gunakan time() untuk mendapatkan waktu saja
#             if isinstance(activity.checkin_time, datetime):
#                 # Jika sudah datetime, langsung konversi
#                 localized_time = activity.checkin_time.astimezone(tz)
#                 checkin_time_str = localized_time.strftime('%Y-%m-%d %H:%M:%S')
#             else:
#                 # Jika masih time, gabungkan dengan tanggal
#                 naive_datetime = datetime.combine(activity.date, activity.checkin_time)
#                 localized_time = tz.localize(naive_datetime)
#                 checkin_time_str = localized_time.strftime('%Y-%m-%d %H:%M:%S')
#         else:
#             checkin_time_str = "N/A"
        
#         employee = activity.user.employee_profile
#         ws_late.append([
#             activity.user.get_full_name() or activity.user.username,
#             employee.position if employee else "N/A",
#             employee.company.name if (employee and employee.company) else "N/A",
#             checkin_time_str
#         ])
    
#     # Sheet 3: Absent Today
#     ws_absent = wb.create_sheet("Absent Today")
#     ws_absent.append(["ABSENT EMPLOYEES TODAY"])
#     ws_absent.append(["Employee", "Position", "Company"])
    
#     for user in absent_today:
#         employee = user.employee_profile
#         ws_absent.append([
#             user.get_full_name() or user.username,
#             employee.position if employee else "N/A",
#             employee.company.name if (employee and employee.company) else "N/A"
#         ])
    
#     # Sheet 4: Activity Details
#     ws_activities = wb.create_sheet("Activity Details")
#     headers = [
#         "Employee", "Position", "Company", "Date",
#         "Check In (GMT+7)", "Check Out (GMT+7)", 
#         "Status", "Attendance Status", "Hours Worked", "Notes"
#     ]
#     ws_activities.append(headers)
    
#     for activity in recent_activities:
#         # Handle check-in time
#         checkin_str = ""
#         if activity.checkin_time:
#             if isinstance(activity.checkin_time, datetime):
#                 # Jika sudah datetime, langsung konversi
#                 localized_in = activity.checkin_time.astimezone(tz)
#                 checkin_str = localized_in.strftime('%Y-%m-%d %H:%M:%S')
#             else:
#                 # Jika masih time, gabungkan dengan tanggal
#                 naive_in = datetime.combine(activity.date, activity.checkin_time)
#                 localized_in = tz.localize(naive_in)
#                 checkin_str = localized_in.strftime('%Y-%m-%d %H:%M:%S')
#         else:
#             checkin_str = "N/A"
        
#         # Handle check-out time
#         checkout_str = ""
#         if activity.checkout_time:
#             if isinstance(activity.checkout_time, datetime):
#                 # Jika sudah datetime, langsung konversi
#                 localized_out = activity.checkout_time.astimezone(tz)
#                 checkout_str = localized_out.strftime('%Y-%m-%d %H:%M:%S')
#             else:
#                 # Jika masih time, gabungkan dengan tanggal
#                 naive_out = datetime.combine(activity.date, activity.checkout_time)
#                 localized_out = tz.localize(naive_out)
#                 checkout_str = localized_out.strftime('%Y-%m-%d %H:%M:%S')
#         else:
#             checkout_str = "N/A"
        
#         # Calculate hours worked
#         hours_worked = "N/A"
#         if activity.checkin_time and activity.checkout_time:
#             # Gunakan versi yang sudah dikonversi untuk perhitungan
#             start_dt = None
#             end_dt = None
            
#             if isinstance(activity.checkin_time, datetime):
#                 start_dt = activity.checkin_time.astimezone(tz)
#             else:
#                 naive_in = datetime.combine(activity.date, activity.checkin_time)
#                 start_dt = tz.localize(naive_in)
            
#             if isinstance(activity.checkout_time, datetime):
#                 end_dt = activity.checkout_time.astimezone(tz)
#             else:
#                 naive_out = datetime.combine(activity.date, activity.checkout_time)
#                 end_dt = tz.localize(naive_out)
            
#             # Handle overnight case
#             if end_dt < start_dt:
#                 end_dt += datetime.timedelta(days=1)
            
#             delta = end_dt - start_dt
#             total_seconds = delta.total_seconds()
#             hours = int(total_seconds // 3600)
#             minutes = int((total_seconds % 3600) // 60)
#             hours_worked = f"{hours}h {minutes}m"
        
#         employee = activity.user.employee_profile
#         row = [
#             activity.user.get_full_name() or activity.user.username,
#             employee.position if employee else "N/A",
#             employee.company.name if (employee and employee.company) else "N/A",
#             activity.date.strftime("%Y-%m-%d"),
#             checkin_str,
#             checkout_str,
#             activity.get_status_display(),
#             activity.get_attendance_status_display(),
#             hours_worked,
#             activity.notes or ""
#         ]
#         ws_activities.append(row)
    
#     # Apply styling to all sheets
#     header_fill = PatternFill(start_color="2D6099", end_color="2D6099", fill_type="solid")
#     header_font = Font(bold=True, color="FFFFFF")
#     thin_border = Border(
#         left=Side(style='thin'),
#         right=Side(style='thin'),
#         top=Side(style='thin'),
#         bottom=Side(style='thin')
#     )
    
#     for ws in wb.worksheets:
#         # Apply header styling to the first row
#         for row in ws.iter_rows(min_row=1, max_row=1):
#             for cell in row:
#                 cell.fill = header_fill
#                 cell.font = header_font
#                 cell.alignment = Alignment(horizontal='center')
        
#         # Apply borders to all cells
#         for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
#             for cell in row:
#                 cell.border = thin_border
        
#         # Auto adjust column widths
#         for col in ws.columns:
#             max_length = 0
#             column_letter = get_column_letter(col[0].column)
            
#             for cell in col:
#                 try:
#                     value = str(cell.value) if cell.value else ""
#                     if len(value) > max_length:
#                         max_length = len(value)
#                 except:
#                     pass
            
#             adjusted_width = (max_length + 2) * 1.2
#             ws.column_dimensions[column_letter].width = adjusted_width
    
#     # Create response
#     response = HttpResponse(
#         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
#     filename = f"dashboard_export_{datetime.now(tz).strftime('%Y%m%d_%H%M%S')}.xlsx"
#     response['Content-Disposition'] = f'attachment; filename={filename}'
    
#     wb.save(response)
#     return response

@login_required
@user_passes_test(is_admin_or_hr)
def export_admin_dashboard(request):
    """Export filtered dashboard data to Excel"""
    
    # Get filter parameters
    company_filter = request.GET.get('company', '')
    employee_filter = request.GET.get('employee', '')
    date_filter = request.GET.get('date_range', 'week')
    
    # Timezone for GMT+7
    tz = pytz.timezone('Asia/Jakarta')  # GMT+7
    
    # Base queryset
    activities_qs = DailyActivity.objects.all()
    employees_qs = Employee.objects.filter(employment_status='active')
    
    # Apply company filter
    if company_filter:
        activities_qs = activities_qs.filter(user__employee_profile__company_id=company_filter)
        employees_qs = employees_qs.filter(company_id=company_filter)
    
    # Apply employee filter
    if employee_filter:
        activities_qs = activities_qs.filter(user__employee_profile__id=employee_filter)
    
    # Apply date filter
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday())
    this_month_start = today.replace(day=1)
    
    if date_filter == 'today':
        activities_qs = activities_qs.filter(date=today)
    elif date_filter == 'week':
        activities_qs = activities_qs.filter(date__gte=this_week_start)
    elif date_filter == 'month':
        activities_qs = activities_qs.filter(date__gte=this_month_start)
    
    # Prefetch related data for efficiency
    activities_qs = activities_qs.prefetch_related(
        'planned_activities',
        'daily_goals',
        'additional_activities',
        'user__employee_profile'
    )
    
    # Calculate statistics (same as dashboard)
    total_employees = employees_qs.count()
    
    if company_filter:
        total_active_users = User.objects.filter(
            is_active=True,
            employee_profile__company_id=company_filter
        ).count()
    else:
        total_active_users = User.objects.filter(is_active=True).count()
    
    # Today's attendance
    today_activities = activities_qs.filter(date=today)
    today_stats = {
        'total_expected': total_active_users,
        'checked_in': today_activities.filter(checkin_time__isnull=False).count(),
        'checked_out': today_activities.filter(checkout_time__isnull=False).count(),
        'on_time': today_activities.filter(attendance_status='on_time').count(),
        'late': today_activities.filter(attendance_status='late').count(),
        'absent': total_active_users - today_activities.filter(checkin_time__isnull=False).count(),
    }
    
    # Attendance trends
    attendance_stats = activities_qs.aggregate(
        total_activities=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        on_time=Count('id', filter=Q(attendance_status='on_time')),
        late=Count('id', filter=Q(attendance_status='late')),
        absent=Count('id', filter=Q(attendance_status='absent')),
    )
    
    # Completion rate
    completion_rate = 0.0
    if attendance_stats['total_activities'] and attendance_stats['completed']:
        completion_rate = (attendance_stats['completed'] / attendance_stats['total_activities']) * 100
    
    # Late today
    late_today = today_activities.filter(attendance_status='late').select_related('user')
    
    # Absent today
    checked_in_user_ids = today_activities.filter(
        checkin_time__isnull=False
    ).values_list('user_id', flat=True)
    
    absent_today = User.objects.filter(is_active=True).exclude(id__in=checked_in_user_ids)
    
    current_company = "All"
    current_employee = "All"
    
    if company_filter:
        absent_today = absent_today.filter(
            employee_profile__company_id=company_filter
        )
        current_company = Company.objects.get(id=company_filter)
    if employee_filter:
        absent_today = absent_today.filter(
            employee_profile__id=employee_filter
        )
        current_employee = Employee.objects.get(id=employee_filter)
    
    # Recent activities
    recent_activities = activities_qs.order_by('-date', '-checkin_time')
    
    # Create workbook with multiple sheets
    wb = Workbook()
    
    # Sheet 1: Dashboard Summary
    ws_summary = wb.active
    ws_summary.title = "Dashboard Summary"
    
    # Write summary header
    ws_summary.append(["ADMIN DASHBOARD EXPORT"])
    ws_summary.append([f"Exported at: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S %Z')}"])
    ws_summary.append([f"Filters: Company={current_company.name if isinstance(current_company, Company) else current_company}, Employee={current_employee.full_name if isinstance(current_employee, Employee) else current_employee}, Date Range={date_filter.capitalize()}"])
    ws_summary.append([])
    
    # Write summary cards data
    ws_summary.append(["SUMMARY STATISTICS"])
    ws_summary.append(["Metric", "Value"])
    ws_summary.append(["Total Employees", total_employees])
    ws_summary.append(["Total Active Users", total_active_users])
    ws_summary.append(["Today's Attendance", f"{today_stats['checked_in']}/{today_stats['total_expected']}"])
    ws_summary.append(["On Time Today", today_stats['on_time']])
    ws_summary.append(["Late Today", today_stats['late']])
    ws_summary.append(["Absent Today", today_stats['absent']])
    ws_summary.append(["Completed Activities", attendance_stats['completed']])
    ws_summary.append(["Total Activities", attendance_stats['total_activities']])
    ws_summary.append(["Completion Rate", f"{completion_rate:.2f}%"])
    ws_summary.append(["On Time Total", attendance_stats['on_time']])
    ws_summary.append(["Late Total", attendance_stats['late']])
    ws_summary.append([])
    
    # Sheet 2: Late Arrivals Today
    ws_late = wb.create_sheet("Late Today")
    ws_late.append(["LATE ARRIVALS TODAY"])
    ws_late.append(["Employee", "Position", "Company", "Check-in Time (GMT+7)"])
    
    for activity in late_today:
        checkin_time_str = ""
        if activity.checkin_time:
            # Handle both datetime and time objects
            if isinstance(activity.checkin_time, datetime):
                localized_time = activity.checkin_time.astimezone(tz)
                checkin_time_str = localized_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                naive_datetime = datetime.combine(activity.date, activity.checkin_time)
                localized_time = tz.localize(naive_datetime)
                checkin_time_str = localized_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            checkin_time_str = "N/A"
        
        employee = activity.user.employee_profile
        ws_late.append([
            activity.user.get_full_name() or activity.user.username,
            employee.position if employee else "N/A",
            employee.company.name if (employee and employee.company) else "N/A",
            checkin_time_str
        ])
    
    # Sheet 3: Absent Today
    ws_absent = wb.create_sheet("Absent Today")
    ws_absent.append(["ABSENT EMPLOYEES TODAY"])
    ws_absent.append(["Employee", "Position", "Company"])
    
    for user in absent_today:
        employee = user.employee_profile
        ws_absent.append([
            user.get_full_name() or user.username,
            employee.position if employee else "N/A",
            employee.company.name if (employee and employee.company) else "N/A"
        ])
    
    # Sheet 4: Activity Details
    ws_activities = wb.create_sheet("Activity Details")
    headers = [
        "Employee", "Position", "Company", "Date",
        "Check In (GMT+7)", "Check Out (GMT+7)", 
        "Status", "Attendance Status", "Work Duration",
        "Morning Problems", "Afternoon Problems", "Notes",
        "Planned Activities", "Activity Status", "Activity Priority", "Activity Reasons",
        "Daily Goals", "Goal Status", "Goal Priority", "Target", "Achieved", "Completion %", "Goal Reasons",
        "Additional Activities", "Add. Category", "Add. Status", "Add. Duration", "Add. Impact"
    ]
    ws_activities.append(headers)
    
    for activity in recent_activities:
        # Handle check-in time
        checkin_str = ""
        if activity.checkin_time:
            if isinstance(activity.checkin_time, datetime):
                localized_in = activity.checkin_time.astimezone(tz)
                checkin_str = localized_in.strftime('%Y-%m-%d %H:%M:%S')
            else:
                naive_in = datetime.combine(activity.date, activity.checkin_time)
                localized_in = tz.localize(naive_in)
                checkin_str = localized_in.strftime('%Y-%m-%d %H:%M:%S')
        else:
            checkin_str = "N/A"
        
        # Handle check-out time
        checkout_str = ""
        if activity.checkout_time:
            if isinstance(activity.checkout_time, datetime):
                localized_out = activity.checkout_time.astimezone(tz)
                checkout_str = localized_out.strftime('%Y-%m-%d %H:%M:%S')
            else:
                naive_out = datetime.combine(activity.date, activity.checkout_time)
                localized_out = tz.localize(naive_out)
                checkout_str = localized_out.strftime('%Y-%m-%d %H:%M:%S')
        else:
            checkout_str = "N/A"
        
        # Calculate work duration
        work_duration = "N/A"
        if activity.work_duration:
            total_seconds = activity.work_duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            work_duration = f"{hours}h {minutes}m"
        
        # Get employee profile
        employee = activity.user.employee_profile
        
        # Prepare lists for related activities
        planned_activities = list(activity.planned_activities.all())
        daily_goals = list(activity.daily_goals.all())
        additional_activities = list(activity.additional_activities.all())
        
        # Determine max rows needed for this activity
        max_rows = max(1, len(planned_activities), len(daily_goals), len(additional_activities))
        
        for i in range(max_rows):
            pa = planned_activities[i] if i < len(planned_activities) else None
            dg = daily_goals[i] if i < len(daily_goals) else None
            aa = additional_activities[i] if i < len(additional_activities) else None
            
            # Only include main activity details in first row
            if i == 0:
                row = [
                    activity.user.get_full_name() or activity.user.username,
                    employee.position if employee else "N/A",
                    employee.company.name if (employee and employee.company) else "N/A",
                    activity.date.strftime("%Y-%m-%d"),
                    checkin_str,
                    checkout_str,
                    activity.get_status_display(),
                    activity.get_attendance_status_display(),
                    work_duration,
                    activity.morning_problems or "",
                    activity.afternoon_problems or "",
                    activity.notes or ""
                ]
            else:
                # For additional rows, leave main activity details empty
                row = ["", "", "", "", "", "", "", "", "", "", "", ""]
            
            # Add planned activity details
            row.extend([
                pa.title if pa else "",
                pa.get_status_display() if pa else "",
                pa.get_priority_display() if pa else "",
                pa.reasons if pa else ""
            ])
            
            # Add daily goal details
            row.extend([
                dg.title if dg else "",
                dg.get_status_display() if dg else "",
                dg.get_priority_display() if dg else "",
                dg.target_value if dg else "",
                dg.achieved_value if dg else "",
                f"{dg.completion_percentage}%" if dg and dg.completion_percentage is not None else "",
                dg.reasons if dg else ""
            ])
            
            # Add additional activity details
            row.extend([
                aa.title if aa else "",
                aa.get_category_display() if aa else "",
                aa.get_status_display() if aa else "",
                str(aa.duration) if aa and aa.duration else "",
                aa.impact_on_planned_work if aa else ""
            ])
            
            ws_activities.append(row)
    
    # Apply styling to all sheets
    header_fill = PatternFill(start_color="2D6099", end_color="2D6099", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for ws in wb.worksheets:
        # Apply header styling to the first row
        for row in ws.iter_rows(min_row=1, max_row=1):
            for cell in row:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
        
        # Apply borders to all cells
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.border = thin_border
        
        # Auto adjust column widths
        for col in ws.columns:
            max_length = 0
            column_letter = get_column_letter(col[0].column)
            
            for cell in col:
                try:
                    value = str(cell.value) if cell.value else ""
                    if len(value) > max_length:
                        max_length = len(value)
                except:
                    pass
            
            adjusted_width = (max_length + 2) * 1.2
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    # filename = f"dashboard_export_{datetime.now(tz).strftime('%Y%m%d_%H%M%S')}.xlsx"
    filename = f"report_company({current_company.name.lower() if isinstance(current_company, Company) else current_company.lower()})_employee({current_employee.full_name.lower() if isinstance(current_employee, Employee) else current_employee.lower()})_date-range({date_filter}).xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    wb.save(response)
    return response