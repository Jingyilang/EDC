from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import CRF, CRFField


class CustomLoginForm(forms.Form):
    
    # 账号（对应 User.username）
    username = forms.CharField(
        label='账号',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入您的账号'
        })
    )
    
    # 密码
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError("账号或密码不正确")
            self.user_cache = user
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)


class RegisterForm(forms.Form):
    # 账号
    username = forms.CharField(
        label='账号',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入账号（用于登录）'
        })
    )
    
    # 密码
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
    )
    
    # 确认密码
    confirm_password = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请再次输入密码'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("该账号已存在，请使用其他账号")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("两次输入的密码不一致")
        return cleaned_data


class CRFForm(forms.ModelForm):
    """CRF创建表单"""
    class Meta:
        model = CRF
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入CRF名称'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '输入CRF描述（可选）'}),
        }


class CRFFieldForm(forms.ModelForm):
    """CRF字段创建表单"""
    class Meta:
        model = CRFField
        fields = ['field_name', 'field_label', 'field_type', 'field_order', 'is_required', 'options']
        widgets = {
            'field_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '字段标识符（英文）'}),
            'field_label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '字段显示名称（中文）'}),
            'field_type': forms.Select(attrs={'class': 'form-control'}),
            'field_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'options': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '选项1,选项2,选项3'}),
        }


class CRFDataEntryForm(forms.Form):
    """CRF数据填写表单（动态生成）"""
    def __init__(self, *args, **kwargs):
        crf = kwargs.pop('crf', None)
        super().__init__(*args, **kwargs)
        
        if crf:
            for field in crf.fields.all().order_by('field_order'):
                field_kwargs = {
                    'label': field.field_label,
                    'required': field.is_required,
                }
                
                if field.field_type == 'text':
                    field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
                    self.fields[field.field_name] = forms.CharField(**field_kwargs)
                elif field.field_type == 'number':
                    field_kwargs['widget'] = forms.NumberInput(attrs={'class': 'form-control'})
                    self.fields[field.field_name] = forms.CharField(**field_kwargs)
                elif field.field_type == 'date':
                    field_kwargs['widget'] = forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                    self.fields[field.field_name] = forms.DateField(**field_kwargs)
                elif field.field_type == 'textarea':
                    field_kwargs['widget'] = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                    self.fields[field.field_name] = forms.CharField(**field_kwargs)
                elif field.field_type == 'select':
                    choices = [('', '请选择')]
                    if field.options:
                        for option in field.options.split(','):
                            choices.append((option.strip(), option.strip()))
                    field_kwargs['choices'] = choices
                    field_kwargs['widget'] = forms.Select(attrs={'class': 'form-control'})
                    self.fields[field.field_name] = forms.ChoiceField(**field_kwargs)
                elif field.field_type == 'radio':
                    choices = []
                    if field.options:
                        for option in field.options.split(','):
                            choices.append((option.strip(), option.strip()))
                    field_kwargs['choices'] = choices
                    field_kwargs['widget'] = forms.RadioSelect(attrs={'class': 'form-check-input'})
                    self.fields[field.field_name] = forms.ChoiceField(**field_kwargs)
                elif field.field_type == 'checkbox':
                    choices = []
                    if field.options:
                        for option in field.options.split(','):
                            choices.append((option.strip(), option.strip()))
                    field_kwargs['choices'] = choices
                    field_kwargs['widget'] = forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
                    self.fields[field.field_name] = forms.MultipleChoiceField(**field_kwargs)
