# events/urls.py
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('upload/', views.upload_excel_view, name='upload_excel'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('download-template/', views.download_template_view, name='download_template'), # NOUVELLE URL
]