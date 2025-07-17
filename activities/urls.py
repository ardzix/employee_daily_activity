from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    # List view of all activities
    path('', views.activity_list_view, name='activity_list'),
    
    # Today's activity summary (backward compatibility)
    path('daily-summary/', views.daily_summary_view, name='daily_summary'),
    
    # Detail view for specific activity (using daily_summary.html)
    path('<int:activity_id>/', views.daily_summary_view, name='daily_summary'),
    
    # Legacy URL that redirects to today's activity detail
    path('data/', views.activity_data_redirect, name='activity_data'),
    
    # Check-in and check-out
    path('check-in/', views.check_in_view, name='check_in'),
    path('check-out/', views.check_out_view, name='check_out'),

    
    # API endpoints for all users
    path('api/check-in/', views.check_in_api, name='check_in_api'),
    path('api/check-out/', views.check_out_api, name='check_out_api'),
    path('api/status/', views.activity_status_api, name='activity_status_api'),
] 