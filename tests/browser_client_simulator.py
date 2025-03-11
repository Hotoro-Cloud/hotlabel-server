#!/usr/bin/env python3
"""
HotLabel Browser Client Simulator

This script simulates browser clients connecting to the HotLabel API,
requesting tasks based on their profile, and submitting responses.

For the TII CrowdLabel Challenge demo
"""

import requests
import json
import time
import argparse
import uuid
import random
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

class BrowserClientSimulator:
    """Simulates a browser client interacting with HotLabel"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        self.session = requests.Session()
    
    def _get_user_agent(self):
        """Get a random user agent string"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        ]
        return random.choice(user_agents)
    
    def _get_language(self):
        """Get a random language preference"""
        languages = ["en", "fr", "es", "de", "zh", "ja", "ar", "ru"]
        weights = [0.5, 0.15, 0.1, 0.1, 0.05, 0.05, 0.025, 0.025]
        return random.choices(languages, weights=weights, k=1)[0]
    
    def _get_interests(self):
        """Get random user interests"""
        all_interests = [
            "technology", "science", "art", "sports", "news", 
            "finance", "education", "entertainment", "health", "travel"
        ]
        # Choose 2-5 random interests
        num_interests = random.randint(2, 5)
        return random.sample(all_interests, num_interests)
    
    def create_profile(self):
        """Create a simulated user profile"""
        # Determine if mobile
        is_mobile = random.random() < 0.3
        
        # Create profile data
        profile = {
            "browser_info": {
                "user_agent": self._get_user_agent(),
                "language": self._get_language(),
                "preferred_languages": [self._get_language() for _ in range(random.randint(0, 2))],
                "timezone": random.choice(["America/New_York", "Europe/London", "Asia/Tokyo", "Australia/Sydney"]),
                "screen_resolution": random.choice(["1920x1080", "1366x768", "2560x1440", "3840x2160", "375x812"]),
                "platform": random.choice(["Windows", "MacOS", "Linux", "iOS", "Android"]),
                "is_mobile": is_mobile
            },
            "recent_sites": self._get_interests(),
            "current_site_category": random.choice(self._get_interests()),
            "current_page_topic": random.choice([
                "machine learning", "cooking", "travel", "soccer", 
                "stock market", "climate change", "artificial intelligence",
                "politics", "movies", "music"
            ]),
            "time_on_page": random.randint(30, 300),  # 30 seconds to 5 minutes
            "interaction_depth": random.uniform(0.1, 1.0),
            "metadata": {
                "detected_language": self._get_language(),
                "technical_terms": [
                    {
                        "domain": random.choice(["programming", "science", "math", "arts", "business"]),
                        "confidence": random.uniform(0.5, 1.0)
                    }
                ],
                "active_hour": random.randint(0, 23),
                "engagement_signals": {
                    "scroll_depth": random.uniform(0.1, 1.0),
                    "click_pattern": random.uniform(0.3, 1.0)
                }
            }
        }
        return profile
    
    def request_task(self):
        """Request a task from the HotLabel API"""
        profile = self.create_profile()
        
        try:
            response = self.session.post(
                f"{self.base_url}/tasks/request?session_id={self.session_id}",
                json=profile
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error requesting task: {e}")
            return None
    
    def submit_response(self, task):
        """Submit a response for a task"""
        # Simulate thinking time (1-10 seconds)
        response_time = random.randint(1000, 10000)
        time.sleep(response_time / 1000)
        
        # Generate response based on task type
        task_type = task.get("type", "")
        choices = task.get("task", {}).get("choices", {})
        
        response_data = None
        if task_type == "multiple-choice" and choices:
            # Select a random choice
            response_data = {"selected_choice": random.choice(list(choices.keys()))}
        elif task_type == "true-false":
            response_data = {"selected_choice": random.choice(["true", "false"])}
        elif task_type == "short-answer":
            # Generate a mock short answer
            response_data = {"text": "This is a simulated short answer response."}
        else:
            # Default fallback
            response_data = {"value": "unknown task type"}
        
        # Prepare response submission
        response_submission = {
            "task_id": task["task_id"],
            "session_id": self.session_id,
            "response_data": response_data,
            "response_time_ms": response_time,
            "client_metadata": {
                "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
                "device_type": "mobile" if task.get("browser_info", {}).get("is_mobile", False) else "desktop",
                "interaction_count": random.randint(1, 10)
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/responses/",
                json=response_submission
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error submitting response: {e}")
            return None

def simulate_user_session(base_url, session_id=None, max_tasks=3):
    """Simulate a complete user session"""
    simulator = BrowserClientSimulator(base_url)
    if session_id:
        simulator.session_id = session_id
    
    print(f"Starting simulation for user: {simulator.session_id}")
    
    tasks_completed = 0
    for i in range(max_tasks):
        # Request a task
        print(f"  Requesting task {i+1}/{max_tasks}...")
        task = simulator.request_task()
        
        if not task:
            print("  No task received, ending session")
            break
        
        print(f"  Received task: {task.get('task_id')} - {task.get('category')} - {task.get('type')}")
        
        # Submit a response
        print(f"  Submitting response...")
        response = simulator.submit_response(task)
        
        if response:
            print(f"  Response submitted successfully: {response.get('response_id', 'unknown')}")
            tasks_completed += 1
        else:
            print(f"  Failed to submit response")
        
        # Small pause between tasks
        time.sleep(random.uniform(1, 3))
    
    print(f"User session completed: {tasks_completed}/{max_tasks} tasks")
    return tasks_completed

def run_simulation(args):
    """Run the full simulation with multiple users"""
    print(f"Starting HotLabel Browser Client Simulation")
    print(f"API URL: {args.url}")
    print(f"Number of users: {args.users}")
    print(f"Tasks per user: {args.tasks_per_user}")
    print()
    
    start_time = time.time()
    total_tasks_completed = 0
    
    # Create user sessions in parallel
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_to_user = {
            executor.submit(
                simulate_user_session, 
                args.url, 
                f"sim-user-{i}", 
                args.tasks_per_user
            ): i for i in range(args.users)
        }
        
        for future in future_to_user:
            user_idx = future_to_user[future]
            try:
                tasks_completed = future.result()
                total_tasks_completed += tasks_completed
                print(f"User {user_idx} completed {tasks_completed} tasks")
            except Exception as e:
                print(f"User {user_idx} generated an exception: {e}")
    
    elapsed_time = time.time() - start_time
    
    print("\nSimulation Summary:")
    print(f"Total elapsed time: {elapsed_time:.2f} seconds")
    print(f"Total tasks completed: {total_tasks_completed}")
    print(f"Tasks per second: {total_tasks_completed / elapsed_time:.2f}")

def main():
    parser = argparse.ArgumentParser(description="HotLabel Browser Client Simulator")
    parser.add_argument("--url", default="http://localhost:8000", help="HotLabel API URL")
    parser.add_argument("--users", type=int, default=5, help="Number of simulated users")
    parser.add_argument("--tasks-per-user", type=int, default=3, help="Number of tasks per user")
    parser.add_argument("--concurrency", type=int, default=3, help="Number of concurrent users")
    args = parser.parse_args()
    
    run_simulation(args)

if __name__ == "__main__":
    main()