from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    push_token = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

class UserPreference(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='preferences'
    )
    notification_preferences = models.JSONField(
        default=dict,
        help_text='User notification preferences in JSON format',
        blank=True
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text='Enable/disable all email notifications'
    )
    push_notifications = models.BooleanField(
        default=True,
        help_text='Enable/disable all push notifications'
    )
    language = models.CharField(
        max_length=10, 
        default='en',
        help_text='User preferred language code (e.g., en, fr, es)'
    )
    timezone = models.CharField(
        max_length=100, 
        default='UTC',
        help_text='User timezone'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"

    class Meta:
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'