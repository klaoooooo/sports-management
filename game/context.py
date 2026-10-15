from .permission import get_role


def role_flags(request):
    role = get_role(request.user)
    return {
        'role': role,
        'is_admin': role == 'admin',
        'can_manage_athletes': role in ('admin', 'agent'),
    }
