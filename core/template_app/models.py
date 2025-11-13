from django.db import models

class TemplateModel(models.Model):
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('push', 'Push Notification'),
    ]

    template_code = models.CharField(max_length=100)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)

    # subject: The subject line for emails or title for push
    subject = models.CharField(max_length=255, blank=True, null=True)

    # content: The main body of the notification (can contain variables like {{name}})
    content = models.TextField()

    # Versioning for template changes
    version = models.PositiveIntegerField(default=1)

    # Language support for multi-language templates
    language = models.CharField(max_length=10, default='en', help_text='Language code (e.g., en, fr, es)')

    # Active status - only active templates are used
    is_active = models.BooleanField(default=True)

    # required_variables: A list of variables the template expects (e.g., ['name', 'order_id'])
    required_variables = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'template'
        # This ensures we can't have two templates with the same name, version, and language
        unique_together = ('template_code', 'version', 'language')
        indexes = [
            models.Index(fields=['template_code', 'language', 'is_active']),
        ]

    def __str__(self):
        return f"{self.template_code} (v{self.version}, {self.language})"
