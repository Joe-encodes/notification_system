import requests
from django.conf import settings
from core.utils import standardized_response
import time

# --- Circuit Breaker State (Conceptual) ---
# This is a simple Python dictionary that tracks failures.
CIRCUIT_STATE = {
    'user_service': {'state': 'CLOSED', 'failure_count': 0, 'last_failure_time': 0},
    'template_service': {'state': 'CLOSED', 'failure_count': 0, 'last_failure_time': 0},
    'MAX_FAILURES': 3,
    'RESET_TIMEOUT': 60 # seconds
}

def check_circuit(service_name):
    """Checks if the circuit is OPEN (tripped) or CLOSED (safe to use)."""
    state = CIRCUIT_STATE[service_name]
    if state['state'] == 'OPEN':
        # If the circuit is OPEN, check if the timeout has passed
        if time.time() > state['last_failure_time'] + CIRCUIT_STATE['RESET_TIMEOUT']:
            state['state'] = 'HALF-OPEN' # Try one request
            print(f"CIRCUIT BREAKER: {service_name} transitioned to HALF-OPEN.")
            return True # Allow one test request
        else:
            print(f"CIRCUIT BREAKER: {service_name} is OPEN. Request blocked.")
            return False
    
    return True # CLOSED or HALF-OPEN

def record_success(service_name):
    """Records a successful call."""
    state = CIRCUIT_STATE[service_name]
    if state['state'] == 'HALF-OPEN':
        state['state'] = 'CLOSED'
        state['failure_count'] = 0
        print(f"CIRCUIT BREAKER: {service_name} transitioned to CLOSED.")
    elif state['state'] == 'CLOSED':
        state['failure_count'] = 0

def record_failure(service_name):
    """Called when a request fails. Increments the failure count."""
    state = CIRCUIT_STATE[service_name]
    state['failure_count'] += 1
    state['last_failure_time'] = time.time()
    
    if state['failure_count'] >= CIRCUIT_STATE['MAX_FAILURES'] and state['state'] != 'OPEN':
        state['state'] = 'OPEN' # Trip the circuit!
        print(f"CIRCUIT BREAKER: {service_name} transitioned to OPEN. Requests will be blocked.")

# --- Service Client Functions ---

# Base URL for internal service communication
BASE_URL = getattr(settings, 'INTERNAL_API_BASE_URL', 'http://localhost:8000/api/v1')
SERVICE_TIMEOUT_SECONDS = getattr(settings, 'SERVICE_CLIENT_TIMEOUT', 5)

def get_user_data(user_id: str) -> dict:
    """Fetches user data from the User Service with Circuit Breaker logic."""
    service_name = 'user_service'
    
    if not check_circuit(service_name):
        return {'success': False, 'error': 'Circuit breaker is OPEN'} # Request blocked by circuit breaker
    
    url = f"{BASE_URL}/users/{user_id}/"
    
    try:
        response = requests.get(url, timeout=SERVICE_TIMEOUT_SECONDS)
        response.raise_for_status() # Raise an error for bad responses
        record_success(service_name)
        result = response.json()
        # Ensure it follows standardized format
        if isinstance(result, dict) and 'success' in result:
            return result
        return {'success': True, 'data': result}
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user data for {user_id}: {e}")
        record_failure(service_name)
        return {'success': False, 'error': str(e)}
    
def get_template_data(template_code: str, language: str = 'en'):
    """Fetches template data from the Template Service with Circuit Breaker protection."""
    service_name = 'template_service'
    if not check_circuit(service_name):
        return {'success': False, 'error': 'Circuit breaker is OPEN'} # Request blocked by circuit breaker

    url = f"{BASE_URL}/templates/{template_code}/"
    params = {'language': language} if language else {}
    try:
        response = requests.get(url, params=params, timeout=SERVICE_TIMEOUT_SECONDS)
        response.raise_for_status()
        record_success(service_name)
        result = response.json()
        # Ensure it follows standardized format
        if isinstance(result, dict) and 'success' in result:
            return result
        return {'success': True, 'data': result}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching template data for {template_code}: {e}")
        record_failure(service_name)
        return {'success': False, 'error': str(e)}
