from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Event(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=300)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='events')
    image = models.ImageField(upload_to='event_images/', default='event_images/default.jpg')
    rsvp_users = models.ManyToManyField(User, related_name='rsvp_events', blank=True)
    
    class Meta:
        ordering = ['-date', '-time']
    
    def __str__(self):
        return self.name
    
    @property
    def is_upcoming(self):
        event_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.time)
        )
        return event_datetime > timezone.now()
    
    @property
    def is_today(self):
        return self.date == timezone.now().date()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_activated = models.BooleanField(default=False)
    activation_token = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"