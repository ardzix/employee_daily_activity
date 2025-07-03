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
    date_filter = request.GET.get('date_range', 'week')
    
    # Base queryset
    activities_qs = DailyActivity.objects.all()
    employees_qs = Employee.objects.filter(employment_status='active')
    
    # Apply company filter
    if company_filter:
        activities_qs = activities_qs.filter(user__employee_profile__company_id=company_filter)
        employees_qs = employees_qs.filter(company_id=company_filter)
    
    # Apply date filter
    if date_filter == 'today':
        activities_qs = activities_qs.filter(date=today)
    elif date_filter == 'week':
        activities_qs = activities_qs.filter(date__gte=this_week_start)
    elif date_filter == 'month':
        activities_qs = activities_qs.filter(date__gte=this_month_start)
    
    # Calculate statistics
    total_employees = employees_qs.count()
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
    
    # Companies for filter
    companies = Company.objects.filter(is_active=True)
    
    context = {
        'today_stats': today_stats,
        'attendance_stats': attendance_stats,
        'recent_activities': recent_activities,
        'late_today': late_today,
        'absent_today': absent_today,
        'companies': companies,
        'selected_company': company_filter,
        'selected_date_range': date_filter,
        'total_employees': total_employees,
        'total_active_users': total_active_users,
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)
