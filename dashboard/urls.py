from django.urls import path
from . import views

app_name = 'dashboard'
 
urlpatterns = [
    path('', views.index_view, name='index'),
    path('admin/', views.admin_dashboard_view, name='admin'),
    path('export/', views.export_admin_dashboard, name='export_admin_dashboard'),
    path(
        'tiles/<int:z>/<int:x>/<int:y>.png',
        views.osm_tile_proxy,
        name='osm_tile',
    ),
] 