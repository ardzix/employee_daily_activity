from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from .models import Company, Employee
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