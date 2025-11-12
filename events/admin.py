from django.contrib import admin
from .models import Event, Participant, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'event_count']
    search_fields = ['name', 'description']
    
    def event_count(self, obj):
        return obj.events.count()
    event_count.short_description = 'Number of Events' # type: ignore


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'date', 'time', 'location', 'participant_count']
    list_filter = ['category', 'date']
    search_fields = ['name', 'location', 'description']
    date_hierarchy = 'date'
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants' # type: ignore


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'event_count']
    search_fields = ['name', 'email']
    filter_horizontal = ['events']
    
    def event_count(self, obj):
        return obj.events.count()
    event_count.short_description = 'Events Registered' # type: ignore