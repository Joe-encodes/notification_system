from rest_framework import serializers

class NotificationRequestSerializer(serializers.Serializer):
    # This is NOT a ModelSerializer because it doesn't map to a DB table.
    # It's a simple Serializer used purely for input validation.
    user_id = serializers.CharField(max_length=255)
    template_code = serializers.CharField(max_length=100)

    # Optional: allows the user to specify if they only want email or push
    notification_type = serializers.ChoiceField(
        choices=['email', 'push'],
        required=False
    )
    template_data = serializers.JSONField(required=False, default=dict)

    # Optional: Key to prevent duplicate requests
    idempotency_key = serializers.CharField(max_length=255, required=False)


def validate(self, data):
        # Custom validation logic goes here (e.g., ensuring template_data is a dict)
        if 'template_data' in data and not isinstance(data['template_data'], dict):
            raise serializers.ValidationError("template_data must be a dictionary.")
        return data



