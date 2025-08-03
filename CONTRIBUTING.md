# Project Evolution & Contribution Guide

This document outlines the development process of the `observe-llm` project, providing technical insights and a guide for future contributions.

## 1. Core Application: The Self-Correcting Agent

The heart of this project is `run_agent.py`, which implements a self-correcting AI agent using LangGraph.

### LangGraph State Machine

The agent's workflow is managed as a state machine. The `AgentState` TypedDict acts as the central data structure that is passed between nodes, ensuring a consistent flow of information.

```python
class AgentState(TypedDict):
    topic: str
    research_result: str
    draft: str
    critique: str
    final_output: Optional[str]
    reviser_output: str
    revision_count: int
    langfuse_handler: Optional[CallbackHandler]
```

### Critique & Revision Loop

The core logic is a cycle where content is generated, critiqued, and then revised based on the critique. This loop continues until the quality is approved or a maximum number of revisions is reached.

- **Nodes:** `researcher`, `writer`, `critique`, and `reviser` represent distinct tasks performed by the LLM.
- **Conditional Edge:** The `should_revise` function is a conditional edge that intelligently routes the workflow. Based on the content of the `critique` node, it decides whether to loop back to the `reviser` node or to exit the loop.

```python
def should_revise(state: AgentState) -> Literal["reviser", "set_final_output"]:
    revision_count = state.get('revision_count', 0)
    if "REVISE" in state["critique"] and revision_count < MAX_REVISIONS:
        return "reviser"
    else:
        return "set_final_output"

# ... in the graph definition
workflow.add_conditional_edges(
    "critique",
    should_revise,
    {"reviser": "reviser", "set_final_output": "set_final_output"}
)
```

### Observability with Langfuse

To trace and debug this complex, cyclical process, Langfuse is integrated at two levels:
1.  **`@observe` Decorator:** Provides function-level tracing for each node.
2.  **`CallbackHandler`:** The `langfuse.langchain.CallbackHandler` is passed to the LangChain LLM models to capture detailed LLM interactions (prompts, responses, token usage, etc.).

## 2. Containerization with Docker

To ensure consistent and easy deployment, the entire application stack is containerized.

### Agent Dockerfile

The `Dockerfile` creates a self-contained image for the Python agent.

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application's code
COPY . .

# Expose the port and define the run command
EXPOSE 8000
CMD ["uvicorn", "run_agent:app_fastapi", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Full Stack

`docker-compose.yml` orchestrates the entire ecosystem, including the agent and the Langfuse stack (Postgres, Redis, Clickhouse, Minio, and the Langfuse UI/worker). The `depends_on` directive ensures services start in the correct order.

## 3. Hardening for Production & Distribution

The project was hardened for public release with the following steps:

### Security: Environment Variable Management

All secrets and sensitive configurations were externalized from `docker-compose.yml` into a `.env` file.

**Before:**
```yaml
# docker-compose.yml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: postgres # Hardcoded secret
```

**After:**
```yaml
# docker-compose.yml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD} # Reference to environment variable
```
An `.env.example` file was created to serve as a template for users.

### Data Persistence

To prevent data loss when containers are removed, Docker's named volumes were replaced with local directory bind mounts. This ensures all database and object storage data persists in the `langfuse-data/` directory on the host machine.

```yaml
# docker-compose.yml
services:
  postgres:
    volumes:
      - ./langfuse-data/postgres:/var/lib/postgresql/data
```

### Build Optimization

-   **`.gitignore`:** Prevents sensitive files (`.env`) and local artifacts (`venv`, `langfuse-data`) from being committed to the Git repository.
-   **`.dockerignore`:** Prevents the same files from being copied into the Docker build context, resulting in a smaller and more secure image.

## 4. Documentation

-   **`README.md`:** A comprehensive guide was created to explain the project's purpose, features, and setup instructions for users with the source code and users with only the pre-built Docker image.
-   **`LICENSE`:** An MIT License was added to clarify the open-source terms of use.

## 5. Deployment

### Multi-Architecture Build

To support both Intel/AMD (amd64) and Apple Silicon (arm64) architectures, a multi-arch image was built and pushed to Docker Hub using `docker buildx`.

**Command:**
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t peter99choi/observe-llm:latest --push .
```

### GitHub Integration

The local project was initialized as a Git repository and pushed to GitHub.

**Commands:**
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/jae-choi/observe-llm.git
git push -u origin main
