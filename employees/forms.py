from django import forms
from .models import Company, Employee

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'code', 'description', 'is_active',
            'work_start_time', 'work_end_time', 'timezone'
        ]
        # widgets = {
        #     'work_start_time': forms.TimeInput(attrs={'type': 'time'}),
        #     'work_end_time': forms.TimeInput(attrs={'type': 'time'}),
        #     'description': forms.Textarea(attrs={'rows': 3}),
        # }

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'user', 'employee_id', 'full_name', 'phone',
            'company', 'position', 'department', 'manager',
            'work_type', 'employment_status', 
            'work_start_time', 'work_end_time',
            'hire_date', 'termination_date'
        ]
        # widgets = {
        #     'work_start_time': forms.TimeInput(attrs={'type': 'time'}),
        #     'work_end_time': forms.TimeInput(attrs={'type': 'time'}),
        #     'hire_date': forms.DateInput(attrs={'type': 'date'}),
        #     'termination_date': forms.DateInput(attrs={'type': 'date'}),
        #     'phone': forms.TextInput(),
        # }