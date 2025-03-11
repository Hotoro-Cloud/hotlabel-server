#!/bin/bash
# HotLabel Server API Tests - Fixed Version
# Run these tests against a running instance of the hotlabel-server

# Set the base URL
BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Create temp directory for JSON files
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Function to run a test and display results
run_test() {
  local test_name=$1
  local command=$2

  echo -e "\n${YELLOW}Running test: ${test_name}${NC}"
  echo "Command: $command"
  echo "-----------------------------------"
  
  # Run the command and capture output
  output=$(eval $command)
  
  # Check if command succeeded
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Test passed${NC}"
    echo "Response:"
    echo "$output" | jq '.' 2>/dev/null || echo "$output"
  else
    echo -e "${RED}✗ Test failed${NC}"
    echo "Error:"
    echo "$output"
  fi
  echo "-----------------------------------"
}

echo -e "${YELLOW}Starting HotLabel Server API Tests${NC}"
echo "Base URL: $BASE_URL"

# Test 1: Health check
run_test "Health Check" "curl -s ${BASE_URL}/health"

# Test 2: Root endpoint
run_test "Root Endpoint" "curl -s ${BASE_URL}/"

# Test 3: Create a task with proper JSON file
cat > ${TEMP_DIR}/task1.json << 'EOF'
{
  "task_id": "test-task-001",
  "track_id": "test-track-001",
  "language": "en",
  "category": "vqa",
  "type": "multiple-choice",
  "topic": "general",
  "complexity": 1,
  "content": {
    "image": {
      "url": "https://picsum.photos/300/200"
    }
  },
  "task": {
    "text": "What color is predominant in this image?",
    "choices": {
      "a": "Blue",
      "b": "Red",
      "c": "Green",
      "d": "Yellow"
    }
  }
}
EOF

run_test "Create Task" "curl -s -X POST ${BASE_URL}/tasks/ -H 'Content-Type: application/json' -d @${TEMP_DIR}/task1.json"

# Test 4: Get a task by ID
run_test "Get Task" "curl -s ${BASE_URL}/tasks/test-task-001"

# Test 5: List tasks
run_test "List Tasks" "curl -s ${BASE_URL}/tasks/?limit=5"

# Test 6: Create a user profile and request a task
cat > ${TEMP_DIR}/profile.json << 'EOF'
{
  "browser_info": {
    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "language": "en",
    "preferred_languages": ["en", "fr"],
    "timezone": "America/New_York",
    "screen_resolution": "1920x1080",
    "platform": "Linux",
    "is_mobile": false
  },
  "recent_sites": ["technology", "science", "education"],
  "current_site_category": "technology",
  "current_page_topic": "artificial intelligence",
  "time_on_page": 120,
  "interaction_depth": 0.8
}
EOF

run_test "Create User Profile and Request Task" "curl -s -X POST ${BASE_URL}/tasks/request?session_id=test-session-001 -H 'Content-Type: application/json' -d @${TEMP_DIR}/profile.json"

# Test 7: Submit a response
cat > ${TEMP_DIR}/response.json << 'EOF'
{
  "task_id": "test-task-001",
  "session_id": "test-session-001",
  "response_data": {
    "selected_choice": "a"
  },
  "response_time_ms": 5000,
  "client_metadata": {
    "browser": "Chrome",
    "device_type": "desktop",
    "interaction_count": 3
  }
}
EOF

run_test "Submit Response" "curl -s -X POST ${BASE_URL}/responses/ -H 'Content-Type: application/json' -d @${TEMP_DIR}/response.json"

# Test 8: Get admin metrics
run_test "Admin Metrics" "curl -s ${BASE_URL}/admin/metrics"

# Test 9: Get queue status
run_test "Queue Status" "curl -s ${BASE_URL}/admin/queue-status"

# Test 10: Create batch tasks
cat > ${TEMP_DIR}/batch-tasks.json << 'EOF'
[
  {
    "task_id": "test-task-002",
    "track_id": "test-track-001",
    "language": "en",
    "category": "text",
    "type": "short-answer",
    "topic": "literature",
    "complexity": 2,
    "content": {
      "text": {
        "text": "The quick brown fox jumps over the lazy dog."
      }
    },
    "task": {
      "text": "What animal is mentioned as being lazy?",
      "choices": null
    }
  },
  {
    "task_id": "test-task-003",
    "track_id": "test-track-001",
    "language": "fr",
    "category": "image",
    "type": "true-false",
    "topic": "art",
    "complexity": 1,
    "content": {
      "image": {
        "url": "https://picsum.photos/300/200?random=2"
      }
    },
    "task": {
      "text": "This image contains a human face.",
      "choices": {
        "true": "True",
        "false": "False"
      }
    }
  }
]
EOF

run_test "Create Batch Tasks" "curl -s -X POST ${BASE_URL}/tasks/batch -H 'Content-Type: application/json' -d @${TEMP_DIR}/batch-tasks.json"

# Cleanup
rm -rf ${TEMP_DIR}

echo -e "\n${YELLOW}All tests completed${NC}"