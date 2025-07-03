from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model for SSO authentication"""
    
    # SSO ID (will be used as username)
    sso_id = models.CharField(max_length=100, unique=True, help_text="SSO User ID from authentication service")
    
    # Override email to have default value
    email = models.EmailField(unique=True, help_text="Email address")
    
    # Additional fields for SSO integration
    sso_access_token = models.TextField(blank=True, null=True, help_text="Current SSO access token")
    sso_refresh_token = models.TextField(blank=True, null=True, help_text="Current SSO refresh token")
    sso_token_expires_at = models.DateTimeField(blank=True, null=True, help_text="When the SSO token expires")
    
    # Override username to use email for login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['sso_id']
    
    def save(self, *args, **kwargs):
        # Auto-generate email if not provided
        if not self.email and self.sso_id:
            self.email = f"{self.sso_id}@arnatech.id"
        
        # Set username to sso_id for consistency (username should not change)
        if self.sso_id:
            self.username = self.sso_id
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.email} ({self.sso_id})"
    
    @property
    def has_employee_profile(self):
        """Check if user has an employee profile"""
        return hasattr(self, 'employee_profile')
    
    @property
    def full_name(self):
        """Return full name or email if names not set"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.email
