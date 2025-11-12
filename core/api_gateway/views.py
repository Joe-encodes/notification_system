from rest_framework.views import APIView
from rest_framework import status
from .serializers import NotificationRequestSerializer
from core.rabbitmq_publisher import publish_notification
from core.redis_client import check_and_set_idempotency_key
from core.utils import standardized_response
import uuid
from django.db import connections
from django.conf import settings

# Initialize Redis client if not already done
try:
    from core.redis_client import redis_client
except ImportError:
    redis_client = None

class HealthCheckView(APIView):
    """
    Health check endpoint to monitor service status.
    Checks connectivity to the database and Redis.
    """
    def get(self, request, *args, **kwargs):
        status_checks = {}
        overall_status = status.HTTP_200_OK
        
        # 1. Database Check
        db_ok = True
        try:
            db_conn = connections['default']
            db_conn.cursor()
            status_checks['database'] = 'OK'
        except Exception as e:
            db_ok = False
            status_checks['database'] = f'Error: {e}'
            overall_status = status.HTTP_503_SERVICE_UNAVAILABLE
            
        # 2. Redis Check
        redis_ok = True
        if redis_client:
            try:
                redis_client.ping()
                status_checks['redis'] = 'OK'
            except Exception as e:
                redis_ok = False
                status_checks['redis'] = f'Error: {e}'
                overall_status = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_checks['redis'] = 'Disabled (Client not initialized)'

        message = "All services are healthy." if overall_status == status.HTTP_200_OK else "One or more services are unhealthy."

        return standardized_response(
            success=overall_status == status.HTTP_200_OK,
            data=status_checks,
            message=message,
            http_status=overall_status
        )

class NotificationAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # 1. Validate incoming data
        serializer = NotificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return standardized_response(
                success=False, 
                error=serializer.errors, 
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        idempotency_key = data.get('idempotency_key') or str(uuid.uuid4())

        # 2. Idempotency check
        if not check_and_set_idempotency_key(idempotency_key):
            return standardized_response(
                success=True, 
                message="Duplicate request detected. Notification already processed.",
                http_status=status.HTTP_200_OK
            )
        
        # 3. Prepare message payload
        message_payload = {
            'idempotency_key': idempotency_key,
            'user_id': str(data.get('user_id')),
            'template_code': data.get('template_code'),
            'variables': data.get('variables', {}),
            'metadata': data.get('metadata', {})
        }
        
        # 4. Routing Logic
        notification_types = data.get('notification_types', ['email', 'push'])
        if isinstance(notification_types, str):
            notification_types = [notification_types]
        
        published_count = 0
        for notif_type in notification_types:
            if notif_type in ['email', 'push']:
                if publish_notification(notif_type, message_payload):
                    published_count += 1
        
        # 5. Final Response
        if published_count > 0:
            return standardized_response(
                success=True, 
                data={'idempotency_key': idempotency_key},
                message="Notification request accepted and queued.",
                http_status=status.HTTP_202_ACCEPTED
            )
        return standardized_response(
            success=False,
            error="Failed to queue notification. No valid notification types specified.",
            http_status=status.HTTP_400_BAD_REQUEST
        )