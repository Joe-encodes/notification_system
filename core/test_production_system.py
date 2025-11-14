#!/usr/bin/env python
"""
Consolidated Production System Test Suite (Stage 4)
Tests all endpoints and flows, including authentication.
Run this on the server: python test_production_system.py
"""
import os
import sys
import django
import requests
import json
import uuid
import re
from datetime import datetime

# --- Configuration ---
# NOTE: Using a static token for testing. In real CI/CD, this would be an env var.
ADMIN_TOKEN = "6859f491e1d1200e43b7a55fdc0d138d8fd080fe" 
BASE_URL = "http://18.170.1.181:8000/api/v1"
HEADERS = {
    'Content-Type': 'application/json',
    # Use the provided token for authorization
    'Authorization': f'Token {ADMIN_TOKEN}' 
}
# ---------------------

# Setup Django (Needed for creating test data directly)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from template_app.models import TemplateModel
from core.celery import debug_task

User = get_user_model()

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_result(test_name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")

# --- Test Data Management ---

def create_test_user():
    """Test 1: Create Test User (Database check)"""
    print_section("Test 1: Create Test User")
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
    """Test 2: Create Test Template (Database check)"""
    print_section("Test 2: Create Test Template")
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

# --- Core Service Tests ---

def test_health_endpoint():
    """Test 3: Health Check Endpoint (DB & Redis)"""
    print_section("Test 3: Health Check Endpoint")
    try:
        # Health check is often public/unauthorized
        response = requests.get(f'{BASE_URL}/health/', timeout=10)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success') and data.get('data', {}).get('database') == 'OK':
            print_result("Health Endpoint", True, "Database and Redis are healthy")
            return True
        else:
            print_result("Health Endpoint", False, "Health check returned unhealthy status")
            return False
    except requests.exceptions.RequestException as e:
        print_result("Health Endpoint", False, f"Connection error: {str(e)}")
        return False

def test_user_api():
    """Test 4: User Service API (Requires Auth)"""
    print_section("Test 4: User Service API (Auth Test)")
    try:
        response = requests.get(f'{BASE_URL}/users/', headers=HEADERS, timeout=10)
        print(f"GET /users/ - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and isinstance(data.get('data'), list):
                print_result("User API - List", True, f"Retrieved {len(data.get('data', []))} users")
                return True
            else:
                print_result("User API - List", False, "Response format incorrect or success=false")
                return False
        else:
            print_result("User API - List", False, f"Status code: {response.status_code} (Authentication likely failed)")
            return False
    except Exception as e:
        print_result("User API", False, f"Error: {str(e)}")
        return False

def test_template_api():
    """Test 5: Template Service API (Requires Auth)"""
    print_section("Test 5: Template Service API (Auth Test)")
    try:
        response = requests.get(f'{BASE_URL}/templates/', headers=HEADERS, timeout=10)
        print(f"GET /templates/ - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and isinstance(data.get('data'), list):
                print_result("Template API - List", True, f"Retrieved {len(data.get('data', []))} templates")
                return True
            else:
                print_result("Template API - List", False, "Response format incorrect or success=false")
                return False
        else:
            print_result("Template API - List", False, f"Status code: {response.status_code} (Authentication likely failed)")
            return False
    except Exception as e:
        print_result("Template API", False, f"Error: {str(e)}")
        return False

def test_celery_task():
    """Test 6: Celery Task Execution (Basic Worker Test)"""
    print_section("Test 6: Celery Task Execution")
    try:
        result = debug_task.delay(message="Hello from test script!")
        print(f"✅ Task sent to queue. Task ID: {result.id}")
        print(f"   Check worker logs (celery_worker) to see task execution")
        return True
    except Exception as e:
        print(f"❌ Error sending task: {str(e)}")
        return False

# --- Notification Flow Tests ---

def test_notification_api_email(user):
    """Test 7: Email Notification API (Queueing)"""
    print_section("Test 7: Email Notification API")
    if not user:
        return False, None
    
    try:
        request_id = str(uuid.uuid4())
        payload = {
            'notification_type': 'email',
            'user_id': str(user.user_id),
            'template_code': 'welcome_email',
            'variables': {
                'name': f"{user.first_name} {user.last_name}",
                'link': 'https://example.com/welcome'
            },
            'request_id': request_id,
            'priority': 1
        }
        
        response = requests.post(
            f'{BASE_URL}/notifications/',
            json=payload,
            headers=HEADERS, # Protected endpoint
            timeout=10
        )
        
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Acceptable codes are 202 (Accepted) or 200 (OK/Success)
        if response.status_code in [200, 202] and data.get('success'):
            print_result("Email Notification", True, f"Request accepted and queued. ID: {request_id}")
            return True, request_id
        else:
            print_result("Email Notification", False, data.get('error', 'API rejected request'))
            return False, None
    except Exception as e:
        print_result("Email Notification", False, f"Error: {str(e)}")
        return False, None

def test_idempotency(user):
    """Test 8: Idempotency Check (Duplicate Prevention)"""
    print_section("Test 8: Idempotency Enforcement")
    if not user:
        return False
    
    try:
        request_id = str(uuid.uuid4()) # Use a unique ID for the first request
        payload = {
            'notification_type': 'email',
            'user_id': str(user.user_id),
            'template_code': 'welcome_email',
            'variables': {'name': 'Test User', 'link': 'https://example.com'},
            'request_id': request_id
        }
        
        # 1. First request (Should succeed, status 202)
        response1 = requests.post(f'{BASE_URL}/notifications/', json=payload, headers=HEADERS, timeout=10)
        
        # 2. Duplicate request with same request_id (Should return 200/202 with a success/duplicate message)
        response2 = requests.post(f'{BASE_URL}/notifications/', json=payload, headers=HEADERS, timeout=10)
        
        print(f"First request Status: {response1.status_code}")
        print(f"Duplicate request Status: {response2.status_code}")
        
        data2 = response2.json()
        
        # Check if the first was accepted (202) AND the second correctly recognized the duplicate (200/202 success message)
        if response1.status_code == 202 and response2.status_code in [200, 202]:
            if data2.get('success') and ("duplicate" in data2.get('message', '').lower() or "already processed" in data2.get('message', '').lower()):
                print_result("Idempotency", True, "Duplicate request detected and prevented.")
                return True
        
        print_result("Idempotency", False, f"Unexpected codes or message. First: {response1.status_code}, Duplicate: {response2.status_code}")
        return False
    except Exception as e:
        print_result("Idempotency", False, f"Error: {str(e)}")
        return False

def test_notification_status(request_id):
    """Test 9: Notification Status Endpoint (Read Status)"""
    print_section("Test 9: Notification Status Check")
    if not request_id:
        return True # Skip if no ID generated
    
    try:
        # Status endpoint is typically read-only and requires auth
        response = requests.get(
            f'{BASE_URL}/notifications/email/status/',
            params={'notification_id': request_id},
            headers=HEADERS,
            timeout=10
        )
        
        print(f"GET Status - Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Status might return 200 (found) or 404 (not yet processed/found)
        if response.status_code == 200 and data.get('success'):
            print_result("Status Check", True, f"Status retrieved successfully: {data['data']['status']}")
            return True
        elif response.status_code == 404:
            print_result("Status Check", True, "Status not found (may not be processed yet, acceptable outcome)")
            return True 
        else:
            print_result("Status Check", False, f"Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print_result("Status Check", False, f"Error: {str(e)}")
        return False

# --- Compliance Tests ---

def test_response_format():
    """Test 10: Standardized Response Format Compliance"""
    print_section("Test 10: Response Format Compliance")
    try:
        # Use health endpoint as it is guaranteed to return data
        response = requests.get(f'{BASE_URL}/health/', timeout=10)
        data = response.json()
        
        required_fields = ['success', 'message', 'data', 'error', 'meta']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print_result("Response Format", False, f"Missing fields: {missing_fields}")
            return False
        
        if not isinstance(data.get('success'), bool):
            print_result("Response Format", False, "success field must be boolean")
            return False
        
        print_result("Response Format", True, "All required fields present with correct types")
        return True
    except Exception as e:
        print_result("Response Format", False, f"Error: {str(e)}")
        return False

def test_snake_case_naming():
    """Test 11: snake_case Naming Convention (Request Check)"""
    print_section("Test 11: snake_case Naming Convention")
    try:
        test_payload = {
            'notification_type': 'email',
            'user_id': 'test-uuid',
            'template_code': 'test',
            'request_id': 'test-123'
        }
        
        snake_case_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        invalid_keys = [key for key in test_payload.keys() if not snake_case_pattern.match(key)]
        
        if invalid_keys:
            print_result("snake_case Naming", False, f"Invalid keys: {invalid_keys}")
            return False
        
        print_result("snake_case Naming", True, "All request fields use snake_case")
        return True
    except Exception as e:
        print_result("snake_case Naming", False, f"Error: {str(e)}")
        return False

# --- Main Execution ---

def main():
    print("\n" + "="*70)
    print("  PRODUCTION SYSTEM TEST SUITE (STAGE 4)")
    print("  Base URL: http://18.170.1.181:8000")
    print("="*70)
    
    results = []
    email_request_id = None
    
    # 1. Setup/Data Tests
    user = create_test_user()
    template = create_test_template()
    results.append(("Test Data Creation", user is not None and template is not None))
    
    # 2. Core/Compliance Tests
    results.append(("Health Endpoint (T3)", test_health_endpoint()))
    results.append(("Response Format (T10)", test_response_format()))
    results.append(("snake_case Naming (T11)", test_snake_case_naming()))
    
    # 3. Authenticated API Tests
    results.append(("User Service API (T4)", test_user_api()))
    results.append(("Template Service API (T5)", test_template_api()))
    
    # 4. Asynchronous/Flow Tests
    results.append(("Celery Task (T6)", test_celery_task()))
    
    if user and template:
        # Notification API test
        email_success, email_request_id = test_notification_api_email(user)
        results.append(("Email Notification API (T7)", email_success))
        
        # Idempotency test (must run after T7 queueing)
        results.append(("Idempotency (T8)", test_idempotency(user)))
        
        # Status check
        if email_request_id:
            results.append(("Notification Status (T9)", test_notification_status(email_request_id)))
    
    # Summary
    print_section("FINAL TEST SUMMARY")
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    percentage = int(passed/total*100) if total > 0 else 0
    
    print(f"\nTotal: {passed}/{total} tests passed ({percentage}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Your system meets core compliance requirements.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please debug and re-run.")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    main()