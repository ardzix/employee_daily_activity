from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/google-login/', views.api_google_login, name='api_google_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/verify-email/', views.api_verify_email, name='api_verify_email'),
    path('api/resend-email-otp/', views.api_resend_email_otp, name='api_resend_email_otp'),
    path('api/mfa/verify/', views.mfa_verify, name='mfa_verify'),
    path('api/mfa/status/', views.api_mfa_status, name='api_mfa_status'),
    path('api/mfa/set/', views.api_mfa_set, name='api_mfa_set'),
    path('api/mfa/disable/', views.api_mfa_disable, name='api_mfa_disable'),
    path('api/passkeys/', views.api_passkeys_list, name='api_passkeys_list'),
    path('api/passkeys/register/begin/', views.api_passkeys_register_begin, name='api_passkeys_register_begin'),
    path('api/passkeys/register/complete/', views.api_passkeys_register_complete, name='api_passkeys_register_complete'),
    path('api/passkeys/<int:passkey_id>/', views.api_passkeys_delete, name='api_passkeys_delete'),
    path('api/passkeys/login/begin/', views.api_passkeys_login_begin, name='api_passkeys_login_begin'),
    path('api/passkeys/login/complete/', views.api_passkeys_login_complete, name='api_passkeys_login_complete'),
    path('api/token/refresh/', views.refresh_token_view, name='token_refresh'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
] 