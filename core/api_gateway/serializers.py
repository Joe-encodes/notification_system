from rest_framework import serializers

class NotificationStatusSerializer(serializers.Serializer):
    """
    Serializer for notification status updates.
    POST /api/v1/notifications/{notification_type}/status/
    {
        notification_id: str,
        status: NotificationStatus,
        timestamp: Optional[datetime],
        error: Optional[str]
    }
    """
    notification_id = serializers.CharField(max_length=255, required=True)
    status = serializers.ChoiceField(
        choices=['delivered', 'pending', 'failed'],
        required=True
    )
    timestamp = serializers.DateTimeField(required=False)
    error = serializers.CharField(required=False, allow_blank=True)

class NotificationRequestSerializer(serializers.Serializer):
    """
    Serializer for notification requests matching the task specification.
    Request format:
    {
        notification_type: NotificationType,
        user_id: uuid,
        template_code: str | path,
        variables: UserData,
        request_id: str,
        priority: int,
        metadata: Optional[dict]
    }
    """
    notification_type = serializers.ChoiceField(
        choices=['email', 'push'],
        required=True
    )
    user_id = serializers.UUIDField(required=True)
    template_code = serializers.CharField(max_length=100, required=True)
    variables = serializers.JSONField(required=True)
    request_id = serializers.CharField(max_length=255, required=False)
    priority = serializers.IntegerField(default=0, required=False)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate(self, data):
        """Custom validation logic"""
        if 'variables' in data and not isinstance(data['variables'], dict):
            raise serializers.ValidationError("variables must be a dictionary.")
        if 'metadata' in data and not isinstance(data['metadata'], dict):
            raise serializers.ValidationError("metadata must be a dictionary.")
        return data



