# LangGraph Agent with Langfuse Observability

This project provides a ready-to-deploy AI agent built with LangGraph that demonstrates a research, critique, and revision loop. It is fully integrated with Langfuse for detailed observability into every step of the agent's execution. The entire system is containerized using Docker for easy setup and deployment.

> **Note: Project Maintainers**
>
> - **GitHub Repository (Source Code & Config):** [github.com/jae-choi/observe-llm](https://github.com/jae-choi/observe-llm)
> - **Docker Hub Image (Pre-built Image):** [hub.docker.com/u/peter99choi](https://hub.docker.com/u/peter99choi)
>
> The source code is managed on GitHub, and the official pre-built Docker images are distributed via Docker Hub.

## ✨ Key Features

- **Self-Correcting Agent:** Implements a graph-based workflow where an AI critiques and revises its own work to improve quality.
- **Detailed Observability:** Integrated with Langfuse to trace, debug, and analyze the agent's behavior, including costs and latency.
- **Web Interface:** A simple FastAPI web interface to interact with the agent.
- **Containerized:** Packaged with Docker and Docker Compose for a one-command setup.
- **Persistent Data:** Configured to store all Langfuse data on your local machine, ensuring data is safe across restarts.

---

## 🚀 Getting Started

This is the recommended method for all users. It runs the complete application stack by pulling pre-built images from Docker Hub.
[Intro WEB](https://jae-choi.github.io/news/observe-llm.html)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Podman](https://podman.io/getting-started/installation) installed and running.

### Step 1: Get the Configuration Files

Download or clone this GitHub repository to get the necessary configuration files.
```bash
git clone https://github.com/jae-choi/observe-llm.git
cd observe-llm
```

### Step 2: Configure API Keys

1.  **Start Langfuse to Get Keys:**
    Run the command below to start only the Langfuse service.
    ```bash
    docker compose up -d langfuse-web
    ```
    Go to `http://localhost:3000`, sign up, create a new project, and copy the **Public Key** and **Secret Key** from the "API Keys" section.

2.  **Create and Edit `.env` file:**
    Copy the example environment file.
    ```bash
    cp .env.example .env
    ```
    Now, open the `.env` file and paste your **Google API Key**, and the **Langfuse Keys** you just copied. For any other secrets, you can leave the defaults for local testing but should change them for production.

### Step 3: Run the Full Application

Run the script for your operating system. This will download all required images and start the full application stack in the background.

-   **On macOS or Linux:**
    ```bash
    ./run.sh
    ```
-   **On Windows:**
    ```bash
    run.bat
    ```

### Accessing the Services

- **AI Agent UI:** [http://localhost:8000](http://localhost:8000)
- **Langfuse Dashboard:** [http://localhost:3000](http://localhost:3000)

### Stopping the Application
```bash
docker compose down
```
> **Note:** This command stops and removes the containers, but your Langfuse data is safe. Because we configured local data persistence, all your data remains in the `langfuse-data` folder in your project directory.

---

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/jae-choi/observe-llm/blob/main/LICENSE) file for details.
