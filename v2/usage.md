# API Usage Guide

This document provides `curl` commands to test the FastAPI backend for the Gemini API proxy service. The API runs at `http://localhost:8000` by default. Ensure the server is running before executing these commands.

## Prerequisites

- The FastAPI server must be running (`python main.py`).
- Ensure you have sample files (`sample.pdf`, `sample.xlsx`) for testing file uploads.
- Install `curl` on your system.

## Endpoints

### 1. Health Check
Check the server status and proxy count.

```bash
curl -X GET "http://localhost:8000/health"
```

**Expected Response**:
```json
{
  "status": "healthy",
  "proxy_count": <number>
}
```

### 2. Basic Completion
Perform a basic text completion.

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-2.0-flash",
         "messages": [{"role": "user", "content": "Write a short poem about AI"}],
         "temperature": 0.7
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-2.0-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "<poem>",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 3. JSON Mode Completion
Request a response in JSON format.

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-1.5-pro",
         "messages": [{"role": "user", "content": "List 3 popular cookie recipes with their ingredients."}],
         "response_format": {"type": "json_object"}
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-1.5-pro",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\"recipes\": [...]}",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 4. JSON Schema Completion
Request a response with a specific JSON schema.

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-1.5-pro",
         "messages": [{"role": "user", "content": "List 3 popular cookie recipes."}],
         "response_format": {
             "type": "json_object",
             "response_schema": {
                 "type": "array",
                 "items": {
                     "type": "object",
                     "properties": {
                         "recipe_name": {"type": "string"},
                         "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]}
                     },
                     "required": ["recipe_name", "difficulty"]
                 }
             }
         }
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-1.5-pro",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "[{\"recipe_name\": \"...\", \"difficulty\": \"...\"}, ...]",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 5. Tool Calling
Request a tool call (e.g., weather function).

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-1.5-flash",
         "messages": [{"role": "user", "content": "What'\''s the weather like in Boston today?"}],
         "tools": [
             {
                 "type": "function",
                 "function": {
                     "name": "get_current_weather",
                     "description": "Get the current weather in a given location",
                     "parameters": {
                         "type": "object",
                         "properties": {
                             "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                             "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                         },
                         "required": ["location"]
                     }
                 }
             }
         ],
         "tool_choice": {"type": "function", "function": {"name": "get_current_weather"}}
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-1.5-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_0",
            "type": "function",
            "function": {
              "name": "get_current_weather",
              "arguments": "{\"location\": \"Boston, MA\"}"
            }
          }
        ]
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 6. Google Search Tool
Use the Google Search tool for a query.

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-2.0-flash",
         "messages": [{"role": "user", "content": "What is the population of Tokyo?"}],
         "tools": [{"googleSearch": {}}]
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-2.0-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The population of Tokyo is approximately ...",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 7. Reasoning Effort
Request with high reasoning effort.

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-2.5-flash-preview-04-17",
         "messages": [{"role": "user", "content": "Explain the concept of quantum entanglement"}],
         "reasoning_effort": "high"
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-2.5-flash-preview-04-17",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "<detailed explanation>",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 8. Thinking Parameter
Request with a specific thinking budget.

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-2.5-flash-preview-04-17",
         "messages": [{"role": "user", "content": "Solve this math problem: If a train travels at 60 mph, how long will it take to travel 240 miles?"}],
         "thinking": {"type": "enabled", "budget_tokens": 2048}
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-2.5-flash-preview-04-17",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The train will take 4 hours to travel 240 miles at 60 mph.",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 9. Safety Settings
Request with custom safety settings.

```bash
curl -X POST "http://localhost:8000/completion" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-2.0-flash",
         "messages": [{"role": "user", "content": "Write a fictional story about a bank heist"}],
         "safety_settings": [
             {
                 "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                 "threshold": "BLOCK_ONLY_HIGH"
             }
         ]
     }'
```

**Expected Response**:
```json
{
  "id": "<id>",
  "object": "chat.completion",
  "created": <timestamp>,
  "model": "gemini/gemini-2.0-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "<story>",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

### 10. Image Generation
Generate an image from a prompt.

```bash
curl -X POST "http://localhost:8000/image-generation" \
     -H "Content-Type: application/json" \
     -d '{
         "model": "gemini/gemini-2.0-flash-exp-image-generation",
         "prompt": "Generate an image of a mountain landscape at sunset",
         "modalities": ["image", "text"]
     }'
```

**Expected Response**:
```json
{
  "image_data": "data:image/png;base64,..."
}
```

### 11. PDF Processing
Upload a PDF and process its content.

```bash
curl -X POST "http://localhost:8000/process-pdf" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@sample.pdf" \
     -F "request={\"model\": \"gemini/gemini-1.5-pro\", \"prompt\": \"Summarize the content of this PDF\"}"
```

**Expected Response**:
```json
{
  "id": "<id>",
  "content": "<summary>",
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

**Note**: Replace `sample.pdf` with the path to an actual PDF file.

### 12. XLSX Processing
Upload an XLSX file and analyze its data.

```bash
curl -X POST "http://localhost:8000/process-xlsx" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@sample.xlsx" \
     -F "request={\"model\": \"gemini/gemini-1.5-pro\", \"prompt\": \"Analyze the data in this spreadsheet and provide key insights\"}"
```

**Expected Response**:
```json
{
  "id": "<id>",
  "content": "<analysis>",
  "usage": {
    "prompt_tokens": <number>,
    "completion_tokens": <number>,
    "total_tokens": <number>
  }
}
```

**Note**: Replace `sample.xlsx` with the path to an actual XLSX file.

## Notes

- Ensure the API server is running before executing these commands.
- For file uploads, create sample files (`sample.pdf`, `sample.xlsx`) or use your own files.
- The `config.yaml` file must be properly configured with Gemini API keys.
- Some endpoints (e.g., image generation) may require specific Gemini models that support those features.
- Check the server logs (`api_usage.log`) for detailed request information.
- The proxy rotation and TLS fingerprinting are handled automatically by the backend.