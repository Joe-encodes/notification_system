from rest_framework import serializers
from .models import TemplateModel

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateModel
        fields = '__all__'  # Serialize all fields of the TemplateModel

        # extra_kwargs ensures that the JSON keys are in snake_case (e.g., template_name)
        extra_kwargs = {
            'template_code': {'source': 'template_code'},
            'notification_type': {'source': 'notification_type'},
            'subject': {'source': 'subject'},
            'content': {'source': 'content'},
            'required_variables': {'source': 'required_variables'},
        }