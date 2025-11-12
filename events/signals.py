from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .models import UserProfile, Event


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(post_save, sender=User)
def send_activation_email(sender, instance, created, **kwargs):
    """Send activation email to newly registered users"""
    if created:
        # Generate activation token
        token = default_token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk))
        
        # Save token to profile
        profile = instance.profile
        profile.activation_token = token
        profile.save()
        
        # Create activation link
        activation_link = f"{settings.SITE_URL}/activate/{uid}/{token}/"
        
        # Send email
        subject = 'Activate Your Event Management Account'
        message = f"""
Hello {instance.first_name or instance.username},

Thank you for registering with Event Management System!

Please click the link below to activate your account:
{activation_link}

This link will expire in 24 hours.

Best regards,
Event Management Team
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send activation email: {e}")


@receiver(m2m_changed, sender=Event.rsvp_users.through)
def send_rsvp_notification(sender, instance, action, pk_set, **kwargs):
    """Send email notification when user RSVPs to an event"""
    if action == "post_add":
        # Get the users who just RSVP'd
        users = User.objects.filter(pk__in=pk_set)
        
        for user in users:
            subject = f'RSVP Confirmation - {instance.name}'
            message = f"""
Hello {user.first_name or user.username},

You have successfully RSVP'd to the following event:

Event: {instance.name}
Date: {instance.date.strftime('%B %d, %Y')}
Time: {instance.time.strftime('%I:%M %p')}
Location: {instance.location}

We look forward to seeing you there!

Best regards,
Event Management Team
            """
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send RSVP email to {user.email}: {e}")