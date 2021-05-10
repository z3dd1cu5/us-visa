"""tuixue URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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
from django.urls import path
from . import views, settings

urlpatterns = [
    path('', views.index, name='index'),
] + ([
    path('refresh/', views.refresh, name='refresh'),
    path('register/', views.register, name='register'),
    path('manage/', views.manage, name='manage'),
] if settings.CGI_CORE_API else []) + ([
    path('ais/refresh/', views.ais_refresh, name='ais_refresh'),
    path('ais/register/', views.ais_register, name='ais_register'),
] if settings.AIS_CORE_API else []) + ([
    path('ais/captcha/', views.ais_captcha, name='ais_captcha'),
] if settings.AIS_CAPTCHA_API else [])
