from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Athlete

INPUT = ("w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm "
         "text-white focus:outline-none focus:border-brand-500")


class StyledLoginForm(AuthenticationForm):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for f in self.fields.values():
            f.widget.attrs['class'] = INPUT


class RegisterForm(UserCreationForm):
    ROLE_CHOICES = [
        ('visitor', 'Visitor (ผู้เข้าชม)'),
        ('sporter', 'Sporter (นักกีฬา)'),
        ('agent', 'Agent (ตัวแทนประเทศ)'),
        ('judge', 'Judge (กรรมการ)'),
    ]
    GENDER_CHOICES = [('', '-'), ('Men', 'Men'), ('Women', 'Women')]

    email = forms.EmailField(label='อีเมล (Email)', required=False)
    role = forms.ChoiceField(label='บทบาท (Role)', choices=ROLE_CHOICES)
    first_name = forms.CharField(label='ชื่อ', max_length=100, required=False)
    last_name = forms.CharField(label='นามสกุล', max_length=100, required=False)
    country = forms.CharField(label='ประเทศ (รหัส 3 ตัว เช่น THA) - Agent/Sporter', max_length=5,
                              required=False)
    gender = forms.ChoiceField(label='เพศ - Sporter', choices=GENDER_CHOICES, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for f in self.fields.values():
            f.widget.attrs['class'] = INPUT

    def clean(self):
        data = super().clean()
        role = data.get('role')
        if role in ('agent', 'sporter') and not data.get('country'):
            self.add_error('country', 'Agent และ Sporter ต้องระบุประเทศ')
        if role == 'sporter':
            for f in ('first_name', 'last_name', 'gender'):
                if not data.get(f):
                    self.add_error(f, 'Sporter ต้องกรอกช่องนี้')
        if data.get('country'):
            data['country'] = data['country'].strip().upper()
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.save()
        role = self.cleaned_data['role']
        profile = user.profile
        profile.role = role
        profile.country = self.cleaned_data.get('country', '')
        profile.save()
        if role == 'sporter':
            Athlete.objects.create(
                user=user, email=user.email, first_name=user.first_name,
                last_name=user.last_name, country=profile.country,
                gender=self.cleaned_data['gender'], bib=f"S{user.id}",
                classification='TBD',
            )
        return user
