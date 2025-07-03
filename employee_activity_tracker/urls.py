"""
URL configuration for employee_activity_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponseRedirect


def root_redirect(request):
    """Smart redirect from root URL"""
    # If user is not authenticated, go to login
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/auth/login/')
    
    # If user is authenticated, go to dashboard (dashboard will handle employee profile logic)
    return HttpResponseRedirect('/dashboard/')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('activities/', include('activities.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('', root_redirect, name='root'),  # Redirect root to dashboard
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
