import requests
import json
import os
from typing import Union, Generator, List, Dict, Optional, Any
from pathlib import Path

# Try to import necessary libraries, provide hints if import fails
try:
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required library: {e.name}")
    print("Please run 'pip install openai pydantic python-dotenv' to install them.")
    exit()

# Get current file directory
current_dir = Path(__file__).parent
# Get backend directory (parent directory)
backend_dir = current_dir.parent
# Build complete path to .env file
env_file = backend_dir / 'libs/.env'

# Load .env file
if env_file.exists():
    load_dotenv(env_file)
    print(f"Successfully loaded .env file: {env_file}")
else:
    print(f"Warning: .env file not found: {env_file}")
    print("Please ensure .env file is created in the backend directory")

def _handle_ollama_api(
    messages: List[Dict[str, str]], 
    format: Union[str, dict], 
    stream: bool, 
    model: Optional[str], 
    max_tokens: Optional[int], 
    temperature: Optional[float], 
    ollama_url: str,
    context_length: int
) -> Union[str, dict, Generator, Any]:
    """
    Handle Ollama API calls.
    
    Args:
        messages: List of conversation messages
        format: Response format ('text', 'json', or dict schema for structured output)
        stream: Whether to enable streaming response
        model: Model name to use
        max_tokens: Maximum tokens to generate
        temperature: Temperature parameter for randomness
        ollama_url: URL for Ollama API endpoint
        context_length: Context window size
        
    Returns:
        Generated response in specified format
    """
    if model is None:
        model = "qwen2.5:7b-instruct-q4_K_M"

    data = {
        "model": model,
        "messages": messages.copy(),  # Make a copy to avoid modifying original
        "stream": stream,
        "options": {
            "num_ctx": context_length
        }
    }
    
    # Handle format parameter - preserve original Ollama functionality
    if isinstance(format, dict):
        data["format"] = "json"
        schema_prompt = f"""Please provide a response in a structured JSON format. The JSON object must strictly adhere to the following schema:
```json
{json.dumps(format, indent=2)}
```"""
        # Inject schema into system prompt
        if data["messages"] and data["messages"][0]['role'] == 'system':
            data["messages"][0]['content'] = f"{data['messages'][0]['content']}\n\n{schema_prompt}"
        else:
            data["messages"].insert(0, {"role": "system", "content": schema_prompt})
    elif format == "json":
         data["format"] = "json"

    if max_tokens is not None:
        data["options"]["num_predict"] = max_tokens
    if temperature is not None:
        data["options"]["temperature"] = temperature

    try:
        if stream:
            def stream_generator():
                with requests.post(ollama_url, json=data, stream=True) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line:
                            json_response = json.loads(line)
                            if 'message' in json_response and json_response['message']['content'] is not None:
                                yield json_response['message']['content']
            return stream_generator()
        else:
            response = requests.post(ollama_url, json={**data, "stream": False})
            response.raise_for_status()
            result = response.json()
            content = result.get('message', {}).get('content', '')
            
            if isinstance(format, dict) or format == "json":
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print("JSON parsing failed for Ollama response. Returning raw content.")
                    return content
            return content
            
    except requests.exceptions.RequestException as e:
        print(f"Ollama request failed: {e}")
        return {} if format == "json" or isinstance(format, dict) else ""
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        return {} if format == "json" or isinstance(format, dict) else ""

def _handle_qwen_api(
    messages: List[Dict[str, str]], 
    format: Union[str, dict], 
    stream: bool, 
    model: Optional[str], 
    max_tokens: Optional[int], 
    temperature: Optional[float], 
    api_key: Optional[str]
) -> Union[str, dict, Generator, Any]:
    """
    Handle Qwen API calls.
    
    Args:
        messages: List of conversation messages
        format: Response format ('text', 'json', or dict schema)
        stream: Whether to enable streaming response
        model: Model name to use
        max_tokens: Maximum tokens to generate
        temperature: Temperature parameter for randomness
        api_key: API key for authentication
        
    Returns:
        Generated response in specified format
    """
    if isinstance(format, dict):
        raise ValueError("Qwen provider does not support dictionary-based JSON schemas for the 'format' parameter. Please use format='json' and specify the structure in the prompt.")

    if model is None:
        model = os.getenv("QWEN_MODEL", "qwen3-max")

    # Use provided api_key first, otherwise read from environment variables
    resolved_api_key = api_key or os.getenv("QWEN_API_KEY")
    if not resolved_api_key:
        raise ValueError("Qwen API key must be provided via the 'api_key' argument or the 'QWEN_API_KEY' environment variable.")

    base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    try:
        client = OpenAI(api_key=resolved_api_key, base_url=base_url)
        
        request_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if format and format.lower() == 'json':
            request_params['response_format'] = {'type': 'json_object'}
            # Check if prompt contains 'json' keyword
            prompt_content_for_check = ""
            for msg in messages:
                prompt_content_for_check += msg.get('content', '')
            if 'json' not in prompt_content_for_check.lower():
                print("Warning: For Qwen's JSON mode, it is recommended to include the word 'json' in your system or user prompt to guide the model.")

        response = client.chat.completions.create(**request_params)

        if stream:
            def stream_generator():
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            return stream_generator()
        else:
            content = response.choices[0].message.content
            if format and format.lower() == 'json':
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print("JSON parsing failed for Qwen response. Returning raw content.")
                    return content
            return content

    except Exception as e:
        print(f"An error occurred with the Qwen API: {e}")
        return {} if format and format.lower() == 'json' else ""

def _handle_deepseek_api(
    messages: List[Dict[str, str]], 
    format: Union[str, dict], 
    stream: bool, 
    model: Optional[str], 
    max_tokens: Optional[int], 
    temperature: Optional[float], 
    api_key: Optional[str]
) -> Union[str, dict, Generator, Any]:
    """
    Handle DeepSeek API calls.
    
    Args:
        messages: List of conversation messages
        format: Response format ('text', 'json', or dict schema)
        stream: Whether to enable streaming response
        model: Model name to use
        max_tokens: Maximum tokens to generate
        temperature: Temperature parameter for randomness
        api_key: API key for authentication
        
    Returns:
        Generated response in specified format
    """
    if isinstance(format, dict):
        raise ValueError("DeepSeek provider does not support dictionary-based JSON schemas for the 'format' parameter. Please use format='json' and specify the structure in the prompt.")

    if model is None:
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Use provided api_key first, otherwise read from environment variables
    resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not resolved_api_key:
        raise ValueError("DeepSeek API key must be provided via the 'api_key' argument or the 'DEEPSEEK_API_KEY' environment variable.")

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    try:
        client = OpenAI(api_key=resolved_api_key, base_url=base_url)
        
        request_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if format and format.lower() == 'json':
            request_params['response_format'] = {'type': 'json_object'}
            # Check if prompt contains 'json' keyword
            prompt_content_for_check = ""
            for msg in messages:
                prompt_content_for_check += msg.get('content', '')
            if 'json' not in prompt_content_for_check.lower():
                print("Warning: For DeepSeek's JSON mode, it is recommended to include the word 'json' in your system or user prompt to guide the model.")

        response = client.chat.completions.create(**request_params)

        if stream:
            def stream_generator():
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            return stream_generator()
        else:
            content = response.choices[0].message.content
            if format and format.lower() == 'json':
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print("JSON parsing failed for DeepSeek response. Returning raw content.")
                    return content
            return content

    except Exception as e:
        print(f"An error occurred with the DeepSeek API: {e}")
        return {} if format and format.lower() == 'json' else ""

def _handle_openai_api(
    messages: List[Dict[str, str]], 
    format: Union[str, dict], 
    stream: bool, 
    model: Optional[str], 
    max_tokens: Optional[int], 
    temperature: Optional[float], 
    api_key: Optional[str]
) -> Union[str, dict, Generator, Any]:
    """
    Handle OpenAI API calls.
    
    Args:
        messages: List of conversation messages
        format: Response format ('text', 'json', or dict schema)
        stream: Whether to enable streaming response
        model: Model name to use
        max_tokens: Maximum tokens to generate
        temperature: Temperature parameter for randomness
        api_key: API key for authentication
        
    Returns:
        Generated response in specified format
    """
    if isinstance(format, dict):
        raise ValueError("OpenAI provider does not support dictionary-based JSON schemas for the 'format' parameter. Please use format='json' and specify the structure in the prompt.")

    if model is None:
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_api_key:
        raise ValueError("OpenAI API key must be provided via the 'api_key' argument or the 'OPENAI_API_KEY' environment variable.")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    try:
        client = OpenAI(api_key=resolved_api_key, base_url=base_url)
        
        request_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if format and format.lower() == 'json':
            request_params['response_format'] = {'type': 'json_object'}

        response = client.chat.completions.create(**request_params)

        if stream:
            def stream_generator():
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            return stream_generator()
        else:
            content = response.choices[0].message.content
            if format and format.lower() == 'json':
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print("JSON parsing failed for OpenAI response. Returning raw content.")
                    return content
            return content

    except Exception as e:
        print(f"An error occurred with the OpenAI API: {e}")
        return {} if format and format.lower() == 'json' else ""

def _handle_anthropic_api(
    messages: List[Dict[str, str]], 
    format: Union[str, dict], 
    stream: bool, 
    model: Optional[str], 
    max_tokens: Optional[int], 
    temperature: Optional[float], 
    api_key: Optional[str]
) -> Union[str, dict, Generator, Any]:
    """
    Handle Anthropic Claude API calls.
    
    Args:
        messages: List of conversation messages
        format: Response format ('text', 'json', or dict schema)
        stream: Whether to enable streaming response
        model: Model name to use
        max_tokens: Maximum tokens to generate
        temperature: Temperature parameter for randomness
        api_key: API key for authentication
        
    Returns:
        Generated response in specified format
    """
    if isinstance(format, dict):
        raise ValueError("Anthropic provider does not support dictionary-based JSON schemas for the 'format' parameter. Please use format='json' and specify the structure in the prompt.")

    if model is None:
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

    resolved_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not resolved_api_key:
        raise ValueError("Anthropic API key must be provided via the 'api_key' argument or the 'ANTHROPIC_API_KEY' environment variable.")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=resolved_api_key)
        
        # Convert message format - Anthropic requires separate system messages
        system_content = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                anthropic_messages.append(msg)

        request_params = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 2048,
            "temperature": temperature,
        }
        
        if system_content:
            request_params["system"] = system_content

        if stream:
            # Anthropic streaming response
            def stream_generator():
                with client.messages.stream(**request_params) as stream:
                    for text in stream.text_stream:
                        yield text
            return stream_generator()
        else:
            response = client.messages.create(**request_params)
            content = response.content[0].text
            
            if format and format.lower() == 'json':
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print("JSON parsing failed for Anthropic response. Returning raw content.")
                    return content
            return content

    except ImportError:
        raise ValueError("Anthropic library not installed. Please run: pip install anthropic")
    except Exception as e:
        print(f"An error occurred with the Anthropic API: {e}")
        return {} if format and format.lower() == 'json' else ""

def chat_api(
    user_prompt: str,
    provider: str = 'ollama',
    system_prompt: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    format: Union[str, dict] = "text",
    stream: bool = False,
    model: Optional[str] = None,
    max_tokens: Optional[int] = 2048,
    temperature: Optional[float] = 0.7,
    api_key: Optional[str] = None,
    ollama_url: str = "http://localhost:11434/api/chat",
    context_length: int = 30000
) -> Union[str, dict, Generator, Any]:
    """
    Unified interface for chatting with large language models, supporting Ollama and various API providers.

    Args:
        user_prompt (str): User input prompt.
        provider (str): API provider, can be 'ollama' or 'api'. Default is 'ollama'.
                       When using 'api', the specific provider is auto-selected from API_PROVIDER in .env file.
        system_prompt (Optional[str]): System prompt.
        history (Optional[List[Dict[str, str]]]): Conversation history.
        format (Union[str, dict]): Response format.
                       - For 'ollama': Can be "text", "json", or a JSON schema dict for structured output.
                       - For 'api': Can be "text" or "json". Schema dict not supported.
        stream (bool): Whether to use streaming response.
        model (Optional[str]): Model name to use. If None, uses default model based on provider.
        max_tokens (Optional[int]): Maximum tokens to generate.
        temperature (Optional[float]): Temperature parameter.
        api_key (Optional[str]): API key. If not provided, tries to read from environment variables.
        ollama_url (str): [Ollama only] URL for Ollama API.
        context_length (int): [Ollama only] Context window size.

    Returns:
        Union[str, dict, Generator, Any]: Returns string, dict, or generator based on parameters.
    """
    # 1. Build common message list
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    # 2. Route to appropriate handler based on provider
    if provider.lower() == 'ollama':
        return _handle_ollama_api(
            messages=messages,
            format=format,
            stream=stream,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            ollama_url=ollama_url,
            context_length=context_length
        )
    
    elif provider.lower() == 'api':
        # API mode: Read configuration from .env file
        api_provider = os.getenv("API_PROVIDER", "deepseek").lower()
        
        if api_provider == "qwen":
            return _handle_qwen_api(messages, format, stream, model, max_tokens, temperature, api_key)
        elif api_provider == "deepseek":
            return _handle_deepseek_api(messages, format, stream, model, max_tokens, temperature, api_key)
        elif api_provider == "openai":
            return _handle_openai_api(messages, format, stream, model, max_tokens, temperature, api_key)
        elif api_provider == "anthropic":
            return _handle_anthropic_api(messages, format, stream, model, max_tokens, temperature, api_key)
        else:
            raise ValueError(f"Unsupported API provider '{api_provider}' in .env file. Supported: deepseek, openai, anthropic, qwen.")
    
    else:
        raise ValueError(f"Unsupported provider '{provider}'. Please choose 'ollama' or 'api'.")


