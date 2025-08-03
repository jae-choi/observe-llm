# LangGraph Agent with Langfuse Observability

This project provides a ready-to-deploy AI agent built with LangGraph that demonstrates a research, critique, and revision loop. It is fully integrated with Langfuse for detailed observability into every step of the agent's execution. The entire system is containerized using Docker for easy setup and deployment.

> **Note: Project Maintainers**
>
> - **GitHub Repository (Source Code):** [github.com/jae-choi](https://github.com/jae-choi)
> - **Docker Hub Image (Pre-built Image):** [hub.docker.com/u/peter99choi](https://hub.docker.com/u/peter99choi)
>
> The source code is managed under the `jae-choi` GitHub account, and the official pre-built Docker images are distributed via the `peter99choi` Docker Hub account.

## ✨ Key Features

- **Self-Correcting Agent:** Implements a graph-based workflow where an AI critiques and revises its own work to improve quality.
- **Detailed Observability:** Integrated with Langfuse to trace, debug, and analyze the agent's behavior, including costs and latency.
- **Web Interface:** A simple FastAPI web interface to interact with the agent.
- **Containerized:** Packaged with Docker and Docker Compose for a one-command setup.
- **Persistent Data:** Configured to store all Langfuse data on your local machine, ensuring data is safe across restarts.

---

## 🚀 Getting Started (with Source Code)

This section is for users who have the source code and want to run the complete application stack including Langfuse.

### Prerequisites

- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Podman](https://podman.io/getting-started/installation) installed and running.
- If using Podman, you will also need `podman-compose`.

> **Note for Apple Silicon (M1/M2/M3) Users:** The Docker images for some services (like `clickhouse`) may run under emulation and show performance warnings. This is expected and does not affect the functionality for local testing.

### Configuration

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/jae-choi/observe-llm.git
    cd observe-llm
    ```

2.  **Create `.env` file:**
    Copy the example environment file. This file will store your secret keys.
    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env` file:**
    Open the newly created `.env` file and fill in the required values for the agent and all backing services.

    > **⚠️ Important Security Note:** The default passwords in the `.env.example` file are for local development only. For any production or public-facing deployment, you **must** change these to strong, randomly generated passwords.

### Running the Application

Open a terminal in the project's root directory and run the appropriate command for your environment:

**Using Docker:**
```bash
docker compose up --build -d
```

**Using Podman:**
```bash
podman-compose up --build -d
```

### Accessing the Services

- **AI Agent UI:** [http://localhost:8000](http://localhost:8000)
- **Langfuse Dashboard:** [http://localhost:3000](http://localhost:3000)

### Stopping the Application

- **Docker:** `docker compose down`
- **Podman:** `podman-compose down`

---

## 📖 Running the Standalone Agent Image

This section is for advanced users who want to run only the agent's Docker image and connect it to a separate Langfuse instance. For most users, the `docker-compose` method above is recommended.

### Step 1: Get the Docker Image

**Option A: From Docker Hub**
Replace `<username>` with the actual Docker Hub username.
```bash
docker pull peter99choi/observe-llm:latest
```

**Option B: From a .tar file**
If you received a `.tar` file, open a terminal in that folder and run:
- **Docker:** `docker load -i observe-llm.tar`
- **Podman:** `podman load -i observe-llm.tar`

### Step 2: Run the Application Container

Run the command below in your terminal. **Remember to replace the placeholder values** with your actual keys.

**Using Docker:**
```bash
docker run -d -p 8000:8000 \
  -e GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY" \
  -e LANGFUSE_PUBLIC_KEY="YOUR_LANGFUSE_PUBLIC_KEY" \
  -e LANGFUSE_SECRET_KEY="YOUR_LANGFUSE_SECRET_KEY" \
  --name observe-llm-app \
  peter99choi/observe-llm:latest
```

**Using Podman:**
```bash
podman run -d -p 8000:8000 \
  -e GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY" \
  -e LANGFUSE_PUBLIC_KEY="YOUR_LANGFUSE_PUBLIC_KEY" \
  -e LANGFUSE_SECRET_KEY="YOUR_LANGFUSE_SECRET_KEY" \
  --name observe-llm-app \
  peter99choi/observe-llm:latest
```

### Step 3: Access the Service

Open your web browser and go to `http://localhost:8000`.

### Step 4: Managing the Container

- **Stop:** `docker stop observe-llm-app` or `podman stop observe-llm-app`
- **Restart:** `docker start observe-llm-app` or `podman start observe-llm-app`
- **Remove:** `docker rm observe-llm-app` or `podman rm observe-llm-app`

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
