from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Event, Category, CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_activated', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'is_activated', 'groups']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('profile_picture', 'phone_number', 'is_activated', 'activation_token')}),
    ) # type: ignore
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('profile_picture', 'phone_number')}),
    )


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