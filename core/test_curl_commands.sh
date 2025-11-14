#!/bin/bash
# Comprehensive cURL Test Script for Production System (Stage 4)
# Run this on the server: bash test_curl_commands.sh

BASE_URL="http://18.170.1.181:8000/api/v1"
ADMIN_TOKEN="6859f491e1d1200e43b7a55fdc0d138d8fd080fe"
AUTH_HEADER="Authorization: Token $ADMIN_TOKEN"
CONTENT_TYPE="Content-Type: application/json"

echo "============================================================"
echo "  PRODUCTION SYSTEM cURL TEST SUITE (AUTH ENABLED)"
echo "  Testing: $BASE_URL"
echo "  Using Token: $ADMIN_TOKEN"
echo "============================================================"

# Helper function for pretty printing and status check
function run_curl_test() {
  local METHOD=$1
  local ENDPOINT=$2
  local DATA=$3
  local NAME=$4
  local AUTH=$5

  echo -e "\n[$NAME] $METHOD $ENDPOINT"
  echo "----------------------------------------"
  
  HEADERS=("$CONTENT_TYPE")
  if [ "$AUTH" == "true" ]; then
      HEADERS+=("$AUTH_HEADER")
  fi

  if [ -z "$DATA" ]; then
    curl -X $METHOD "$BASE_URL$ENDPOINT" \
      -H "${HEADERS[@]}" \
      -w "\nHTTP Status: %{http_code}\n" \
      -s | python3 -m json.tool || echo "Failed"
  else
    curl -X $METHOD "$BASE_URL$ENDPOINT" \
      -H "${HEADERS[@]}" \
      -d "$DATA" \
      -w "\nHTTP Status: %{http_code}\n" \
      -s | python3 -m json.tool || echo "Failed"
  fi
}

# --- UNPROTECTED ENDPOINT ---
run_curl_test "GET" "/health/" "" "Test 1: Health Check" "false"

# --- PROTECTED ENDPOINTS (Requires Token) ---
run_curl_test "GET" "/users/" "" "Test 2: User Service - List Users" "true"
run_curl_test "GET" "/templates/" "" "Test 3: Template Service - List Templates" "true"

# Test 4: Create User (Requires you to change the email if it exists)
USER_PAYLOAD='{
  "email": "curl_test_user@example.com",
  "password": "testpass123",
  "first_name": "Curl",
  "last_name": "Test",
  "push_token": "curl_token_12345",
  "preferences": {
    "email": true,
    "push": true
  }
}'
run_curl_test "POST" "/users/" "$USER_PAYLOAD" "Test 4: Create New Test User" "true"

# You would extract the USER_ID here for the next tests.
# For demonstration, we'll use the user created by the Python script (test@example.com)
# NOTE: Replace 'USER_ID_FROM_DB' with the actual UUID of test@example.com
DUMMY_USER_ID="USER_ID_FROM_DB"
REQUEST_ID_BASE="test-curl-$(date +%s)"

# Test 5: Send Email Notification
EMAIL_PAYLOAD='{
  "notification_type": "email",
  "user_id": "'"$DUMMY_USER_ID"'",
  "template_code": "welcome_email",
  "variables": {
    "name": "Curl Test User",
    "link": "https://example.com/welcome"
  },
  "request_id": "'"$REQUEST_ID_BASE"'-email",
  "priority": 1
}'
run_curl_test "POST" "/notifications/" "$EMAIL_PAYLOAD" "Test 5: Send Email Notification (Queueing)" "true"

# Test 6: Idempotency Test (Duplicate Request)
IDEMPOTENT_PAYLOAD='{
  "notification_type": "email",
  "user_id": "'"$DUMMY_USER_ID"'",
  "template_code": "welcome_email",
  "variables": {
    "name": "Idempotency Test",
    "link": "https://example.com"
  },
  "request_id": "idempotent-test-12345",
  "priority": 1
}'
echo -e "\n[Test 6] Idempotency Test - First Request (should queue)"
echo "----------------------------------------"
run_curl_test "POST" "/notifications/" "$IDEMPOTENT_PAYLOAD" "Test 6a: Idempotency (First Request)" "true"

echo -e "\n[Test 6] Idempotency Test - Duplicate Request (should be rejected/success w/ duplicate message)"
echo "----------------------------------------"
run_curl_test "POST" "/notifications/" "$IDEMPOTENT_PAYLOAD" "Test 6b: Idempotency (Duplicate Request)" "true"


# Test 7: Get Notification Status
echo "Note: Status check requires replacing 'REQUEST_ID' with a real one, e.g., 'idempotent-test-12345'"
DUMMY_REQUEST_ID="idempotent-test-12345"
run_curl_test "GET" "/notifications/email/status/?notification_id=$DUMMY_REQUEST_ID" "" "Test 7: Get Notification Status" "true"

echo -e "\n============================================================"
echo "  Test Suite Complete. Remember to replace DUMMY_USER_ID."
echo "============================================================"