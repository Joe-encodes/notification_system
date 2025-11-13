import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self, message="Hello World"):
    print(f'Debug Task Received: {message}')
    print(f'Task Request: {self.request!r}')
    return f"Processed: {message}"
