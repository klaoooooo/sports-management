from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def is_admin(user):
    """Admin = staff or superuser. Everyone else logged in is a normal User."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def admin_required(view_func):
    """Admin only. Normal users are sent back to the dashboard with a message;
    anonymous visitors are sent to the login page."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, 'You do not have permission to do that (Admin only).')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper