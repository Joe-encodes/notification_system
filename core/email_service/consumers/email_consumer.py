import json
import logging
import pika
import os
import django
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags
from core.core.rabbitmq import get_rabbitmq_connection
from core.circuit_breaker import circuit_breaker
from core.retry import retry_with_backoff
from core.core.service_client import get_user_data, get_template_data

# Setup Django environment for standalone consumer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from template_app.models import TemplateModel

logger = logging.getLogger(__name__)
User = get_user_model()

class EmailConsumer:
    def __init__(self):
        try:
            self.connection = get_rabbitmq_connection()
            self.channel = self.connection.channel()
            self.setup_queues()
        except Exception as e:
            logger.error(f"Failed to initialize email consumer: {str(e)}")
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
            queue='email.dlq',
            durable=True
        )
        
        # Bind DLQ to DLX
        self.channel.queue_bind(
            exchange='notifications.dlx',
            queue='email.dlq',
            routing_key='email.dlq'
        )
        
        # Declare the email queue with DLQ configuration
        self.channel.queue_declare(
            queue='email.queue',
            durable=True,
            arguments={
                'x-dead-letter-exchange': 'notifications.dlx',
                'x-dead-letter-routing-key': 'email.dlq'
            }
        )
        
        # Bind the queue to the exchange
        self.channel.queue_bind(
            exchange='notifications.direct',
            queue='email.queue',
            routing_key='email'
        )
        
        # Set up QoS
        self.channel.basic_qos(prefetch_count=1)
        
        # Set up consumer
        self.channel.basic_consume(
            queue='email.queue',
            on_message_callback=self.process_message,
            auto_ack=False
        )
    
    def _substitute_variables(self, template_content: str, variables: dict) -> str:
        """Substitute variables in template (e.g., {{name}} -> actual name)"""
        result = template_content
        for key, value in variables.items():
            result = result.replace(f'{{{{{key}}}}}', str(value))
        return result

    def process_message(self, ch, method, properties, body):
        """Process email notification message from queue"""
        try:
            message = json.loads(body)
            logger.info(f"Processing email message: {message.get('request_id')}")
            
            request_id = message.get('request_id')
            user_id = message.get('user_id')
            template_code = message.get('template_code')
            variables = message.get('variables', {})
            
            # 1. Fetch user data (synchronous REST call with circuit breaker)
            @retry_with_backoff(retries=3, backoff_in_seconds=1, max_backoff=10)
            def fetch_user():
                return get_user_data(user_id)
            
            user_data = fetch_user()
            if not user_data or not user_data.get('success'):
                raise Exception(f"Failed to fetch user data for {user_id}")
            
            user_info = user_data.get('data', {})
            user_email = user_info.get('email')
            user_language = user_info.get('preferences', {}).get('language', 'en')
            
            if not user_email:
                raise Exception(f"User {user_id} has no email address")
            
            # 2. Fetch template (synchronous REST call with circuit breaker)
            @retry_with_backoff(retries=3, backoff_in_seconds=1, max_backoff=10)
            def fetch_template():
                return get_template_data(template_code, language=user_language)
            
            template_data = fetch_template()
            if not template_data or not template_data.get('success'):
                raise Exception(f"Failed to fetch template {template_code}")
            
            template_info = template_data.get('data', {})
            if template_info.get('notification_type') != 'email':
                raise Exception(f"Template {template_code} is not an email template")
            
            # 3. Get template content and subject
            template_content = template_info.get('content', '')
            template_subject = template_info.get('subject', 'Notification')
            
            # 4. Merge user data with provided variables
            merged_variables = {
                'name': user_info.get('first_name', '') + ' ' + user_info.get('last_name', ''),
                **variables
            }
            
            # 5. Substitute variables in template
            email_body = self._substitute_variables(template_content, merged_variables)
            email_subject = self._substitute_variables(template_subject, merged_variables)
            
            # 6. Send email using Django's send_mail
            send_mail(
                subject=email_subject,
                message=strip_tags(email_body),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=[user_email],
                html_message=email_body,
                fail_silently=False
            )
            
            # 7. Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Email sent successfully to {user_email} (request_id: {request_id})")
            
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            
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
        logger.info("Starting email consumer...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
        finally:
            self.connection.close()

if __name__ == "__main__":
    consumer = EmailConsumer()
    consumer.start_consuming()
