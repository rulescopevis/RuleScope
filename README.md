# RuleScope

RuleScope is an interactive system designed to support the generation, verification, and refinement of data validation rules based on data semantics. The project architecture consists of a Python-based Flask backend and a Vue 3 frontend.

## Table of Contents

- [Dependencies and Installation](#dependencies-and-installation)
  - [Backend Dependencies](#backend-dependencies)
  - [Frontend Dependencies](#frontend-dependencies)
- [LLM Configuration](#llm-configuration)
- [Project Startup](#project-startup)
- [Project Structure](#project-structure)

## Dependencies and Installation

### Backend Dependencies

The backend is developed using Python. Please ensure **Python 3.11** is installed. 

It is highly recommended to create a virtual environment in the root directory before installing dependencies. Run the following command to install the required packages:
```bash
pip install -r requirements.txt
```

**Optional GPU Acceleration:**
If your device has an NVIDIA GPU, you can install `cuml` and `cupy` to accelerate processing:
```bash
pip install cupy-cuda12x
pip install --extra-index-url=[https://pypi.nvidia.com](https://pypi.nvidia.com) cuml-cu12
```

### Frontend Dependencies

The frontend is developed using Vue 3. Please ensure **Node.js** and **npm** are installed on your system.

Navigate to the frontend directory and install the dependencies:
```bash
cd frontend
npm install
```

## LLM Configuration

The backend relies on Large Language Models (LLMs) for rule generation and refinement. You can configure the system to use either a local Ollama instance or external APIs.

### Option 1: Local Ollama (Recommended for Privacy)

1. **Install and Run Ollama**: Ensure Ollama is installed and running on its default port `11434`.
2. **Download Required Models**: The system requires a multi-model pipeline. You **must pull all** of the following models for RuleScope to function correctly:
   ```bash
   ollama pull qwen2.5:7b-instruct-q4_K_M
   ollama pull qwen2.5:14b-instruct-q4_K_M
   ollama pull qwen2.5:32b-instruct-q4_K_M
   ollama pull qwen2.5:72b-instruct-q4_K_M
   ```
   
   > **⚠️ Hardware Requirement:** Your device must have sufficient VRAM to independently run the `72b` quantized version. This typically requires at least **40-48GB of VRAM**.

### Option 2: API Configuration

If you prefer using external APIs (OpenAI, Anthropic, DeepSeek, Qwen, etc.) instead of local models:

1. Navigate to the `backend/libs/` directory.
2. Copy the example environment file: `cp .env.example .env`
3. Open `.env` and configure your preferred `API_PROVIDER` along with the corresponding API keys and Base URLs.

   *Example `.env` configuration:*
   ```ini
   # Choose provider: openai, anthropic, deepseek, qwen
   API_PROVIDER=openai
   
   # OpenAI configuration
   OPENAI_API_KEY=your_api_key_here
   ```

## Project Startup

You will need to open **two separate terminal windows** to run the backend and frontend concurrently.

### 1. Start the Backend

The backend service entry point is located at `backend/libs/app.py`. Run the following command from the **project root directory**:
```bash
python backend/libs/app.py
```

### 2. Start the Frontend

In a new terminal window, navigate to the `frontend` directory and start the development server:
```bash
cd frontend
npm run serve
```

After a successful startup, the application will typically be accessible in your browser at `http://localhost:8080` (please check the terminal output for the exact port if 8080 is occupied).

## Project Structure

### Backend (`backend/`)
Contains data storage and core business logic.

- **`dataset/`**: Stores system demonstration cases (e.g., animal, basketball, electrocar). This includes table information, visualization metadata, and initial validation rules.
- **`libs/`**: The core backend code library.
  - `app.py`: The Flask application entry point.
  - Contains core operational modules such as `rule_generator`, `rule_implementer`, and `rule_refiner`.
  - Contains utility scripts for LLM interaction, JSON parsing, and data processing.

### Frontend (`frontend/`)
Responsible for the user interface and interactions.

- **`src/components/`**: Stores Vue components that make up the main UI elements of the application.
- **`src/render/`**: Contains rendering logic, primarily used for the visual presentation of data and validation rules.
- **`src/utils/`**: Stores general utility functions and helper classes for frontend operations.