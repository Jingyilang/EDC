from django.db import models
from django.contrib.auth.models import User


class CRF(models.Model):
    """CRF（病例报告表）模型"""
    name = models.CharField(max_length=200, verbose_name='CRF名称')
    description = models.TextField(blank=True, verbose_name='CRF描述')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_crfs', verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    
    class Meta:
        verbose_name = 'CRF'
        verbose_name_plural = 'CRF列表'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class CRFField(models.Model):
    """CRF字段定义模型"""
    FIELD_TYPES = [
        ('text', '文本输入'),
        ('number', '数字输入'),
        ('date', '日期选择'),
        ('select', '下拉选择'),
        ('textarea', '多行文本'),
        ('radio', '单选按钮'),
        ('checkbox', '多选框'),
    ]
    
    crf = models.ForeignKey(CRF, on_delete=models.CASCADE, related_name='fields', verbose_name='所属CRF')
    field_name = models.CharField(max_length=100, verbose_name='字段名称')
    field_label = models.CharField(max_length=200, verbose_name='字段标签')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, verbose_name='字段类型')
    field_order = models.IntegerField(default=0, verbose_name='字段顺序')
    is_required = models.BooleanField(default=False, verbose_name='是否必填')
    options = models.TextField(blank=True, verbose_name='选项（逗号分隔）', help_text='用于select/radio/checkbox类型，用逗号分隔各选项')
    
    class Meta:
        verbose_name = 'CRF字段'
        verbose_name_plural = 'CRF字段列表'
        ordering = ['field_order']
    
    def __str__(self):
        return f"{self.crf.name} - {self.field_label}"


class CRFSubmission(models.Model):
    """CRF数据提交记录"""
    crf = models.ForeignKey(CRF, on_delete=models.CASCADE, related_name='submissions', verbose_name='所属CRF')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crf_submissions', verbose_name='提交人')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    data = models.TextField(verbose_name='提交的JSON数据')
    
    class Meta:
        verbose_name = 'CRF提交记录'
        verbose_name_plural = 'CRF提交记录列表'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.crf.name} - {self.submitted_by.username} - {self.submitted_at}"
