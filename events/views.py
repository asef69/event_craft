from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from .models import Event, Participant, Category
from .forms import EventForm, ParticipantForm, CategoryForm


# Dashboard View
def dashboard(request):
    """Organizer Dashboard with stats and dynamic filtering"""
    from datetime import datetime, timedelta
    
    # Calculate statistics using optimized queries
    total_participants = Participant.objects.aggregate(
        total=Count('id')
    )['total'] or 0
    
    total_events = Event.objects.count()
    
    # Get current datetime
    now = timezone.now()
    today = now.date()
    
    # Calculate upcoming and past events
    upcoming_events = Event.objects.filter(
        Q(date__gt=today) | 
        Q(date=today, time__gt=now.time())
    ).count()
    
    past_events = Event.objects.filter(
        Q(date__lt=today) |
        Q(date=today, time__lte=now.time())
    ).count()
    
    # Get today's events with optimized queries
    todays_events = Event.objects.filter(
        date=today
    ).select_related('category').prefetch_related('participants')
    
    # Handle dynamic filtering based on filter parameter
    filter_type = request.GET.get('filter', 'today')
    
    if filter_type == 'all':
        filtered_events = Event.objects.all().select_related('category').prefetch_related('participants')
        filter_title = "All Events"
    elif filter_type == 'upcoming':
        filtered_events = Event.objects.filter(
            Q(date__gt=today) | 
            Q(date=today, time__gt=now.time())
        ).select_related('category').prefetch_related('participants')
        filter_title = "Upcoming Events"
    elif filter_type == 'past':
        filtered_events = Event.objects.filter(
            Q(date__lt=today) |
            Q(date=today, time__lte=now.time())
        ).select_related('category').prefetch_related('participants')
        filter_title = "Past Events"
    else:  # today
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
    }
    
    return render(request, 'events/dashboard.html', context)


# Event Views
def event_list(request):
    """List all events with optimized queries and search functionality"""
    # Get search parameters
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base query with optimizations
    events = Event.objects.select_related('category').prefetch_related('participants')
    
    # Apply search filter
    if search_query:
        events = events.filter(
            Q(name__icontains=search_query) | 
            Q(location__icontains=search_query)
        )
    
    # Apply category filter
    if category_filter:
        events = events.filter(category_id=category_filter)
    
    # Apply date range filter
    if date_from:
        events = events.filter(date__gte=date_from)
    if date_to:
        events = events.filter(date__lte=date_to)
    
    # Get all categories for filter dropdown
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


def event_detail(request, pk):
    """Display detailed information for a specific event"""
    event = get_object_or_404(
        Event.objects.select_related('category').prefetch_related('participants'),
        pk=pk
    )
    
    context = {
        'event': event,
    }
    
    return render(request, 'events/event_detail.html', context)


def event_create(request):
    """Create a new event"""
    if request.method == 'POST':
        form = EventForm(request.POST)
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


def event_update(request, pk):
    """Update an existing event"""
    event = get_object_or_404(Event, pk=pk)
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
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


# Participant Views
def participant_list(request):
    """List all participants with their events"""
    search_query = request.GET.get('search', '').strip()
    
    participants = Participant.objects.prefetch_related('events')
    
    if search_query:
        participants = participants.filter(
            Q(name__icontains=search_query) | 
            Q(email__icontains=search_query)
        )
    
    context = {
        'participants': participants,
        'search_query': search_query,
    }
    
    return render(request, 'events/participant_list.html', context)


def participant_detail(request, pk):
    """Display detailed information for a specific participant"""
    participant = get_object_or_404(
        Participant.objects.prefetch_related('events__category'),
        pk=pk
    )
    
    context = {
        'participant': participant,
    }
    
    return render(request, 'events/participant_detail.html', context)


def participant_create(request):
    """Create a new participant"""
    if request.method == 'POST':
        form = ParticipantForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Participant created successfully!')
            return redirect('participant_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ParticipantForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'events/participant_form.html', context)


def participant_update(request, pk):
    """Update an existing participant"""
    participant = get_object_or_404(Participant, pk=pk)
    
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


def participant_delete(request, pk):
    """Delete a participant"""
    participant = get_object_or_404(Participant, pk=pk)
    
    if request.method == 'POST':
        participant.delete()
        messages.success(request, 'Participant deleted successfully!')
        return redirect('participant_list')
    
    context = {
        'participant': participant,
    }
    
    return render(request, 'events/participant_confirm_delete.html', context)


# Category Views
def category_list(request):
    """List all categories with event counts"""
    categories = Category.objects.annotate(event_count=Count('events'))
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'events/category_list.html', context)


def category_detail(request, pk):
    """Display detailed information for a specific category"""
    category = get_object_or_404(Category, pk=pk)
    events = category.events.prefetch_related('participants') # type: ignore
    
    context = {
        'category': category,
        'events': events,
    }
    
    return render(request, 'events/category_detail.html', context)


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