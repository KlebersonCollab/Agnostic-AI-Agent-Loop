import os
import json
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ChatMessage, MessageRole, ToolCall, ToolDefinition

# OpenAI Provider Implementation
class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        from openai import OpenAI
        
        # Falls back to OPENAI_API_KEY environment variable if api_key is None
        self.client = OpenAI(
            api_key=self.api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL")
        )

    def _generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatMessage:
        openai_messages = self._convert_messages(messages)
        openai_tools = self._convert_tools(tools) if tools else None

        params = {
            "model": self.model_name,
            "messages": openai_messages,
            "temperature": temperature,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        if openai_tools:
            params["tools"] = openai_tools

        response = self.client.chat.completions.create(**params)
        
        if not response or not hasattr(response, "choices") or not response.choices:
            # Check for error fields in response (common in OpenRouter)
            error_details = ""
            if hasattr(response, "error") and response.error:
                error_details = f" Error: {response.error}"
            elif isinstance(response, dict) and "error" in response:
                error_details = f" Error: {response['error']}"
            elif hasattr(response, "response") and hasattr(response.response, "json"):
                try:
                    js = response.response.json()
                    if "error" in js:
                        error_details = f" Error: {js['error']}"
                except Exception:
                    pass
            
            raise ValueError(
                f"Model response has no choices or returned an error.{error_details} "
                f"Raw response: {response}"
            )

        choice_message = response.choices[0].message
        return self._parse_response(choice_message)

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        converted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                converted.append({"role": "system", "content": msg.content})
            elif msg.role == MessageRole.USER:
                converted.append({"role": "user", "content": msg.content})
            elif msg.role == MessageRole.ASSISTANT:
                item = {"role": "assistant"}
                if msg.content is not None:
                    item["content"] = msg.content
                if msg.tool_calls:
                    item["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                converted.append(item)
            elif msg.role == MessageRole.TOOL:
                converted.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.name or "tool",
                    "content": msg.content or ""
                })
        return converted

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        converted = []
        for t in tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
            })
        return converted

    def _parse_response(self, choice_message) -> ChatMessage:
        content = choice_message.content
        tool_calls = None
        
        if choice_message.tool_calls:
            tool_calls = []
            for tc in choice_message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {"raw_arguments": tc.function.arguments}
                
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args
                    )
                )

        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls
        )


# Generic OpenAI Compatible Provider (Ollama, Groq, DeepSeek, etc.)
class OpenAICompatibleProvider(OpenAIProvider):
    """
    Subclass of OpenAIProvider that allows specifying custom base_url and API keys.
    Useful for local Ollama, Groq, DeepSeek, or other third-party OpenAI-like endpoints.
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        # Default local Ollama endpoint if nothing else is specified
        default_base_url = base_url or "http://localhost:11434/v1"
        default_api_key = api_key or "ollama"
        super().__init__(model_name=model_name, api_key=default_api_key, base_url=default_base_url, **kwargs)


# OpenRouter Provider Implementation
class OpenRouterProvider(OpenAIProvider):
    """
    Subclass of OpenAIProvider specifically pre-configured for OpenRouter.
    Includes default headers recommended by OpenRouter for discovery.
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        base_url = "https://openrouter.ai/api/v1"
        default_headers = {
            "HTTP-Referer": "https://github.com/google/antigravity",
            "X-Title": "Antigravity Agent",
        }
        super().__init__(
            model_name=model_name,
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY"),
            base_url=base_url,
            **kwargs
        )
        self.client.default_headers.update(default_headers)
