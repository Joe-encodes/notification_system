from rest_framework.views import APIView
from rest_framework import status
from .serializers import NotificationRequestSerializer, NotificationStatusSerializer
from core.rabbitmq_publisher import publish_notification
from core.redis_client import check_and_set_idempotency_key, redis_client
from core.utils import standardized_response
import uuid
from django.db import connections
from django.conf import settings
from datetime import datetime

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
        request_id = data.get('request_id') or str(uuid.uuid4())
        notification_type = data.get('notification_type')

        # 2. Idempotency check using request_id
        if not check_and_set_idempotency_key(request_id):
            return standardized_response(
                success=True, 
                message="Duplicate request detected. Notification already processed.",
                http_status=status.HTTP_200_OK
            )
        
        # 3. Prepare message payload matching task specification
        message_payload = {
            'request_id': request_id,
            'user_id': str(data.get('user_id')),
            'template_code': data.get('template_code'),
            'variables': data.get('variables', {}),
            'priority': data.get('priority', 0),
            'metadata': data.get('metadata', {})
        }
        
        # 4. Route to appropriate queue based on notification_type
        published = False
        if notification_type in ['email', 'push']:
            published = publish_notification(notification_type, message_payload)
        
        # 5. Final Response
        if published:
            return standardized_response(
                success=True, 
                data={'request_id': request_id},
                message="Notification request accepted and queued.",
                http_status=status.HTTP_202_ACCEPTED
            )
        return standardized_response(
            success=False,
            error="Failed to queue notification.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class NotificationStatusView(APIView):
    """
    Endpoint to update notification status.
    POST /api/v1/notifications/{notification_type}/status/
    {
        notification_id: str,
        status: NotificationStatus,
        timestamp: Optional[datetime],
        error: Optional[str]
    }
    """
    def post(self, request, notification_type, *args, **kwargs):
        if notification_type not in ['email', 'push']:
            return standardized_response(
                success=False,
                error=f"Invalid notification type: {notification_type}",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = NotificationStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return standardized_response(
                success=False,
                error=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        notification_id = data.get('notification_id')
        status_value = data.get('status')
        timestamp = data.get('timestamp') or datetime.now().isoformat()
        error_message = data.get('error')
        
        # Store status in Redis (or database in production)
        if redis_client:
            status_key = f"notification_status:{notification_type}:{notification_id}"
            status_data = {
                'status': status_value,
                'timestamp': timestamp,
                'error': error_message
            }
            redis_client.hset(status_key, mapping=status_data)
            redis_client.expire(status_key, 86400)  # 24 hours
        
        return standardized_response(
            success=True,
            data={'notification_id': notification_id, 'status': status_value},
            message="Notification status updated successfully.",
            http_status=status.HTTP_200_OK
        )
    
    def get(self, request, notification_type, *args, **kwargs):
        """Get notification status by notification_id"""
        notification_id = request.query_params.get('notification_id')
        if not notification_id:
            return standardized_response(
                success=False,
                error="notification_id query parameter is required",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        if redis_client:
            status_key = f"notification_status:{notification_type}:{notification_id}"
            status_data = redis_client.hgetall(status_key)
            if status_data:
                return standardized_response(
                    success=True,
                    data=status_data,
                    message="Notification status retrieved.",
                    http_status=status.HTTP_200_OK
                )
        
        return standardized_response(
            success=False,
            error="Notification status not found",
            http_status=status.HTTP_404_NOT_FOUND
        )