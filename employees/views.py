from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from datetime import date
from .models import Company, Employee
from activities.models import DailyActivity
from django.contrib.auth import get_user_model
from .forms import CompanyForm, EmployeeForm

def is_admin_or_hr(user):
    """Check if user is admin or HR"""
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin_or_hr)
def company_list(request):
    companies = Company.objects.all()
    return render(request, 'company/company_list.html', {'companies': companies})

@login_required
@user_passes_test(is_admin_or_hr)
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('employee:company_list')
    else:
        form = CompanyForm()
    return render(request, 'company/company_form.html', {'form': form})

@login_required
@user_passes_test(is_admin_or_hr)
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('employee:company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'company/company_form.html', {'form': form, 'object': company})

@login_required
@user_passes_test(is_admin_or_hr)
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        company.delete()
        return redirect('employee:company_list')
    return render(request, 'company/company_confirm_delete.html', {'object': company})



@login_required
@user_passes_test(is_admin_or_hr)
def employee_list(request):
    employees = Employee.objects.all()
    return render(request, 'employee/employee_list.html', {'employees': employees})

@login_required
@user_passes_test(is_admin_or_hr)
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee_instance = form.save(commit=False)

            if not employee_instance.work_start_time:
                employee_instance.work_start_time = employee_instance.company.work_start_time
                
            if not employee_instance.work_end_time:
                employee_instance.work_end_time = employee_instance.company.work_end_time
                
            employee_instance.save()
            return redirect('employee:employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'employee/employee_form.html', {'form': form})

@login_required
@user_passes_test(is_admin_or_hr)
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            employee_instance = form.save(commit=False)

            if not employee_instance.work_start_time:
                employee_instance.work_start_time = employee_instance.company.work_start_time
                
            if not employee_instance.work_end_time:
                employee_instance.work_end_time = employee_instance.company.work_end_time
                
            employee_instance.save()
            return redirect('employee:employee_list')
    else:
        form = EmployeeForm(instance=employee)
    
    return render(request, 'employee/employee_form.html', {
        'form': form,
        'object': employee
    })

@login_required
@user_passes_test(is_admin_or_hr)
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        return redirect('employee:employee_list')
    return render(request, 'employee/employee_confirm_delete.html', {'object': employee})


@login_required
@user_passes_test(is_admin_or_hr)
def daily_summary_view(request, activity_id=None):
    """Display daily activity summary - can show today's or a specific activity"""
    if activity_id:
        # Show specific activity
        daily_activity = get_object_or_404(
            DailyActivity.objects.prefetch_related(
                'planned_activities', 'daily_goals', 'additional_activities', 'goals'
            ),
            id=activity_id
        )
    else:
        # Show today's activity
        today = date.today()
        try:
            daily_activity = DailyActivity.objects.prefetch_related(
                'planned_activities', 'daily_goals', 'additional_activities', 'goals'
            ).get(id=activity_id, date=today)
        except DailyActivity.DoesNotExist:
            # No activity for today, redirect to check-in
            return redirect('activities:check_in')
    
    context = {
        'user': daily_activity.user,
        'daily_activity': daily_activity,
        'goals': daily_activity.goals.all(),
        'planned_activities': daily_activity.planned_activities.all(),
        'daily_goals': daily_activity.daily_goals.all(),
        'additional_activities': daily_activity.additional_activities.all(),
        'can_check_in': not daily_activity.checkin_time and daily_activity.date == date.today(),
        'can_check_out': daily_activity.checkin_time and not daily_activity.checkout_time and daily_activity.date == date.today(),
        'has_employee_profile': hasattr(request.user, 'employee_profile'),
    }
    
    return render(request, 'activities/daily_summary.html', context)