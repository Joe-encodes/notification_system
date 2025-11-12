from celery import shared_task
from core.service_client import get_user_data, get_template_data
import time # Used to simulate network latency and failures
import random
import json


#Helper function for worker logic
def simulate_external_service_call(service_name):
    """Simulates a call to an external service (e.g., SendGrid, FCM)."""
    # Simulate network latency
    time.sleep(random.uniform(0.1, 0.5))
    # Simulate a transient failure 10% of the time
    if random.random() < 0.1:
        raise ConnectionError(f"Simulated transient connection error to {service_name}.")
    # Simulate a permanent failure 5% of the time
    if random.random() < 0.5:
        raise ValueError(f"Simulated permanent authentication error with {service_name}.")
    
    return True

def render_template(content, data):
    """Renders the template content by replacing placeholders with actual data."""
    rendered_content = content
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}"
        rendered_content = content.replace(placeholder, str(value))
    return rendered_content

# --- Celery Tasks (The Microservices) ---

@shared_task(
    bind=True,
    queue='email', # <-- 1. Queue Listener
    autoretry_for=(ConnectionError,), # <-- 2. Retry System Trigger
    retry_backoff=True, # <-- 3. Exponential Backoff
    max_retries=5 # <-- 4. Max Retries
)

def send_email_notification(self, payload_json):
    """
    Email Service: Consumes messages from the email queue and sends emails.
    """
    try:
        payload = json.loads(payload_json)
        user_id = payload['user_id']
        template_name = payload['template_name']
        template_data = payload['template_data']
        
        print(f"EMAIL WORKER: Processing request for user {user_id} with template {template_name}. Attempt {self.request.retries + 1}")

        # 1. Fetch User Data (Synchronous call to User Service)
        user_response = get_user_data(user_id)
        if not user_response or not user_response.get('success'):
            # If user data is unavailable, it's a permanent failure for this task
            raise ValueError(f"User data not found for user_id: {user_id}")
        
        user_data = user_response['data']
        
        # Check user preference (Idempotency/Filtering)
        if not user_data.get('prefers_email'):
            print(f"EMAIL WORKER: User {user_id} prefers not to receive emails. Task complete (filtered).")
            return "Filtered by user preference"

        # 2. Fetch Template Data (Synchronous call to Template Service)
        template_response = get_template_data(template_name)
        if not template_response or not template_response.get('success'):
            raise ValueError(f"Template not found for name: {template_name}")
            
        template = template_response['data']
        
        # 3. Render Template
        email_subject = render_template(template.get('subject', 'Notification'), template_data)
        email_body = render_template(template.get('content', 'Empty Content'), template_data)
        recipient_email = user_data['email']
        
        # 4. Simulate Sending Email (External Service Call)
        simulate_external_service_call("SendGrid/SMTP")
        
        print(f"EMAIL WORKER: Successfully sent email to {recipient_email} with subject: {email_subject}")
        return "Email sent successfully"

    except ConnectionError as exc:
        # This is a transient error, Celery will automatically retry with backoff
        print(f"EMAIL WORKER: Transient error encountered. Retrying...")
        raise self.retry(exc=exc)
        
    except ValueError as exc:
        # This is a permanent error (e.g., bad user_id, bad template_name, auth error)
        # We log it and let the task fail, which can be routed to a Dead Letter Queue (DLQ)
        print(f"EMAIL WORKER: Permanent error encountered. Not retrying. Error: {exc}")
        # In a real system, we would explicitly route this to a DLQ
        return f"Permanent failure: {exc}"
        
    except Exception as exc:
        # Catch all other unexpected errors
        print(f"EMAIL WORKER: Unexpected error: {exc}")
        return f"Unexpected failure: {exc}"


@shared_task(
    bind=True,
    queue='push', # Consume from the 'push' queue
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    max_retries=5
)
def send_push_notification(self, payload_json):
    """
    Push Service: Consumes messages from the push queue and sends push notifications.
    """
    try:
        payload = json.loads(payload_json)
        user_id = payload['user_id']
        template_name = payload['template_name']
        template_data = payload['template_data']
        
        print(f"PUSH WORKER: Processing request for user {user_id} with template {template_name}. Attempt {self.request.retries + 1}")

        # 1. Fetch User Data
        user_response = get_user_data(user_id)
        if not user_response or not user_response.get('success'):
            raise ValueError(f"User data not found for user_id: {user_id}")
        
        user_data = user_response['data']
        
        # Check user preference and token
        if not user_data.get('prefers_push') or not user_data.get('push_token'):
            print(f"PUSH WORKER: User {user_id} prefers not to receive push or has no token. Task complete (filtered).")
            return "Filtered by user preference/missing token"

        # 2. Fetch Template Data
        template_response = get_template_data(template_name)
        if not template_response or not template_response.get('success'):
            raise ValueError(f"Template not found for name: {template_name}")
            
        template = template_response['data']
        
        # 3. Render Template
        push_title = render_template(template.get('subject', 'Notification'), template_data)
        push_body = render_template(template.get('content', 'Empty Content'), template_data)
        device_token = user_data['push_token']
        
        # 4. Simulate Sending Push (External Service Call)
        simulate_external_service_call("FCM/OneSignal")
        
        print(f"PUSH WORKER: Successfully sent push to device {device_token} with title: {push_title}")
        return "Push sent successfully"

    except ConnectionError as exc:
        print(f"PUSH WORKER: Transient error encountered. Retrying...")
        raise self.retry(exc=exc)
        
    except ValueError as exc:
        print(f"PUSH WORKER: Permanent error encountered. Not retrying. Error: {exc}")
        return f"Permanent failure: {exc}"
        
    except Exception as exc:
        print(f"PUSH WORKER: Unexpected error: {exc}")
        return f"Unexpected failure: {exc}"