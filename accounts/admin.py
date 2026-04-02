from django.contrib import admin
from .models import CRF, CRFField, CRFSubmission


@admin.register(CRF)
class CRFAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CRFField)
class CRFFieldAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'field_label', 'field_type', 'crf', 'field_order', 'is_required']
    list_filter = ['field_type', 'is_required', 'crf']
    search_fields = ['field_name', 'field_label']
    list_editable = ['field_order', 'is_required']


@admin.register(CRFSubmission)
class CRFSubmissionAdmin(admin.ModelAdmin):
    list_display = ['crf', 'submitted_by', 'submitted_at']
    list_filter = ['crf', 'submitted_at']
    search_fields = ['submitted_by__username', 'crf__name']
    readonly_fields = ['submitted_at']
