import pika
import ssl
from django.conf import settings

def get_rabbitmq_connection():
    """
    Create and return a RabbitMQ connection with SSL if configured
    """
    ssl_options = None
    if getattr(settings, 'RABBITMQ_USE_SSL', False):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = getattr(settings, 'RABBITMQ_SSL_VERIFY_HOSTNAME', True)
        ssl_context.verify_mode = ssl.CERT_REQUIRED if getattr(settings, 'RABBITMQ_SSL_VERIFY', True) else ssl.CERT_NONE
        ssl_options = pika.SSLOptions(ssl_context)

    credentials = pika.PlainCredentials(
        username=settings.RABBITMQ_USERNAME,
        password=settings.RABBITMQ_PASSWORD
    )
    
    parameters = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT or 5672,
        virtual_host=getattr(settings, 'RABBITMQ_VHOST', '/'),
        credentials=credentials,
        ssl_options=ssl_options,
        connection_attempts=3,
        retry_delay=5,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    
    return pika.BlockingConnection(parameters)
