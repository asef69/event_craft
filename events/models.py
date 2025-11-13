from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone


class CustomUser(AbstractUser):
    """Custom User Model with profile picture and phone number"""
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        default='profile_pictures/default_profile.jpg',
        blank=True
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    is_activated = models.BooleanField(default=False)
    activation_token = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.username


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
    rsvp_users = models.ManyToManyField(CustomUser, related_name='rsvp_events', blank=True)
    
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