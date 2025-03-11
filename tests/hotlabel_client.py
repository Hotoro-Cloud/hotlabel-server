#!/usr/bin/env python3
"""
HotLabel Client SDK Example - For LLM Operators

This script demonstrates how to use the HotLabel API to:
1. Submit labeling tasks
2. Check task status
3. Retrieve completed responses

For the TII CrowdLabel Challenge demo
"""

import requests
import json
import time
import argparse
import uuid
from typing import List, Dict, Any, Optional

class HotLabelClient:
    """Client for interacting with the HotLabel API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        # Add API key to headers if provided
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def _get_headers(self):
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json"}
        return headers
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the HotLabel API is available"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new labeling task"""
        response = self.session.post(
            f"{self.base_url}/tasks/",
            headers=self._get_headers(),
            json=task_data
        )
        response.raise_for_status()
        return response.json()
    
    def create_batch_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple labeling tasks in batch"""
        response = self.session.post(
            f"{self.base_url}/tasks/batch",
            headers=self._get_headers(),
            json=tasks
        )
        response.raise_for_status()
        return response.json()
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get information about a specific task"""
        response = self.session.get(f"{self.base_url}/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def list_tasks(self, status: Optional[str] = None, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List tasks with optional filtering"""
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        
        response = self.session.get(
            f"{self.base_url}/tasks/",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_response(self, response_id: str) -> Dict[str, Any]:
        """Get a specific response by ID"""
        response = self.session.get(f"{self.base_url}/responses/{response_id}")
        response.raise_for_status()
        return response.json()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        response = self.session.get(f"{self.base_url}/admin/metrics")
        response.raise_for_status()
        return response.json()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get task queue status"""
        response = self.session.get(f"{self.base_url}/admin/queue-status")
        response.raise_for_status()
        return response.json()


def create_sample_vqa_task():
    """Create a sample VQA task"""
    return {
        "task_id": f"vqa-{uuid.uuid4()}",
        "track_id": "demo-track-001",
        "language": "en",
        "category": "vqa",
        "type": "multiple-choice",
        "topic": "general",
        "complexity": 2,
        "content": {
            "image": {
                "url": "https://picsum.photos/300/200"
            }
        },
        "task": {
            "text": "What is the main object shown in this image?",
            "choices": {
                "a": "Person",
                "b": "Building",
                "c": "Nature",
                "d": "Vehicle"
            }
        }
    }

def create_sample_text_task():
    """Create a sample text classification task"""
    return {
        "task_id": f"text-{uuid.uuid4()}",
        "track_id": "demo-track-001",
        "language": "en",
        "category": "text",
        "type": "multiple-choice",
        "topic": "sentiment",
        "complexity": 1,
        "content": {
            "text": {
                "text": "The service at this restaurant was excellent, and the food was delicious. I would definitely return."
            }
        },
        "task": {
            "text": "What is the sentiment of this text?",
            "choices": {
                "a": "Positive",
                "b": "Neutral",
                "c": "Negative"
            }
        }
    }

def create_tii_vqa_task():
    """Create a sample VQA task matching TII's format"""
    return {
        "task_id": f"tii-vqa-{uuid.uuid4()}",
        "track_id": "tii-track-001",
        "language": "en",
        "category": "vqa",
        "type": "true-false",
        "topic": "formula1",
        "complexity": 1,
        "content": {
            "image": {
                "url": "https://s3-eu-north-1-derc-wmi-crowdlabel-placeholder.s3.eu-north-1.amazonaws.com/TII-VQA_F1_000001.png"
            }
        },
        "task": {
            "text": "Are any cyan wheel guns visible?",
            "choices": {
                "a": "true",
                "b": "false"
            }
        }
    }

def demo_batch_submission(client, num_tasks=5):
    """Demonstrate batch submission of tasks"""
    print(f"\n[+] Submitting a batch of {num_tasks} tasks")
    
    # Create a mix of task types
    tasks = []
    for i in range(num_tasks):
        if i % 2 == 0:
            tasks.append(create_sample_vqa_task())
        else:
            tasks.append(create_sample_text_task())
    
    # Submit batch
    result = client.create_batch_tasks(tasks)
    print(f"Batch submission result: {json.dumps(result, indent=2)}")
    
    return result

def demo_task_monitoring(client, task_ids, max_wait=60):
    """Demonstrate monitoring of task status"""
    print(f"\n[+] Monitoring tasks: {task_ids}")
    
    completed_tasks = set()
    start_time = time.time()
    
    while len(completed_tasks) < len(task_ids) and (time.time() - start_time) < max_wait:
        for task_id in task_ids:
            if task_id in completed_tasks:
                continue
            
            try:
                task_info = client.get_task(task_id)
                status = task_info.get("status")
                print(f"Task {task_id}: {status}")
                
                if status == "completed":
                    completed_tasks.add(task_id)
            except Exception as e:
                print(f"Error checking task {task_id}: {e}")
        
        # If not all tasks are completed, wait before checking again
        if len(completed_tasks) < len(task_ids):
            print(f"Waiting for {len(task_ids) - len(completed_tasks)} more tasks to complete...")
            time.sleep(5)
    
    print(f"\nTask monitoring complete. {len(completed_tasks)}/{len(task_ids)} tasks completed.")

def demo_metrics(client):
    """Demonstrate retrieving system metrics"""
    print("\n[+] Retrieving system metrics")
    
    try:
        metrics = client.get_metrics()
        print("\nTask Metrics:")
        print(f"Total tasks: {metrics['tasks']['total_tasks']}")
        print(f"Completed tasks: {metrics['tasks']['completed_tasks']}")
        print(f"Completion rate: {metrics['tasks']['completion_rate']}%")
        
        print("\nResponse Metrics:")
        quality = metrics.get('responses', {}).get('quality_breakdown', {})
        print(f"High quality: {quality.get('high', 0)}")
        print(f"Medium quality: {quality.get('medium', 0)}")
        print(f"Low quality: {quality.get('low', 0)}")
        
        print("\nQueue Status:")
        queue = client.get_queue_status()
        print(f"Queue length: {queue.get('queue_length', 0)}")
    except Exception as e:
        print(f"Error retrieving metrics: {e}")

def main():
    parser = argparse.ArgumentParser(description="HotLabel Client Demo")
    parser.add_argument("--url", default="http://localhost:8000", help="HotLabel API URL")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of tasks to create")
    parser.add_argument("--monitor", action="store_true", help="Monitor task status")
    parser.add_argument("--tii", action="store_true", help="Use TII format for tasks")
    args = parser.parse_args()
    
    client = HotLabelClient(base_url=args.url)
    
    # Check API health
    try:
        health = client.health_check()
        print(f"API Health: {health}")
    except Exception as e:
        print(f"Error connecting to API: {e}")
        return
    
    # Demonstrate batch submission
    result = demo_batch_submission(client, args.batch_size)
    
    # Get list of successfully created task IDs
    task_ids = []
    if "created_tasks" in result:
        task_ids = [task.get("task_id") for task in result.get("created_tasks", [])]
    
    # Demonstrate task monitoring if requested
    if args.monitor and task_ids:
        demo_task_monitoring(client, task_ids)
    
    # Demonstrate metrics retrieval
    demo_metrics(client)
    
    # Submit a TII-format task if requested
    if args.tii:
        print("\n[+] Submitting a TII-format VQA task")
        tii_task = create_tii_vqa_task()
        result = client.create_task(tii_task)
        print(f"Task created: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    main()