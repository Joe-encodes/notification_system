from django.core.management.base import BaseCommand
import logging
from email_service.consumers.email_consumer import EmailConsumer

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Starts the RabbitMQ email consumer'

    def handle(self, *args, **options):
        """Handle the command execution"""
        self.stdout.write(self.style.SUCCESS('Starting email consumer...'))
        
        try:
            consumer = EmailConsumer()
            consumer.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Stopping email consumer...'))
        except Exception as e:
            logger.error(f"Error in email consumer: {str(e)}")
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
