@echo off
REM This script builds and starts the application using Docker Compose.

echo Starting observe-llm services in the background...
docker compose up --build -d
echo Services are starting. You can access the agent at http://localhost:8000 and Langfuse at http://localhost:3000
