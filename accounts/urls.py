from django.urls import path
from . import views

urlpatterns = [
    # 登录注册相关
    path('login/', views.custom_login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.user_logout, name='logout'),
    
    # 普通用户 - 患者提交流程
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('patient/<int:patient_submission_id>/crf/', views.patient_crf_list, name='patient_crf_list'),
    path('patient/<int:patient_submission_id>/submit/', views.patient_submit, name='patient_submit'),
    path('patient/<int:patient_submission_id>/crf/<int:crf_id>/fill/', views.crf_fill, name='crf_fill'),
    
    # Superuser CRF管理
    path('crf/', views.crf_list, name='crf_list'),
    path('crf/create/', views.crf_create, name='crf_create'),
    path('crf/<int:pk>/edit/', views.crf_edit, name='crf_edit'),
    path('crf/<int:pk>/delete/', views.crf_delete, name='crf_delete'),
    path('crf/<int:pk>/fields/', views.crf_fields, name='crf_fields'),
    path('crf/<int:pk>/fields/add/', views.crf_field_add, name='crf_field_add'),
    path('crf/<int:pk>/fields/<int:field_pk>/edit/', views.crf_field_edit, name='crf_field_edit'),
    path('crf/<int:pk>/fields/<int:field_pk>/delete/', views.crf_field_delete, name='crf_field_delete'),
    
    # 数据查看和导出（superuser）
    path('submissions/', views.crf_submissions, name='crf_submissions'),
    path('patient/<int:patient_submission_id>/detail/', views.patient_data_detail, name='patient_data_detail'),
    path('export/', views.export_all_data, name='export_all_data'),
]
