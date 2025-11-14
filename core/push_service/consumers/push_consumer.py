import json
import logging
import pika
import os
import django
from django.conf import settings
from core.rabbitmq import get_rabbitmq_connection
from core.circuit_breaker import circuit_breaker
from core.retry import retry_with_backoff
from core.service_client import get_user_data, get_template_data

# Setup Django environment for standalone consumer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

logger = logging.getLogger(__name__)

class PushConsumer:
    def __init__(self):
        try:
            self.connection = get_rabbitmq_connection()
            self.channel = self.connection.channel()
            self.setup_queues()
        except Exception as e:
            logger.error(f"Failed to initialize push consumer: {str(e)}")
            raise
        
    def setup_queues(self):
        # Declare the main exchange
        self.channel.exchange_declare(
            exchange='notifications.direct',
            exchange_type='direct',
            durable=True
        )
        
        # Declare Dead Letter Exchange (DLX)
        self.channel.exchange_declare(
            exchange='notifications.dlx',
            exchange_type='direct',
            durable=True
        )
        
        # Declare DLQ first
        self.channel.queue_declare(
            queue='push.dlq',
            durable=True
        )
        
        # Bind DLQ to DLX
        self.channel.queue_bind(
            exchange='notifications.dlx',
            queue='push.dlq',
            routing_key='push.dlq'
        )
        
        # Declare the push queue with DLQ configuration
        self.channel.queue_declare(
            queue='push.queue',
            durable=True,
            arguments={
                'x-dead-letter-exchange': 'notifications.dlx',
                'x-dead-letter-routing-key': 'push.dlq'
            }
        )
        
        # Bind the queue to the exchange
        self.channel.queue_bind(
            exchange='notifications.direct',
            queue='push.queue',
            routing_key='push'
        )
        
        # Set up QoS
        self.channel.basic_qos(prefetch_count=1)
        
        # Set up consumer
        self.channel.basic_consume(
            queue='push.queue',
            on_message_callback=self.process_message,
            auto_ack=False
        )
    
    def _substitute_variables(self, template_content: str, variables: dict) -> str:
        """Substitute variables in template (e.g., {{name}} -> actual name)"""
        result = template_content
        for key, value in variables.items():
            result = result.replace(f'{{{{{key}}}}}', str(value))
        return result

    def _send_fcm_notification(self, push_token: str, title: str, body: str, data: dict = None):
        """
        Send push notification using Firebase Cloud Messaging (FCM).
        This is a placeholder - you'll need to configure FCM credentials.
        """
        try:
            from pyfcm import FCMNotification
            
            # Get FCM server key from settings
            fcm_server_key = getattr(settings, 'FCM_SERVER_KEY', None)
            if not fcm_server_key:
                raise Exception("FCM_SERVER_KEY not configured in settings")
            
            push_service = FCMNotification(api_key=fcm_server_key)
            
            result = push_service.notify_single_device(
                registration_id=push_token,
                message_title=title,
                message_body=body,
                data_message=data or {}
            )
            
            logger.info(f"FCM notification sent: {result}")
            return result
            
        except ImportError:
            logger.warning("pyfcm not installed. Using mock FCM notification.")
            # Mock implementation for development
            logger.info(f"Mock FCM: Sending to {push_token} - Title: {title}, Body: {body}")
            return {'success': True, 'mock': True}
        except Exception as e:
            logger.error(f"FCM notification failed: {str(e)}")
            raise

    def process_message(self, ch, method, properties, body):
        """Process push notification message from queue"""
        try:
            message = json.loads(body)
            logger.info(f"Processing push message: {message.get('request_id')}")
            
            request_id = message.get('request_id')
            user_id = message.get('user_id')
            template_code = message.get('template_code')
            variables = message.get('variables', {})
            
            # 1. Fetch user data (synchronous REST call with circuit breaker)
            user_data = get_user_data(user_id)
            if not user_data or not user_data.get('success'):
                raise Exception(f"Failed to fetch user data for {user_id}")
            
            user_info = user_data.get('data', {})
            push_token = user_info.get('push_token')
            user_language = user_info.get('preferences', {}).get('language', 'en')
            
            if not push_token:
                raise Exception(f"User {user_id} has no push token")
            
            # 2. Fetch template (synchronous REST call with circuit breaker)
            template_data = get_template_data(template_code, language=user_language)
            if not template_data or not template_data.get('success'):
                raise Exception(f"Failed to fetch template {template_code}")
            
            template_info = template_data.get('data', {})
            if template_info.get('notification_type') != 'push':
                raise Exception(f"Template {template_code} is not a push template")
            
            # 3. Get template content and subject (title for push)
            template_content = template_info.get('content', '')
            template_title = template_info.get('subject', 'Notification')
            
            # 4. Merge user data with provided variables
            merged_variables = {
                'name': user_info.get('first_name', '') + ' ' + user_info.get('last_name', ''),
                **variables
            }
            
            # 5. Substitute variables in template
            push_body = self._substitute_variables(template_content, merged_variables)
            push_title = self._substitute_variables(template_title, merged_variables)
            
            # 6. Prepare notification data
            notification_data = {
                'request_id': request_id,
                'user_id': user_id,
                **message.get('metadata', {})
            }
            
            # 7. Send push notification
            self._send_fcm_notification(
                push_token=push_token,
                title=push_title,
                body=push_body,
                data=notification_data
            )
            
            # 8. Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Push notification sent successfully to {user_id} (request_id: {request_id})")
            
        except Exception as e:
            logger.error(f"Error processing push notification: {str(e)}")
            
            # Check if max retries reached
            if method.delivery_info.get('redelivered', False):
                # Move to DLQ
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                logger.warning(f"Message moved to DLQ: {str(e)}")
            else:
                # Retry
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.warning(f"Message requeued for retry: {str(e)}")
    
    def start_consuming(self):
        logger.info("Starting push consumer...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
        finally:
            self.connection.close()

if __name__ == "__main__":
    consumer = PushConsumer()
    consumer.start_consuming()


