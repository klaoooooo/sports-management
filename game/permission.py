from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect


def get_role(user):
    """anonymous / admin / agent / sporter / judge / visitor"""
    if not user.is_authenticated:
        return 'anonymous'
    if user.is_superuser or user.is_staff:
        return 'admin'
    profile = getattr(user, 'profile', None)
    return profile.role if profile else 'visitor'


def agent_country(user):
    profile = getattr(user, 'profile', None)
    return profile.country.upper() if profile else ''


def can_edit_results(user, event):
    role = get_role(user)
    if role == 'admin':
        return True
    return role == 'judge' and event.judge_id == user.id


def can_manage_athlete(user, country):
    role = get_role(user)
    if role == 'admin':
        return True
    return role == 'agent' and agent_country(user) == (country or '').upper()


def roles_required(*roles):
    """สำหรับหน้าเว็บ: ไม่ล็อกอิน -> หน้า login, ไม่มีสิทธิ์ -> กลับหน้าแรก"""
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if get_role(request.user) not in roles:
                messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
                return redirect('medals')
            return view(request, *args, **kwargs)
        return wrapper
    return deco


def api_roles(*roles):
    """สำหรับ AJAX API: คืน JSON 401/403"""
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'กรุณาเข้าสู่ระบบ'}, status=401)
            if get_role(request.user) not in roles:
                return JsonResponse({'status': 'error', 'message': 'ไม่มีสิทธิ์ทำรายการนี้'}, status=403)
            return view(request, *args, **kwargs)
        return wrapper
    return deco
