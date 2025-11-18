# Nebius AI Integration

## Overview
Nebius provides enterprise-grade LLM access via OpenAI-compatible API.

## Available Models
- **Qwen3-235B** (default): State-of-the-art reasoning, 235B params
- **Qwen2.5-Coder-7B**: Code-specialized, fast inference
- **Llama-3.3-70B**: General purpose, high quality
- **DeepSeek-R1**: Advanced reasoning model
- **Gemma-2-9B**: Fast, efficient

## Usage

### Environment Setup
```bash
export NEBIUS_API_KEY="your_key_here"
```

### CLI
```bash
qwen-dev --provider nebius
```

### Python API
```python
from qwen_dev_cli.core.providers.nebius import NebiusProvider

provider = NebiusProvider()
response = await provider.chat([
    {"role": "user", "content": "Hello!"}
])
```

### Streaming
```python
async for chunk in provider.stream_chat(messages):
    print(chunk, end="", flush=True)
```

## Features
- ✅ Streaming & non-streaming
- ✅ Temperature control
- ✅ Max tokens configuration
- ✅ Multi-turn conversations
- ✅ Context awareness
- ✅ Concurrent requests
- ✅ Error handling & retries

## Performance
- Latency: ~200-500ms first token
- Throughput: 20-50 tokens/s
- Cost: $50 free tier available

## Testing
```bash
pytest tests/test_nebius_integration.py -v
```

All tests passing: ✅ 9/9 (17.52s)
