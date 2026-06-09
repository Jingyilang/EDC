from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import csv
from datetime import date
from .forms import CustomLoginForm, RegisterForm, CRFForm, CRFFieldForm, CRFDataEntryForm, PatientIDForm
from .models import CRF, CRFField, CRFSubmission, PatientSubmission, CRFDraft


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
    """普通用户仪表板 - 输入患者号"""
    if request.user.is_superuser:
        return redirect('crf_list')
    
    # 获取当前用户已提交的患者记录（按提交时间排序）
    submitted_patients = PatientSubmission.objects.filter(
        submitted_by=request.user,
        is_submitted=True
    ).order_by('-submitted_at')
    
    # 已提交患者ID列表（用于快速查重）
    submitted_patient_ids = submitted_patients.values_list('patient_id', flat=True)
    
    # 获取进行中的患者记录（未提交）
    in_progress_patients = PatientSubmission.objects.filter(
        submitted_by=request.user,
        is_submitted=False
    ).order_by('-updated_at')
    
    if request.method == 'POST':
        form = PatientIDForm(request.POST)
        if form.is_valid():
            patient_id = form.cleaned_data['patient_id']
            
            # 检查该患者是否已提交
            if patient_id in submitted_patient_ids:
                return render(request, 'accounts/user_dashboard.html', {
                    'form': form,
                    'error': f'患者 {patient_id} 已提交，无法填写信息',
                    'submitted_patients': submitted_patients,
                    'in_progress_patients': in_progress_patients
                })
            
            # 检查是否已有进行中的记录，如果没有则创建
            patient_submission, created = PatientSubmission.objects.get_or_create(
                patient_id=patient_id,
                submitted_by=request.user,
                defaults={'is_submitted': False}
            )
            
            # 跳转到患者CRF填写页面
            return redirect('patient_crf_list', patient_submission_id=patient_submission.id)
    else:
        form = PatientIDForm()
    
    return render(request, 'accounts/user_dashboard.html', {
        'form': form,
        'submitted_patients': submitted_patients,
        'in_progress_patients': in_progress_patients
    })


@login_required
def patient_crf_list(request, patient_submission_id):
    """显示患者的所有CRF列表"""
    if request.user.is_superuser:
        return redirect('crf_list')
    
    patient_submission = get_object_or_404(
        PatientSubmission,
        id=patient_submission_id,
        submitted_by=request.user
    )
    
    # 如果已提交，重定向回dashboard
    if patient_submission.is_submitted:
        return redirect('user_dashboard')
    
    # 获取所有启用的CRF
    crfs = CRF.objects.filter(is_active=True)
    
    # 获取每个CRF的完成状态
    crf_status = {}
    all_completed = True
    
    for crf in crfs:
        # 检查是否有草稿
        draft = CRFDraft.objects.filter(
            patient_submission=patient_submission,
            crf=crf
        ).first()
        
        # 检查是否已提交
        submission = CRFSubmission.objects.filter(
            patient_submission=patient_submission,
            crf=crf
        ).first()
        
        if submission:
            status = 'submitted'
        elif draft:
            status = 'draft' if not draft.is_completed else 'completed'
            if not draft.is_completed:
                all_completed = False
        else:
            status = 'not_started'
            all_completed = False
        
        crf_status[crf.id] = {
            'status': status,
            'draft': draft,
            'submission': submission
        }
    
    # 检查所有必填项是否完成
    can_submit = all_completed and len(crf_status) > 0
    
    return render(request, 'accounts/patient_crf_list.html', {
        'patient_submission': patient_submission,
        'crfs': crfs,
        'crf_status': crf_status,
        'can_submit': can_submit
    })


@login_required
def patient_submit(request, patient_submission_id):
    """提交患者所有CRF"""
    if request.user.is_superuser:
        return redirect('crf_list')
    
    patient_submission = get_object_or_404(
        PatientSubmission,
        id=patient_submission_id,
        submitted_by=request.user,
        is_submitted=False
    )
    
    if request.method == 'POST':
        # 获取所有CRF
        crfs = CRF.objects.filter(is_active=True)
        
        # 检查所有CRF是否都已完成
        all_completed = True
        for crf in crfs:
            draft = CRFDraft.objects.filter(
                patient_submission=patient_submission,
                crf=crf,
                is_completed=True
            ).first()
            
            # 如果已有提交记录也算完成
            submission_exists = CRFSubmission.objects.filter(
                patient_submission=patient_submission,
                crf=crf
            ).exists()
            
            if not draft and not submission_exists:
                all_completed = False
                break
        
        if not all_completed:
            return redirect('patient_crf_list', patient_submission_id=patient_submission.id)
        
        # 将所有草稿转换为正式提交
        for crf in crfs:
            draft = CRFDraft.objects.filter(
                patient_submission=patient_submission,
                crf=crf,
                is_completed=True
            ).first()
            
            if draft:
                # 创建正式提交
                CRFSubmission.objects.create(
                    patient_submission=patient_submission,
                    crf=crf,
                    submitted_by=request.user,
                    data=draft.data
                )
                # 删除草稿
                draft.delete()
        
        # 标记患者提交为已提交
        patient_submission.is_submitted = True
        patient_submission.submitted_at = timezone.now()
        patient_submission.save()
        
        return redirect('user_dashboard')
    
    return redirect('patient_crf_list', patient_submission_id=patient_submission.id)


@login_required
def crf_fill(request, patient_submission_id, crf_id):
    """填写CRF（支持保存草稿）"""
    if request.user.is_superuser:
        return redirect('crf_list')
    
    patient_submission = get_object_or_404(
        PatientSubmission,
        id=patient_submission_id,
        submitted_by=request.user,
        is_submitted=False
    )
    
    crf = get_object_or_404(CRF, pk=crf_id, is_active=True)
    
    if not crf.fields.exists():
        return render(request, 'accounts/crf_no_fields.html', {'crf': crf})
    
    # 获取现有草稿
    draft = CRFDraft.objects.filter(
        patient_submission=patient_submission,
        crf=crf
    ).first()
    
    # 准备初始数据
    initial_data = None
    if draft:
        initial_data = json.loads(draft.data)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        form = CRFDataEntryForm(request.POST, crf=crf)
        
        # 提取所有字段的原始数据（不受验证影响）
        raw_data = {}
        for field in crf.fields.all():
            field_name = field.field_name
            if field_name in request.POST:
                values = request.POST.getlist(field_name)
                if field.field_type == 'checkbox':
                    raw_data[field_name] = values if values else []
                else:
                    raw_data[field_name] = values[0] if values else ''
        
        if action == 'save':
            # 保存草稿：不验证必填项，直接保存原始数据
            CRFDraft.objects.update_or_create(
                patient_submission=patient_submission,
                crf=crf,
                defaults={
                    'data': json.dumps(raw_data),
                    'is_completed': False
                }
            )
            
            # 用原始数据重建表单，避免渲染时触发字段验证错误
            form = CRFDataEntryForm(crf=crf, initial_data=raw_data)
            
            return render(request, 'accounts/crf_fill.html', {
                'crf': crf,
                'form': form,
                'patient_submission': patient_submission,
                'saved': True,
                'is_completed': False,
                'suppress_errors': True
            })
        
        # action == 'submit_crf'：需要验证必填项
        if form.is_valid():
            # 处理日期类型，转换为字符串
            data = {}
            for key, value in form.cleaned_data.items():
                if isinstance(value, date):
                    data[key] = value.isoformat()
                elif isinstance(value, list):
                    data[key] = value
                else:
                    data[key] = value
            
            # 检查所有必填项是否已完成
            all_completed = True
            missing_fields = []
            for field in crf.fields.all():
                if field.is_required:
                    field_value = data.get(field.field_name)
                    if not field_value or (isinstance(field_value, list) and len(field_value) == 0):
                        all_completed = False
                        missing_fields.append(field.field_label)
            
            if not all_completed:
                # 保存当前数据为草稿（保留进度），但返回错误提示
                CRFDraft.objects.update_or_create(
                    patient_submission=patient_submission,
                    crf=crf,
                    defaults={
                        'data': json.dumps(data),
                        'is_completed': False
                    }
                )
                
                return render(request, 'accounts/crf_fill.html', {
                    'crf': crf,
                    'form': form,
                    'patient_submission': patient_submission,
                    'error': f'请填写所有必填项后再提交：{", ".join(missing_fields)}'
                })
            
            # 所有必填项已完成，保存并返回
            CRFDraft.objects.update_or_create(
                patient_submission=patient_submission,
                crf=crf,
                defaults={
                    'data': json.dumps(data),
                    'is_completed': True
                }
            )
            
            return redirect('patient_crf_list', patient_submission_id=patient_submission.id)
    else:
        form = CRFDataEntryForm(crf=crf, initial_data=initial_data)
    
    return render(request, 'accounts/crf_fill.html', {
        'crf': crf,
        'form': form,
        'patient_submission': patient_submission,
        'draft': draft,
        'is_completed': draft.is_completed if draft else False
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
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = CRFForm(request.POST)
        if form.is_valid():  # ✅ 先验证表单
            crf = form.save(commit=False)   # ✅ 不立即保存
            crf.created_by = request.user   # ✅ 关键：设置创建者
            crf.save()                      # ✅ 现在保存
            
            # ✅ 自动创建患者号字段（强制）
            CRFField.objects.create(
                crf=crf,
                field_name='patient_id',
                field_label='患者号',
                field_type='text',
                field_order=0,  # 放在第一个
                is_required=True  # 必填
            )
            
            # ✅ 自动创建住院号字段（强制）
            CRFField.objects.create(
                crf=crf,
                field_name='admission_id',
                field_label='住院号',
                field_type='text',
                field_order=1,  # 放在第二个
                is_required=True  # 必填
            )
            
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
        if form.is_valid():           # ✅ 先验证表单
            field = form.save(commit=False)  # ✅ 不立即保存
            field.crf = crf           # ✅ 关键：设置所属CRF
            
            # ✅ 确保自定义字段排在患者号和住院号之后（从第3位开始）
            # 患者号=0，住院号=1，自定义字段最小为2
            if field.field_order < 2:
                field.field_order = 2
            
            field.save()              # ✅ 现在保存
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
    
    # 保护默认字段：患者号和住院号不允许修改 field_name 和 field_label
    is_protected_field = field.field_name in ['patient_id', 'admission_id']
    
    if request.method == 'POST':
        form = CRFFieldForm(request.POST, instance=field)
        if form.is_valid():
            edited_field = form.save(commit=False)
            
            # ✅ 确保自定义字段排在患者号和住院号之后（从第3位开始）
            # 患者号=0，住院号=1，自定义字段最小为2
            if edited_field.field_name not in ['patient_id', 'admission_id']:
                if edited_field.field_order < 2:
                    edited_field.field_order = 2
            
            edited_field.save()
            return redirect('crf_fields', pk=crf.pk)
    else:
        form = CRFFieldForm(instance=field)
    
    return render(request, 'accounts/crf_field_form.html', {
        'form': form, 
        'crf': crf, 
        'field': field, 
        'action': '编辑',
        'is_protected_field': is_protected_field
    })


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


# ==================== 数据查看和导出视图 ====================

@login_required
def crf_submissions(request):
    """查看所有患者提交记录（superuser）"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    submissions = PatientSubmission.objects.filter(
        is_submitted=True
    ).select_related('submitted_by').order_by('-submitted_at')
    
    return render(request, 'accounts/crf_submissions.html', {
        'submissions': submissions
    })


@login_required
def patient_data_detail(request, patient_submission_id):
    """查看患者数据详情（superuser）"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    patient_submission = get_object_or_404(
        PatientSubmission,
        id=patient_submission_id,
        is_submitted=True
    )
    
    # 获取该患者的所有CRF提交
    crf_submissions = CRFSubmission.objects.filter(
        patient_submission=patient_submission
    ).select_related('crf')
    
    # 组织数据
    submission_data = []
    for submission in crf_submissions:
        data = json.loads(submission.data)
        fields = {f.field_name: f for f in submission.crf.fields.all()}
        
        submission_data.append({
            'crf': submission.crf,
            'data': data,
            'fields': fields
        })
    
    return render(request, 'accounts/patient_data_detail.html', {
        'patient_submission': patient_submission,
        'submission_data': submission_data
    })


@login_required
def export_all_data(request):
    """导出所有患者数据为CSV（合并所有CRF）"""
    if not request.user.is_superuser:
        return redirect('user_dashboard')
    
    # 获取所有已提交的患者记录
    patient_submissions = PatientSubmission.objects.filter(
        is_submitted=True
    ).select_related('submitted_by')
    
    if not patient_submissions.exists():
        return HttpResponse("没有数据可导出", content_type="text/plain")
    
    # 获取所有CRF及其字段
    crfs = CRF.objects.filter(is_active=True).prefetch_related('fields')
    
    # 创建CSV响应
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="所有患者数据导出.csv"'
    
    writer = csv.writer(response)
    
    # 构建表头：患者基本信息 + 所有CRF字段（带CRF前缀）
    header = ['患者号', '提交人', '提交时间']
    
    # 为每个CRF的字段添加前缀
    crf_field_map = {}  # 用于后续数据查找
    for crf in crfs:
        crf_field_map[crf.id] = []
        for field in crf.fields.all().order_by('field_order'):
            column_name = f"{crf.name}_{field.field_name}"
            header.append(column_name)
            crf_field_map[crf.id].append(field.field_name)
    
    writer.writerow(header)
    
    # 写入数据
    for patient_submission in patient_submissions:
        # 获取该患者的所有CRF数据
        crf_submissions = CRFSubmission.objects.filter(
            patient_submission=patient_submission
        ).select_related('crf')
        
        # 组织数据
        row_data = {
            '患者号': patient_submission.patient_id,
            '提交人': patient_submission.submitted_by.username,
            '提交时间': patient_submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if patient_submission.submitted_at else ''
        }
        
        # 填充每个CRF的数据
        for submission in crf_submissions:
            crf_data = json.loads(submission.data)
            for field_name in crf_field_map.get(submission.crf.id, []):
                column_name = f"{submission.crf.name}_{field_name}"
                value = crf_data.get(field_name, '')
                # 处理列表类型（多选框）
                if isinstance(value, list):
                    value = ','.join(value)
                row_data[column_name] = value
        
        # 按表头顺序构建行
        row = [row_data.get(col, '') for col in header]
        writer.writerow(row)
    
    return response