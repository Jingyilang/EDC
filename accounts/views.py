from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
import json
import csv
from .forms import CustomLoginForm, RegisterForm, CRFForm, CRFFieldForm, CRFDataEntryForm
from .models import CRF, CRFField, CRFSubmission


def custom_login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # 根据用户类型跳转到不同页面
            if user.is_superuser:
                return redirect('crf_list')
            else:
                return redirect('user_dashboard')
    else:
        form = CustomLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('user_dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def user_dashboard(request):
    """普通用户仪表板"""
    if request.user.is_superuser:
        return redirect('crf_list')
    
    # 获取所有启用的CRF
    crfs = CRF.objects.filter(is_active=True)
    
    # 获取用户已提交的记录
    user_submissions = CRFSubmission.objects.filter(submitted_by=request.user).select_related('crf')
    
    # 按CRF分组统计提交次数
    crf_submission_counts = {}
    for submission in user_submissions:
        if submission.crf_id not in crf_submission_counts:
            crf_submission_counts[submission.crf_id] = 0
        crf_submission_counts[submission.crf_id] += 1
    
    return render(request, 'accounts/user_dashboard.html', {
        'crfs': crfs,
        'user_submissions': user_submissions,
        'crf_submission_counts': crf_submission_counts
    })


# ==================== Superuser CRF管理视图 ====================

@login_required
def crf_list(request):
    """CRF列表（仅superuser可见）"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crfs = CRF.objects.filter(created_by=request.user)
    return render(request, 'accounts/crf_list.html', {'crfs': crfs})


@login_required
def crf_create(request):
    """创建CRF"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = CRFForm(request.POST)
        if form.save():
            return redirect('crf_list')
    else:
        form = CRFForm()
    
    return render(request, 'accounts/crf_form.html', {'form': form, 'action': '创建'})


@login_required
def crf_edit(request, pk):
    """编辑CRF"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        form = CRFForm(request.POST, instance=crf)
        if form.save():
            return redirect('crf_list')
    else:
        form = CRFForm(instance=crf)
    
    return render(request, 'accounts/crf_form.html', {'form': form, 'crf': crf, 'action': '编辑'})


@login_required
def crf_delete(request, pk):
    """删除CRF"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    if request.method == 'POST':
        crf.delete()
        return redirect('crf_list')
    
    return render(request, 'accounts/crf_confirm_delete.html', {'crf': crf})


@login_required
def crf_fields(request, pk):
    """管理CRF字段"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    fields = crf.fields.all().order_by('field_order')
    
    return render(request, 'accounts/crf_fields.html', {'crf': crf, 'fields': fields})


@login_required
def crf_field_add(request, pk):
    """添加CRF字段"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        form = CRFFieldForm(request.POST)
        if form.save():
            return redirect('crf_fields', pk=crf.pk)
    else:
        form = CRFFieldForm()
    
    return render(request, 'accounts/crf_field_form.html', {'form': form, 'crf': crf, 'action': '添加'})


@login_required
def crf_field_edit(request, pk, field_pk):
    """编辑CRF字段"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    field = get_object_or_404(CRFField, pk=field_pk, crf=crf)
    
    if request.method == 'POST':
        form = CRFFieldForm(request.POST, instance=field)
        if form.save():
            return redirect('crf_fields', pk=crf.pk)
    else:
        form = CRFFieldForm(instance=field)
    
    return render(request, 'accounts/crf_field_form.html', {'form': form, 'crf': crf, 'field': field, 'action': '编辑'})


@login_required
def crf_field_delete(request, pk, field_pk):
    """删除CRF字段"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    field = get_object_or_404(CRFField, pk=field_pk, crf=crf)
    
    if request.method == 'POST':
        field.delete()
        return redirect('crf_fields', pk=crf.pk)
    
    return render(request, 'accounts/crf_field_confirm_delete.html', {'crf': crf, 'field': field})


# ==================== 用户数据填写视图 ====================

@login_required
def crf_fill(request, pk):
    """填写CRF（用户）- 每次都是新提交"""
    if request.user.is_superuser:
        return redirect('crf_list')
    
    crf = get_object_or_404(CRF, pk=pk, is_active=True)
    
    # 检查CRF是否有字段定义
    if not crf.fields.exists():
        return render(request, 'accounts/crf_no_fields.html', {'crf': crf})
    
    if request.method == 'POST':
        form = CRFDataEntryForm(request.POST, crf=crf)
        if form.is_valid():
            # 每次都创建新提交
            CRFSubmission.objects.create(
                crf=crf,
                submitted_by=request.user,
                data=json.dumps(form.cleaned_data)
            )
            return redirect('user_dashboard')
    else:
        form = CRFDataEntryForm(crf=crf)
    
    return render(request, 'accounts/crf_fill.html', {
        'crf': crf,
        'form': form
    })


@login_required
def crf_withdraw_submission(request, submission_pk):
    """撤回单条CRF提交（用户）"""
    if request.user.is_superuser:
        return redirect('crf_list')
    
    submission = get_object_or_404(CRFSubmission, pk=submission_pk, submitted_by=request.user)
    crf = submission.crf
    
    if request.method == 'POST':
        submission.delete()
        return redirect('user_dashboard')
    
    return render(request, 'accounts/crf_withdraw_confirm.html', {
        'crf': crf,
        'submission': submission
    })


@login_required
def crf_submissions(request, pk):
    """查看CRF提交记录（superuser）"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    submissions = CRFSubmission.objects.filter(crf=crf).select_related('submitted_by')
    
    return render(request, 'accounts/crf_submissions.html', {'crf': crf, 'submissions': submissions})


@login_required
def crf_submission_detail(request, pk, submission_pk):
    """查看CRF提交详情（superuser）"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    submission = get_object_or_404(CRFSubmission, pk=submission_pk, crf=crf)
    
    # 解析JSON数据
    data = json.loads(submission.data)
    
    # 构建字段映射
    fields = {f.field_name: f for f in crf.fields.all()}
    
    return render(request, 'accounts/crf_submission_detail.html', {
        'crf': crf,
        'submission': submission,
        'data': data,
        'fields': fields
    })


@login_required
def crf_export(request, pk):
    """导出CRF数据为CSV"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    crf = get_object_or_404(CRF, pk=pk, created_by=request.user)
    submissions = CRFSubmission.objects.filter(crf=crf).select_related('submitted_by')
    
    if not submissions.exists():
        return HttpResponse("没有数据可导出", content_type="text/plain")
    
    # 创建CSV响应
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{crf.name}_数据导出.csv"'
    
    writer = csv.writer(response)
    
    # 获取字段
    fields = list(crf.fields.all().order_by('field_order'))
    
    # 写入表头
    header = ['提交ID', '提交人', '提交时间'] + [f.field_label for f in fields]
    writer.writerow(header)
    
    # 写入数据
    for submission in submissions:
        data = json.loads(submission.data)
        row = [
            submission.id,
            submission.submitted_by.username,
            submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
        ]
        for field in fields:
            row.append(data.get(field.field_name, ''))
        writer.writerow(row)
    
    return response
