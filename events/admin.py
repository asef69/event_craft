from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Event, Category, UserProfile

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'event_count']
    search_fields = ['name', 'description']
    
    def event_count(self, obj):
        return obj.events.count()
    event_count.short_description = 'Number of Events' # type: ignore


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'date', 'time', 'location', 'rsvp_count']
    list_filter = ['category', 'date']
    search_fields = ['name', 'location', 'description']
    date_hierarchy = 'date'
    filter_horizontal = ['rsvp_users']
    
    def rsvp_count(self, obj):
        return obj.rsvp_users.count()
    rsvp_count.short_description = 'RSVPs' # type: ignore


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_activated', 'activation_token']
    list_filter = ['is_activated']
    search_fields = ['user__username', 'user__email']