from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .models import Event, Category, UserProfile
from .forms import EventForm, CategoryForm, UserRegistrationForm, ParticipantForm
from .decorators import admin_required, organizer_required, participant_required, activation_required


# Authentication Views
def signup(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate account until email verification
            user.save()
            
            # Assign Participant group by default
            participant_group, created = Group.objects.get_or_create(name='Participant')
            user.groups.add(participant_group)
            
            messages.success(request, 'Registration successful! Please check your email to activate your account.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'events/signup.html', {'form': form})


def activate_account(request, uidb64, token):
    """Activate user account via email link"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.profile.is_activated = True # type: ignore
        user.save()
        user.profile.save() # type: ignore
        
        messages.success(request, 'Your account has been activated successfully! You can now login.')
        return redirect('login')
    else:
        messages.error(request, 'Activation link is invalid or has expired.')
        return redirect('login')


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Please activate your account first. Check your email for the activation link.')
                return redirect('login')
            
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'events/login.html')


@login_required
def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


# Dashboard Views
@login_required
@activation_required
def dashboard(request):
    """Role-based dashboard redirect"""
    user = request.user
    group_names = list(request.user.groups.values_list('name', flat=True))
    
    # Check user role and redirect to appropriate dashboard
    if user.is_superuser or 'Admin' in group_names:
        return admin_dashboard(request)
    elif 'Organizer' in group_names:
        return organizer_dashboard(request)
    else:
        return participant_dashboard(request)


@login_required
@admin_required
def admin_dashboard(request):
    """Admin Dashboard with full access"""
    from datetime import datetime, timedelta
    
    # Calculate statistics
    total_participants = User.objects.filter(groups__name='Participant').count()
    total_events = Event.objects.count()
    
    now = timezone.now()
    today = now.date()
    
    upcoming_events = Event.objects.filter(
        Q(date__gt=today) | 
        Q(date=today, time__gt=now.time())
    ).count()
    
    past_events = Event.objects.filter(
        Q(date__lt=today) |
        Q(date=today, time__lte=now.time())
    ).count()
    
    todays_events = Event.objects.filter(
        date=today
    ).select_related('category').prefetch_related('rsvp_users')
    
    # Handle filtering
    filter_type = request.GET.get('filter', 'today')
    
    if filter_type == 'all':
        filtered_events = Event.objects.all().select_related('category').prefetch_related('rsvp_users')
        filter_title = "All Events"
    elif filter_type == 'upcoming':
        filtered_events = Event.objects.filter(
            Q(date__gt=today) | 
            Q(date=today, time__gt=now.time())
        ).select_related('category').prefetch_related('rsvp_users')
        filter_title = "Upcoming Events"
    elif filter_type == 'past':
        filtered_events = Event.objects.filter(
            Q(date__lt=today) |
            Q(date=today, time__lte=now.time())
        ).select_related('category').prefetch_related('rsvp_users')
        filter_title = "Past Events"
    else:
        filtered_events = todays_events
        filter_title = "Today's Events"
    
    context = {
        'total_participants': total_participants,
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'todays_events': todays_events,
        'filtered_events': filtered_events,
        'filter_type': filter_type,
        'filter_title': filter_title,
        'dashboard_type': 'admin',
    }
    
    return render(request, 'events/admin_dashboard.html', context)


@login_required
@organizer_required
def organizer_dashboard(request):
    """Organizer Dashboard for managing events and categories"""
    now = timezone.now()
    today = now.date()
    
    total_events = Event.objects.count()
    total_categories = Category.objects.count()
    
    upcoming_events = Event.objects.filter(
        Q(date__gt=today) | 
        Q(date=today, time__gt=now.time())
    ).count()
    
    todays_events = Event.objects.filter(
        date=today
    ).select_related('category').prefetch_related('rsvp_users')
    
    filter_type = request.GET.get('filter', 'today')
    
    if filter_type == 'all':
        filtered_events = Event.objects.all().select_related('category').prefetch_related('rsvp_users')
        filter_title = "All Events"
    elif filter_type == 'upcoming':
        filtered_events = Event.objects.filter(
            Q(date__gt=today) | 
            Q(date=today, time__gt=now.time())
        ).select_related('category').prefetch_related('rsvp_users')
        filter_title = "Upcoming Events"
    else:
        filtered_events = todays_events
        filter_title = "Today's Events"
    
    context = {
        'total_events': total_events,
        'total_categories': total_categories,
        'upcoming_events': upcoming_events,
        'filtered_events': filtered_events,
        'filter_type': filter_type,
        'filter_title': filter_title,
        'dashboard_type': 'organizer',
    }
    
    return render(request, 'events/organizer_dashboard.html', context)


@login_required
@participant_required
def participant_dashboard(request):
    """Participant Dashboard to view RSVP'd events"""
    user = request.user
    
    now = timezone.now()
    today = now.date()
    
    # Get all RSVP'd events
    rsvp_events = user.rsvp_events.select_related('category').all()
    
    # Categorize events
    upcoming_rsvp = rsvp_events.filter(
        Q(date__gt=today) | 
        Q(date=today, time__gt=now.time())
    )
    
    past_rsvp = rsvp_events.filter(
        Q(date__lt=today) |
        Q(date=today, time__lte=now.time())
    )
    
    context = {
        'rsvp_events': rsvp_events,
        'upcoming_rsvp': upcoming_rsvp,
        'past_rsvp': past_rsvp,
        'total_rsvp': rsvp_events.count(),
        'dashboard_type': 'participant',
    }
    
    return render(request, 'events/participant_dashboard.html', context)

# Event Views
@login_required
def event_list(request):
    """List all events with optimized queries and search functionality"""
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    events = Event.objects.select_related('category').prefetch_related('rsvp_users')
    
    if search_query:
        events = events.filter(
            Q(name__icontains=search_query) | 
            Q(location__icontains=search_query)
        )
    
    if category_filter:
        events = events.filter(category_id=category_filter)
    
    if date_from:
        events = events.filter(date__gte=date_from)
    if date_to:
        events = events.filter(date__lte=date_to)
    
    categories = Category.objects.all()
    
    context = {
        'events': events,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'events/event_list.html', context)


@login_required
def event_detail(request, pk):
    """Display detailed information for a specific event"""
    event = get_object_or_404(
        Event.objects.select_related('category').prefetch_related('rsvp_users'),
        pk=pk
    )
    
    user_has_rsvp = request.user in event.rsvp_users.all()
    
    context = {
        'event': event,
        'user_has_rsvp': user_has_rsvp,
    }
    
    return render(request, 'events/event_detail.html', context)


@login_required
@organizer_required
def event_create(request):
    """Create a new event"""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event created successfully!')
            return redirect('event_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'events/event_form.html', context)


@login_required
@organizer_required
def event_update(request, pk):
    """Update an existing event"""
    event = get_object_or_404(Event, pk=pk)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm(instance=event)
    
    context = {
        'form': form,
        'event': event,
        'action': 'Update',
    }
    
    return render(request, 'events/event_form.html', context)


@login_required
@organizer_required
def event_delete(request, pk):
    """Delete an event"""
    event = get_object_or_404(Event, pk=pk)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully!')
        return redirect('event_list')
    
    context = {
        'event': event,
    }
    
    return render(request, 'events/event_confirm_delete.html', context)


# RSVP Functionality
@login_required
@participant_required
def rsvp_event(request, pk):
    """RSVP to an event"""
    event = get_object_or_404(Event, pk=pk)
    user = request.user
    
    if user in event.rsvp_users.all():
        messages.warning(request, 'You have already RSVP\'d to this event.')
    else:
        event.rsvp_users.add(user)
        messages.success(request, f'You have successfully RSVP\'d to {event.name}! Check your email for confirmation.')
    
    return redirect('event_detail', pk=pk)


@login_required
@participant_required
def cancel_rsvp(request, pk):
    """Cancel RSVP to an event"""
    event = get_object_or_404(Event, pk=pk)
    user = request.user
    
    if user in event.rsvp_users.all():
        event.rsvp_users.remove(user)
        messages.success(request, f'Your RSVP to {event.name} has been cancelled.')
    else:
        messages.warning(request, 'You have not RSVP\'d to this event.')
    
    return redirect('event_detail', pk=pk)

# Participant Views (Admin only can manage)
@login_required
@admin_required
def participant_list(request):
    """List all participants with their events"""
    search_query = request.GET.get('search', '').strip()
    
    participants = User.objects.filter(groups__name='Participant').prefetch_related('rsvp_events')
    
    if search_query:
        participants = participants.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    context = {
        'participants': participants,
        'search_query': search_query,
    }
    
    return render(request, 'events/participant_list.html', context)


@login_required
@admin_required
def participant_detail(request, pk):
    """Display detailed information for a specific participant"""
    participant = get_object_or_404(
        User.objects.prefetch_related('rsvp_events__category'),
        pk=pk
    )
    
    context = {
        'participant': participant,
    }
    
    return render(request, 'events/participant_detail.html', context)


@login_required
@admin_required
def participant_update(request, pk):
    """Update an existing participant"""
    participant = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = ParticipantForm(request.POST, instance=participant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Participant updated successfully!')
            return redirect('participant_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ParticipantForm(instance=participant)
    
    context = {
        'form': form,
        'participant': participant,
        'action': 'Update',
    }
    
    return render(request, 'events/participant_form.html', context)


@login_required
@admin_required
def participant_delete(request, pk):
    """Delete a participant"""
    participant = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        participant.delete()
        messages.success(request, 'Participant deleted successfully!')
        return redirect('participant_list')
    
    context = {
        'participant': participant,
    }
    
    return render(request, 'events/participant_confirm_delete.html', context)


# Category Views (Organizer and Admin)
@login_required
def category_list(request):
    """List all categories with event counts"""
    categories = Category.objects.annotate(event_count=Count('events'))
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'events/category_list.html', context)


@login_required
def category_detail(request, pk):
    """Display detailed information for a specific category"""
    category = get_object_or_404(Category, pk=pk)
    events = category.events.prefetch_related('rsvp_users') # type: ignore
    
    context = {
        'category': category,
        'events': events,
    }
    
    return render(request, 'events/category_detail.html', context)


@login_required
@organizer_required
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully!')
            return redirect('category_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'events/category_form.html', context)


@login_required
@organizer_required
def category_update(request, pk):
    """Update an existing category"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('category_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'action': 'Update',
    }
    
    return render(request, 'events/category_form.html', context)


@login_required
@organizer_required
def category_delete(request, pk):
    """Delete a category"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('category_list')
    
    context = {
        'category': category,
    }
    
    return render(request, 'events/category_confirm_delete.html', context)



@login_required
def participant_create(request):
    # allow only Admin/Organizer (or superuser)
    if not (
        request.user.is_superuser
        or request.user.groups.filter(name__in=["Admin", "Organizer"]).exists()
    ):
        messages.error(request, "You don't have permission to add participants.")
        return redirect("events:participant_list")

    if request.method == "POST":
        form = ParticipantForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Participant created successfully.")
            return redirect("events:participant_list")
    else:
        form = ParticipantForm()

    return render(request, "events/participant_form.html", {"form": form})

