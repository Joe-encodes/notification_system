#!/bin/bash
# Comprehensive cURL Test Script for Production System
# Run this on the server: bash test_curl_commands.sh

BASE_URL="http://18.170.1.181:8000/api/v1"

echo "============================================================"
echo "  PRODUCTION SYSTEM cURL TEST SUITE"
echo "  Testing: $BASE_URL"
echo "============================================================"

# Test 1: Health Check
echo -e "\n[Test 1] Health Check Endpoint"
echo "----------------------------------------"
curl -X GET "$BASE_URL/health/" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | python3 -m json.tool || echo "Failed"

# Test 2: Get Users List
echo -e "\n[Test 2] User Service - List Users"
echo "----------------------------------------"
curl -X GET "$BASE_URL/users/" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | python3 -m json.tool || echo "Failed"

# Test 3: Get Templates List
echo -e "\n[Test 3] Template Service - List Templates"
echo "----------------------------------------"
curl -X GET "$BASE_URL/templates/" \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | python3 -m json.tool || echo "Failed"

# Test 4: Create User (if needed)
echo -e "\n[Test 4] Create Test User"
echo "----------------------------------------"
USER_PAYLOAD='{
  "email": "test@example.com",
  "password": "testpass123",
  "first_name": "Test",
  "last_name": "User",
  "push_token": "test_token_12345",
  "preferences": {
    "email": true,
    "push": true
  }
}'
curl -X POST "$BASE_URL/users/" \
  -H "Content-Type: application/json" \
  -d "$USER_PAYLOAD" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | python3 -m json.tool || echo "Failed"

# Test 5: Get User by ID (you'll need to replace USER_ID)
echo -e "\n[Test 5] Get User by ID"
echo "----------------------------------------"
echo "Note: Replace USER_ID with actual user ID from Test 4"
# curl -X GET "$BASE_URL/users/USER_ID/" \
#   -H "Content-Type: application/json" \
#   -w "\nHTTP Status: %{http_code}\n" \
#   -s | python3 -m json.tool || echo "Failed"

# Test 6: Email Notification
echo -e "\n[Test 6] Send Email Notification"
echo "----------------------------------------"
EMAIL_PAYLOAD='{
  "notification_type": "email",
  "user_id": "REPLACE_WITH_USER_ID",
  "template_code": "welcome_email",
  "variables": {
    "name": "Test User",
    "link": "https://example.com/welcome"
  },
  "request_id": "test-email-'$(date +%s)'",
  "priority": 1
}'
echo "Note: Replace REPLACE_WITH_USER_ID with actual user ID"
# curl -X POST "$BASE_URL/notifications/" \
#   -H "Content-Type: application/json" \
#   -d "$EMAIL_PAYLOAD" \
#   -w "\nHTTP Status: %{http_code}\n" \
#   -s | python3 -m json.tool || echo "Failed"

# Test 7: Push Notification
echo -e "\n[Test 7] Send Push Notification"
echo "----------------------------------------"
PUSH_PAYLOAD='{
  "notification_type": "push",
  "user_id": "REPLACE_WITH_USER_ID",
  "template_code": "welcome_email",
  "variables": {
    "name": "Test User",
    "link": "https://example.com/welcome"
  },
  "request_id": "test-push-'$(date +%s)'",
  "priority": 1
}'
echo "Note: Replace REPLACE_WITH_USER_ID with actual user ID"
# curl -X POST "$BASE_URL/notifications/" \
#   -H "Content-Type: application/json" \
#   -d "$PUSH_PAYLOAD" \
#   -w "\nHTTP Status: %{http_code}\n" \
#   -s | python3 -m json.tool || echo "Failed"

# Test 8: Idempotency Test
echo -e "\n[Test 8] Idempotency Test (Duplicate Request)"
echo "----------------------------------------"
IDEMPOTENT_PAYLOAD='{
  "notification_type": "email",
  "user_id": "REPLACE_WITH_USER_ID",
  "template_code": "welcome_email",
  "variables": {
    "name": "Test User",
    "link": "https://example.com"
  },
  "request_id": "idempotent-test-12345",
  "priority": 1
}'
echo "Sending first request..."
# curl -X POST "$BASE_URL/notifications/" \
#   -H "Content-Type: application/json" \
#   -d "$IDEMPOTENT_PAYLOAD" \
#   -w "\nHTTP Status: %{http_code}\n" \
#   -s | python3 -m json.tool || echo "Failed"

echo "Sending duplicate request with same request_id..."
# curl -X POST "$BASE_URL/notifications/" \
#   -H "Content-Type: application/json" \
#   -d "$IDEMPOTENT_PAYLOAD" \
#   -w "\nHTTP Status: %{http_code}\n" \
#   -s | python3 -m json.tool || echo "Failed"

# Test 9: Get Notification Status
echo -e "\n[Test 9] Get Notification Status"
echo "----------------------------------------"
echo "Note: Replace REQUEST_ID with actual request ID from Test 6 or 7"
# curl -X GET "$BASE_URL/notifications/email/status/?notification_id=REQUEST_ID" \
#   -H "Content-Type: application/json" \
#   -w "\nHTTP Status: %{http_code}\n" \
#   -s | python3 -m json.tool || echo "Failed"

# Test 10: Update Notification Status
echo -e "\n[Test 10] Update Notification Status"
echo "----------------------------------------"
STATUS_PAYLOAD='{
  "notification_id": "REQUEST_ID",
  "status": "delivered",
  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
  "error": null
}'
echo "Note: Replace REQUEST_ID with actual request ID"
# curl -X POST "$BASE_URL/notifications/email/status/" \
#   -H "Content-Type: application/json" \
#   -d "$STATUS_PAYLOAD" \
#   -w "\nHTTP Status: %{http_code}\n" \
#   -s | python3 -m json.tool || echo "Failed"

echo -e "\n============================================================"
echo "  Test Suite Complete"
echo "============================================================"

