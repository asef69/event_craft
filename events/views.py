from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import Event, Category, CustomUser
from .forms import (CustomUserCreationForm, CategoryForm, EventForm, ParticipantForm,
                    ProfileUpdateForm, CustomPasswordChangeForm)
from .decorators import activation_required, admin_required, organizer_required, participant_required


# Mixin for role-based access control
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to restrict access to Admin users only"""
    login_url = 'login'
    
    def test_func(self):
        return self.request.user.groups.filter(name='Admin').exists() or self.request.user.is_superuser # type: ignore
    
    def handle_no_permission(self): # type: ignore
        messages.error(self.request, 'You do not have permission to access this page.') # type: ignore
        return redirect('dashboard')


class OrganizerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to restrict access to Organizer and Admin users"""
    login_url = 'login'
    
    def test_func(self):
        user_groups = self.request.user.groups.values_list('name', flat=True) # type: ignore
        return any(group in user_groups for group in ['Admin', 'Organizer']) or self.request.user.is_superuser # type: ignore
    
    def handle_no_permission(self): # type: ignore
        messages.error(self.request, 'You do not have permission to access this page.') # type: ignore
        return redirect('dashboard')


class ParticipantRequiredMixin(LoginRequiredMixin):
    """Mixin to restrict access to authenticated users"""
    login_url = 'login'


# Authentication Views
class SignUpView(CreateView):
    """User registration view - CONVERTED FROM FBV"""
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'events/signup.html'
    success_url = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False  # Deactivate until email verification
        user.save()
        
        # Assign Participant group by default
        participant_group, created = Group.objects.get_or_create(name='Participant')
        user.groups.add(participant_group)
        
        messages.success(self.request, 'Registration successful! Please check your email to activate your account.')
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class LoginView(View):
    """User login view - CONVERTED FROM FBV"""
    template_name = 'events/login.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
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
            return render(request, self.template_name)


class LogoutView(LoginRequiredMixin, View):
    """User logout view - CONVERTED FROM FBV"""
    login_url = 'login'
    
    def get(self, request):
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('login')


class ActivateAccountView(View):
    """Activate user account via email link - CONVERTED FROM FBV"""
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.is_activated = True
            user.save()
            
            messages.success(request, 'Your account has been activated successfully! You can now login.')
            return redirect('login')
        else:
            messages.error(request, 'Activation link is invalid or has expired.')
            return redirect('login')


# Profile Views
class ProfileView(LoginRequiredMixin, TemplateView):
    """View user profile - NEW FOR MID-TERM"""
    template_name = 'events/profile.html'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Edit user profile - NEW FOR MID-TERM"""
    model = CustomUser
    form_class = ProfileUpdateForm
    template_name = 'events/profile_edit.html'
    success_url = reverse_lazy('profile')
    login_url = 'login'
    
    def get_object(self, queryset=None): # type: ignore
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PasswordChangeView(LoginRequiredMixin, View):
    """Change password - NEW FOR MID-TERM"""
    template_name = 'events/password_change.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('profile')
    login_url = 'login'
    
    def get(self, request):
        form = self.form_class(request.user)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password has been changed successfully!')
            return redirect(self.success_url)
        else:
            messages.error(request, 'Please correct the errors below.')
            return render(request, self.template_name, {'form': form})


class CustomPasswordResetView(PasswordResetView):
    """Password reset via email - NEW FOR MID-TERM"""
    template_name = 'events/password_reset.html'
    email_template_name = 'events/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')
    
    def form_valid(self, form):
        messages.success(self.request, 'Password reset email has been sent to your email address.')
        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Password reset confirmation - NEW FOR MID-TERM"""
    template_name = 'events/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been reset successfully! You can now login.')
        return super().form_valid(form)
    
# Dashboard Views
class DashboardView(LoginRequiredMixin, View):
    """Role-based dashboard redirect - CONVERTED FROM FBV"""
    login_url = 'login'
    
    def get(self, request):
        user = request.user
        
        # Check activation
        if not user.is_activated and not user.is_superuser:
            messages.error(request, 'Please activate your account first.')
            return redirect('login')
        
        # Redirect based on role
        if user.is_superuser or user.groups.filter(name='Admin').exists():
            return AdminDashboardView.as_view()(request)
        elif user.groups.filter(name='Organizer').exists():
            return OrganizerDashboardView.as_view()(request)
        else:
            return ParticipantDashboardView.as_view()(request)


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Admin Dashboard - CONVERTED FROM FBV"""
    template_name = 'events/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate statistics
        context['total_participants'] = CustomUser.objects.filter(groups__name='Participant').count()
        context['total_events'] = Event.objects.count()
        
        now = timezone.now()
        today = now.date()
        
        context['upcoming_events'] = Event.objects.filter(
            Q(date__gt=today) | Q(date=today, time__gt=now.time())
        ).count()
        
        context['past_events'] = Event.objects.filter(
            Q(date__lt=today) | Q(date=today, time__lte=now.time())
        ).count()
        
        todays_events = Event.objects.filter(date=today).select_related('category').prefetch_related('rsvp_users')
        
        # Handle filtering
        filter_type = self.request.GET.get('filter', 'today')
        
        if filter_type == 'all':
            context['filtered_events'] = Event.objects.all().select_related('category').prefetch_related('rsvp_users')
            context['filter_title'] = "All Events"
        elif filter_type == 'upcoming':
            context['filtered_events'] = Event.objects.filter(
                Q(date__gt=today) | Q(date=today, time__gt=now.time())
            ).select_related('category').prefetch_related('rsvp_users')
            context['filter_title'] = "Upcoming Events"
        elif filter_type == 'past':
            context['filtered_events'] = Event.objects.filter(
                Q(date__lt=today) | Q(date=today, time__lte=now.time())
            ).select_related('category').prefetch_related('rsvp_users')
            context['filter_title'] = "Past Events"
        else:
            context['filtered_events'] = todays_events
            context['filter_title'] = "Today's Events"
        
        context['filter_type'] = filter_type
        context['dashboard_type'] = 'admin'
        
        return context


class OrganizerDashboardView(OrganizerRequiredMixin, TemplateView):
    """Organizer Dashboard - CONVERTED FROM FBV"""
    template_name = 'events/organizer_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        now = timezone.now()
        today = now.date()
        
        context['total_events'] = Event.objects.count()
        context['total_categories'] = Category.objects.count()
        context['upcoming_events'] = Event.objects.filter(
            Q(date__gt=today) | Q(date=today, time__gt=now.time())
        ).count()
        
        filter_type = self.request.GET.get('filter', 'today')
        
        if filter_type == 'all':
            context['filtered_events'] = Event.objects.all().select_related('category').prefetch_related('rsvp_users')
            context['filter_title'] = "All Events"
        elif filter_type == 'upcoming':
            context['filtered_events'] = Event.objects.filter(
                Q(date__gt=today) | Q(date=today, time__gt=now.time())
            ).select_related('category').prefetch_related('rsvp_users')
            context['filter_title'] = "Upcoming Events"
        else:
            context['filtered_events'] = Event.objects.filter(date=today).select_related('category').prefetch_related('rsvp_users')
            context['filter_title'] = "Today's Events"
        
        context['filter_type'] = filter_type
        context['dashboard_type'] = 'organizer'
        
        return context


class ParticipantDashboardView(ParticipantRequiredMixin, TemplateView):
    """Participant Dashboard - CONVERTED FROM FBV"""
    template_name = 'events/participant_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        now = timezone.now()
        today = now.date()
        
        rsvp_events = user.rsvp_events.select_related('category').all() # type: ignore
        
        context['rsvp_events'] = rsvp_events
        context['upcoming_rsvp'] = rsvp_events.filter(
            Q(date__gt=today) | Q(date=today, time__gt=now.time())
        )
        context['past_rsvp'] = rsvp_events.filter(
            Q(date__lt=today) | Q(date=today, time__lte=now.time())
        )
        context['total_rsvp'] = rsvp_events.count()
        context['dashboard_type'] = 'participant'
        
        return context


# Event Views
class EventListView(LoginRequiredMixin, ListView):
    """List all events - CONVERTED FROM FBV"""
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    login_url = 'login'
    
    def get_queryset(self):
        queryset = Event.objects.select_related('category').prefetch_related('rsvp_users')
        
        # Apply filters
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(location__icontains=search_query)
            )
        
        category_filter = self.request.GET.get('category', '')
        if category_filter:
            queryset = queryset.filter(category_id=category_filter)
        
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.GET.get('date_to', '')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    """Event detail view - CONVERTED FROM FBV"""
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    login_url = 'login'
    
    def get_queryset(self):
        return Event.objects.select_related('category').prefetch_related('rsvp_users')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_has_rsvp'] = self.request.user in self.object.rsvp_users.all() # type: ignore
        return context


class EventCreateView(OrganizerRequiredMixin, CreateView):
    """Create event - CONVERTED FROM FBV"""
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('event_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Event created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class EventUpdateView(OrganizerRequiredMixin, UpdateView):
    """Update event - CONVERTED FROM FBV"""
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    
    def get_success_url(self):
        return reverse_lazy('event_detail', kwargs={'pk': self.object.pk}) # type: ignore
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['event'] = self.object # type: ignore
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Event updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class EventDeleteView(OrganizerRequiredMixin, DeleteView):
    """Delete event - CONVERTED FROM FBV"""
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('event_list')
    context_object_name = 'event'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Event deleted successfully!')
        return super().delete(request, *args, **kwargs)


# RSVP Views
class RSVPEventView(ParticipantRequiredMixin, View):
    """RSVP to event - CONVERTED FROM FBV"""
    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        
        if user in event.rsvp_users.all():
            messages.warning(request, 'You have already RSVP\'d to this event.')
        else:
            event.rsvp_users.add(user)
            messages.success(request, f'You have successfully RSVP\'d to {event.name}! Check your email for confirmation.')
        
        return redirect('event_detail', pk=pk)


class CancelRSVPView(ParticipantRequiredMixin, View):
    """Cancel RSVP - CONVERTED FROM FBV"""
    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        user = request.user
        
        if user in event.rsvp_users.all():
            event.rsvp_users.remove(user)
            messages.success(request, f'Your RSVP to {event.name} has been cancelled.')
        else:
            messages.warning(request, 'You have not RSVP\'d to this event.')
        
        return redirect('event_detail', pk=pk)


# Category Views
class CategoryListView(LoginRequiredMixin, ListView):
    """List all categories - CONVERTED FROM FBV"""
    model = Category
    template_name = 'events/category_list.html'
    context_object_name = 'categories'
    login_url = 'login'
    
    def get_queryset(self):
        return Category.objects.annotate(event_count=Count('events'))


class CategoryDetailView(LoginRequiredMixin, DetailView):
    """Category detail - CONVERTED FROM FBV"""
    model = Category
    template_name = 'events/category_detail.html'
    context_object_name = 'category'
    login_url = 'login'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['events'] = self.object.events.prefetch_related('rsvp_users') # type: ignore
        return context


class CategoryCreateView(OrganizerRequiredMixin, CreateView):
    """Create category - CONVERTED FROM FBV"""
    model = Category
    form_class = CategoryForm
    template_name = 'events/category_form.html'
    success_url = reverse_lazy('category_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Category created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CategoryUpdateView(OrganizerRequiredMixin, UpdateView):
    """Update category - CONVERTED FROM FBV"""
    model = Category
    form_class = CategoryForm
    template_name = 'events/category_form.html'
    
    def get_success_url(self):
        return reverse_lazy('category_detail', kwargs={'pk': self.object.pk}) # type: ignore
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['category'] = self.object # type: ignore
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CategoryDeleteView(OrganizerRequiredMixin, DeleteView):
    """Delete category - CONVERTED FROM FBV"""
    model = Category
    template_name = 'events/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')
    context_object_name = 'category'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Category deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Participant Views (Admin Only)
class ParticipantListView(AdminRequiredMixin, ListView):
    """List all participants - CONVERTED FROM FBV"""
    model = CustomUser
    template_name = 'events/participant_list.html'
    context_object_name = 'participants'
    
    def get_queryset(self):
        queryset = CustomUser.objects.filter(groups__name='Participant').prefetch_related('rsvp_events')
        
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) | 
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class ParticipantDetailView(AdminRequiredMixin, DetailView):
    """Participant detail - CONVERTED FROM FBV"""
    model = CustomUser
    template_name = 'events/participant_detail.html'
    context_object_name = 'participant'
    
    def get_queryset(self):
        return CustomUser.objects.prefetch_related('rsvp_events__category')


class ParticipantUpdateView(AdminRequiredMixin, UpdateView):
    """Update participant - CONVERTED FROM FBV"""
    model = CustomUser
    form_class = ParticipantForm
    template_name = 'events/participant_form.html'
    
    def get_success_url(self):
        return reverse_lazy('participant_detail', kwargs={'pk': self.object.pk}) # type: ignore
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['participant'] = self.object # type: ignore
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Participant updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ParticipantDeleteView(AdminRequiredMixin, DeleteView):
    """Delete participant - CONVERTED FROM FBV"""
    model = CustomUser
    template_name = 'events/participant_confirm_delete.html'
    success_url = reverse_lazy('participant_list')
    context_object_name = 'participant'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Participant deleted successfully!')
        return super().delete(request, *args, **kwargs)   



class ParticipantCreateView(OrganizerRequiredMixin, CreateView):
    """Create participant - CONVERTED FROM FBV"""
    model = CustomUser
    form_class = ParticipantForm
    template_name = 'events/participant_form.html'
    success_url = reverse_lazy('participant_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Participant created successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)          
