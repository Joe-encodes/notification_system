from kombu import Connection, Exchange, Producer
from django.conf import settings
import json

NOTIFICATION_EXCHANGE = Exchange('notifications.direct', 'direct', durable=True)

def publish_notification(routing_key: str, message_data: dict):
    """
    Publishes a message to RabbitMQ.
    """
    broker_url = settings.CELERY_BROKER_URL # Get the RabbitMQ address from settings
    
    try:
        # 1. Connect to the broker
        with Connection(broker_url) as conn:
            with conn.channel() as channel:
                # 2. Declare the exchange (make sure it exists)
                NOTIFICATION_EXCHANGE.declare(channel)
                
                # 3. Create a producer (the sender)
                producer = Producer(channel, NOTIFICATION_EXCHANGE)
                
                # 4. Publish the message
                producer.publish(
                    json.dumps(message_data),
                    routing_key=routing_key, # This is 'email' or 'push'
                    serializer='json',
                    delivery_mode='persistent' # Ensures the message survives a RabbitMQ restart
                )
                return True
    except Exception as e:
        # If we can't connect to RabbitMQ, we log the error
        print(f"Error publishing message to RabbitMQ: {e}")
        return False
    