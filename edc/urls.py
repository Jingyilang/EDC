"""
URL configuration for edc project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('czy-edc-2026/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', RedirectView.as_view(url='login/', permanent=False), name='home'),
]
