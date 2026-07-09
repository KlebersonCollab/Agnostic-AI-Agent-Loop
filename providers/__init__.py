from typing import Optional

from .base import (
    BaseLLMProvider,
    ChatMessage,
    MessageRole,
    ToolCall,
    ToolDefinition
)
from .openai import OpenAIProvider, OpenAICompatibleProvider, OpenRouterProvider
from .gemini import GeminiProvider
from .anthropic import AnthropicProvider

# Factory function to build LLM providers
def get_provider(
    provider_name: str,
    model_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> BaseLLMProvider:
    provider_name = provider_name.lower()
    if provider_name == "openai":
        return OpenAIProvider(model_name=model_name, api_key=api_key, base_url=base_url, **kwargs)
    elif provider_name in ("openai_compatible", "ollama", "groq", "deepseek"):
        return OpenAICompatibleProvider(model_name=model_name, api_key=api_key, base_url=base_url, **kwargs)
    elif provider_name == "openrouter":
        return OpenRouterProvider(model_name=model_name, api_key=api_key, **kwargs)
    elif provider_name == "gemini":
        return GeminiProvider(model_name=model_name, api_key=api_key, **kwargs)
    elif provider_name == "anthropic":
        return AnthropicProvider(model_name=model_name, api_key=api_key, **kwargs)
    else:
        raise ValueError(
            f"Unsupported provider: {provider_name}. "
            f"Supported providers are: 'openai', 'gemini', 'anthropic', 'openrouter', 'openai_compatible' (ollama, groq, deepseek, etc.)"
        )
