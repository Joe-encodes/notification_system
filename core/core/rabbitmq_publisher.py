from kombu import Connection, Exchange, Producer
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

def publish_notification(routing_key: str, message_data: dict):
    """
    Publishes a message to RabbitMQ.
    """
    broker_url = settings.CELERY_BROKER_URL # Get the RabbitMQ address from settings
    
    try:
        # 1. Connect to the broker
        with Connection(broker_url) as conn:
            with conn.channel() as channel:
                # 2. Declare the exchange within the channel context
                exchange = Exchange('notifications.direct', type='direct', durable=True)
                exchange.declare(channel)
                
                # 3. Create a producer (the sender) with the exchange
                producer = Producer(channel, exchange=exchange)
                
                # 4. Publish the message (kombu will serialize it automatically)
                producer.publish(
                    message_data,  # Pass dict directly, kombu serializes it
                    routing_key=routing_key, # This is 'email' or 'push'
                    serializer='json',
                    delivery_mode=2  # Persistent delivery mode
                )
                logger.info(f"Message published to {routing_key} queue: {message_data.get('request_id', 'unknown')}")
                return True
    except Exception as e:
        # If we can't connect to RabbitMQ, we log the error
        logger.error(f"Error publishing message to RabbitMQ: {e}")
        print(f"Error publishing message to RabbitMQ: {e}")
        return False
    