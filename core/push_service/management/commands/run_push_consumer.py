from django.core.management.base import BaseCommand
from push_service.consumers.push_consumer import PushConsumer

class Command(BaseCommand):
    help = 'Start the push notification consumer'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting push notification consumer...'))
        consumer = PushConsumer()
        consumer.start_consuming()


