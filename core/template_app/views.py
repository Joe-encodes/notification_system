from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import TemplateModel
from .serializers import TemplateSerializer
from core.utils import CustomResponseMixin

class TemplateViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows templates to be viewed or edited.
    Uses template_code for lookups instead of primary key.
    """
    serializer_class = TemplateSerializer
    queryset = TemplateModel.objects.all()
    permission_classes = [AllowAny]
    lookup_field = 'template_code'
    
    def get_queryset(self):
        """
        Optionally filters templates by type and active status.
        Example: /api/v1/templates/?notification_type=email&is_active=true
        """
        queryset = TemplateModel.objects.all()
        notification_type = self.request.query_params.get('notification_type')
        is_active = self.request.query_params.get('is_active')

        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active_bool)

        return queryset