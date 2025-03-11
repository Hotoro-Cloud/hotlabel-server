# HotLabel Server

HotLabel Server is the backend component of the HotLabel platform, responsible for:

1. Managing and distributing labeling tasks for LLM alignment
2. Receiving and processing responses from users
3. Matching tasks to appropriate users based on their profiles
4. Tracking user profiles and task history
5. Providing analytics and statistics

## Key Components

- **FastAPI application**: RESTful API for interacting with the system
- **Redis**: Storage for tasks, responses, user profiles, and statistics
- **Celery**: Background processing for task distribution and quality checks

## Architecture Overview

HotLabel Server follows a microservices architecture:

- **API Service**: Handles HTTP requests and responses
- **Worker Service**: Processes background tasks
- **Beat Service**: Manages scheduled tasks
- **Flower**: Monitoring for Celery tasks
- **Redis**: Shared data store and message broker

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Make sure ports 8000, 5555, and 6379 are available

### Running the Application

1. Clone the repository

```bash
git clone https://github.com/yourusername/hotlabel-server.git
cd hotlabel-server
```

2. Start the application using Docker Compose

```bash
docker-compose up -d
```

3. Access the API documentation at http://localhost