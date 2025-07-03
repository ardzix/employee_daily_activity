from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/verify-email/', views.api_verify_email, name='api_verify_email'),
    path('api/resend-email-otp/', views.api_resend_email_otp, name='api_resend_email_otp'),
    path('api/mfa/verify/', views.mfa_verify, name='mfa_verify'),
    path('api/token/refresh/', views.refresh_token_view, name='token_refresh'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
] 