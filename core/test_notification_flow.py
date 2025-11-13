#!/usr/bin/env python
"""
Test script for the notification system.
This demonstrates the full end-to-end flow for Stage 4.
"""
import os
import sys
import django
import requests
import json
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from template_app.models import TemplateModel
from core.celery import debug_task

User = get_user_model()

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health_endpoint():
    """Test the health check endpoint"""
    print_section("Testing Health Endpoint")
    try:
        response = requests.get('http://localhost:8000/api/v1/health/')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def create_test_user():
    """Create a test user for notifications"""
    print_section("Creating Test User")
    try:
        user, created = User.objects.get_or_create(
            email='test@example.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'User',
                'push_token': 'test_push_token_12345'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"✅ Created user: {user.email} (ID: {user.user_id})")
        else:
            print(f"✅ User already exists: {user.email} (ID: {user.user_id})")
        return user
    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        return None

def create_test_template():
    """Create a test email template"""
    print_section("Creating Test Template")
    try:
        template, created = TemplateModel.objects.get_or_create(
            template_code='welcome_email',
            notification_type='email',
            language='en',
            defaults={
                'subject': 'Welcome {{name}}!',
                'content': 'Hello {{name}}, welcome to our notification system! Click here: {{link}}',
                'is_active': True,
                'required_variables': ['name', 'link']
            }
        )
        if created:
            print(f"✅ Created template: {template.template_code}")
        else:
            print(f"✅ Template already exists: {template.template_code}")
        return template
    except Exception as e:
        print(f"❌ Error creating template: {str(e)}")
        return None

def test_celery_task():
    """Test Celery task execution"""
    print_section("Testing Celery Task")
    try:
        result = debug_task.delay(message="Hello from test script!")
        print(f"✅ Task sent to queue. Task ID: {result.id}")
        print(f"   Check worker logs to see task execution")
        return True
    except Exception as e:
        print(f"❌ Error sending task: {str(e)}")
        return False

def test_notification_api():
    """Test the notification API endpoint"""
    print_section("Testing Notification API")
    try:
        # Get a user first
        user = User.objects.first()
        if not user:
            print("❌ No users found. Please create a user first.")
            return False
        
        # Create notification request
        payload = {
            'notification_type': 'email',
            'user_id': str(user.user_id),
            'template_code': 'welcome_email',
            'variables': {
                'name': f"{user.first_name} {user.last_name}",
                'link': 'https://example.com/welcome'
            },
            'request_id': str(uuid.uuid4()),
            'priority': 1
        }
        
        response = requests.post(
            'http://localhost:8000/api/v1/notifications/',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code in [200, 202]:
            print("✅ Notification request accepted and queued!")
            print("   Check email_consumer logs to see message processing")
            return True
        else:
            print("❌ Notification request failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("  NOTIFICATION SYSTEM TEST SUITE")
    print("  Stage 4: Distributed Notification System")
    print("="*60)
    
    results = []
    
    # Test 1: Health endpoint
    results.append(("Health Endpoint", test_health_endpoint()))
    
    # Test 2: Create test data
    user = create_test_user()
    template = create_test_template()
    results.append(("Test Data Creation", user is not None and template is not None))
    
    # Test 3: Celery task
    results.append(("Celery Task", test_celery_task()))
    
    # Test 4: Notification API
    if user and template:
        results.append(("Notification API", test_notification_api()))
    
    # Summary
    print_section("Test Summary")
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your notification system is working!")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")

if __name__ == '__main__':
    main()

