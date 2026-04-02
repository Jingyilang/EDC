from django.urls import path
from . import views

urlpatterns = [
    # 登录注册相关
    path('login/', views.custom_login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.user_logout, name='logout'),
    
    # 普通用户
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    
    # Superuser CRF管理
    path('crf/', views.crf_list, name='crf_list'),
    path('crf/create/', views.crf_create, name='crf_create'),
    path('crf/<int:pk>/edit/', views.crf_edit, name='crf_edit'),
    path('crf/<int:pk>/delete/', views.crf_delete, name='crf_delete'),
    path('crf/<int:pk>/fields/', views.crf_fields, name='crf_fields'),
    path('crf/<int:pk>/fields/add/', views.crf_field_add, name='crf_field_add'),
    path('crf/<int:pk>/fields/<int:field_pk>/edit/', views.crf_field_edit, name='crf_field_edit'),
    path('crf/<int:pk>/fields/<int:field_pk>/delete/', views.crf_field_delete, name='crf_field_delete'),
    
    # 用户数据填写
    path('crf/<int:pk>/fill/', views.crf_fill, name='crf_fill'),
    path('submission/<int:submission_pk>/withdraw/', views.crf_withdraw_submission, name='crf_withdraw_submission'),
    
    # 数据查看和导出
    path('crf/<int:pk>/submissions/', views.crf_submissions, name='crf_submissions'),
    path('crf/<int:pk>/submissions/<int:submission_pk>/', views.crf_submission_detail, name='crf_submission_detail'),
    path('crf/<int:pk>/export/', views.crf_export, name='crf_export'),
]
