# RuleScope

RuleScope is an interactive system that supports the generation, verification, and refinement of data validation rules based on data semantics. This project consists of a Python backend based on Flask and a frontend application based on Vue 3.

## Table of Contents

- [Dependencies and Installation](#dependencies-and-installation)
  - [Backend Dependencies](#backend-dependencies)
  - [Frontend Dependencies](#frontend-dependencies)
- [LLM Configuration](#llm-configuration)
- [Project Startup](#project-startup)
- [Project Structure](#project-structure)

## Dependencies and Installation

### Backend Dependencies

The backend is developed using Python. Please ensure Python 3.11 is installed.

It is recommended to create a virtual environment in the `backend` directory and install dependencies.

Please run the following command to install the required dependencies:
```bash
pip install -r requirements.txt
```

If your device has a GPU, you can install `cuml` and `cupy` for acceleration:
```bash
pip install cupy-cuda12x
pip install --extra-index-url=https://pypi.nvidia.com cuml-cu12
```

### Frontend Dependencies

The frontend is developed using Vue 3. Please ensure Node.js and npm are installed.

Enter the frontend directory and install dependencies:
```bash
cd frontend
npm install
```

## LLM Configuration

The backend relies on Large Language Models (LLMs) for rule generation and refinement. You can configure it to use either a local Ollama instance or external APIs.

### Option 1: Local Ollama (Recommended for Privacy)

1. **Install and Run Ollama**: Ensure Ollama is installed and running on port `11434` (default).
2. **Download Models**: You need to pull the following models. Please choose the model size that fits your hardware capabilities:
   - `qwen2.5:7b-instruct-q4_K_M`
   - `qwen2.5:14b-instruct-q4_K_M`
   - `qwen2.5:32b-instruct-q4_K_M`
   - `qwen2.5:72b-instruct-q4_K_M`

   Please ensure your device has sufficient resources to run these models.

### Option 2: API Configuration

If you prefer using external APIs (OpenAI, Anthropic, DeepSeek, Qwen, etc.):

1. Navigate to `backend/libs/`.
2. Copy `.env.example` to a new file named `.env`.
3. Open `.env` and configure your `API_PROVIDER` and the corresponding API keys/URLs.

   Example `.env` configuration:
   ```ini
   # Choose provider: openai, anthropic, deepseek, qwen
   API_PROVIDER=openai
   
   # OpenAI configuration
   OPENAI_API_KEY=your_key_here
   ```

## Project Startup

### Start Backend

The backend service entry point is located at `backend/libs/app.py`.

Run the following command in the project root directory:
```bash
python backend/libs/app.py
```

### Start Frontend

Ensure dependencies are installed, then run the following command in the `frontend` directory:
```bash
cd frontend
npm run serve
```

After successful startup, you can usually access it via browser at `http://localhost:8080` (please check the terminal output for the specific port).

## Project Structure

### Backend (`backend/`)

The backend mainly contains data storage and core business logic.

- **`dataset/`**: Stores system demonstration cases (such as animal, basketball, electrocar, etc.), including table information, visualization information, and validation rules.
- **`libs/`**: Backend core code library.
  - `app.py`: Flask application entry point.
  - Contains core modules such as rule generation (`rule_generator`), rule implementation (`rule_implementer`), and rule refinement (`rule_refiner`).
  - Contains utility scripts for LLM interaction, JSON parsing, etc.

### Frontend (`frontend/`)

The frontend is mainly responsible for user interface display and interaction.

- **`src/components/`**: Stores Vue components, which constitute the main UI elements of the page.
- **`src/render/`**: Contains rendering-related logic code, mainly used for visual presentation of data and rules.
- **`src/utils/`**: Stores general utility functions and helper classes for the frontend.