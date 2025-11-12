import json
import logging
import pika
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from core.rabbitmq import get_rabbitmq_connection
from core.circuit_breaker import circuit_breaker
from core.retry import retry_with_backoff

logger = logging.getLogger(__name__)

class EmailConsumer:
    def __init__(self):
        self.connection = get_rabbitmq_connection()
        self.channel = self.connection.channel()
        self.setup_queues()
        
    def setup_queues(self):
        # Declare the main exchange
        self.channel.exchange_declare(
            exchange='notifications.direct',
            exchange_type='direct',
            durable=True
        )
        
        # Declare the email queue
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
        
        # Declare DLQ
        self.channel.queue_declare(
            queue='email.dlq',
            durable=True
        )
        
        # Set up QoS
        self.channel.basic_qos(prefetch_count=1)
        
        # Set up consumer
        self.channel.basic_consume(
            queue='email.queue',
            on_message_callback=self.process_message,
            auto_ack=False
        )
    
    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    def process_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            logger.info(f"Processing email message: {message}")
            
            # Extract data
            to_email = message.get('to')
            subject = message.get('subject')
            template_name = message.get('template_name')
            context = message.get('context', {})
            
            # Render email template
            html_message = render_to_string(f'emails/{template_name}.html', context)
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Email sent to {to_email}")
            
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
