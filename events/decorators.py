from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.contrib.auth import logout


def activation_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and not profile.is_activated:
                messages.error(request, 'Please activate your account. We just logged you out.')
                logout(request)  
                return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator to restrict access to Admin users only"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('login')
        
        if not request.user.groups.filter(name='Admin').exists() and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def organizer_required(view_func):
    """Decorator to restrict access to Organizer and Admin users"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('login')
        
        user_groups = request.user.groups.values_list('name', flat=True)
        if not any(group in user_groups for group in ['Admin', 'Organizer']) and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def participant_required(view_func):
    """Decorator to restrict access to authenticated Participant users"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper