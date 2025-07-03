from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # The fields to be used in displaying the User model.
    list_display = ('email', 'sso_id', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'sso_id', 'first_name', 'last_name')
    ordering = ('email',)
    
    # The fieldsets to organize the User admin form
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('SSO Information', {
            'fields': ('sso_id',)
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
        ('SSO Tokens', {
            'fields': ('sso_access_token', 'sso_refresh_token', 'sso_token_expires_at'),
            'classes': ('collapse',)
        })
    )
    
    # The fieldsets to organize the add User admin form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'sso_id', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('last_login', 'date_joined')
