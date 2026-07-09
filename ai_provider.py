import os
import json
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Define standardized roles for the agent loop
class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

# Standardized tool call representation
class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

# Standardized chat message representation
class ChatMessage(BaseModel):
    role: MessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

# Standardized tool definition representation
class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})

# Abstract Base Class for all LLM Providers
class BaseLLMProvider(ABC):
    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key
        self.kwargs = kwargs

    @abstractmethod
    def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatMessage:
        """
        Generate a response based on the conversation history and optional tools.
        """
        pass


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

    def generate(
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


# Anthropic Provider Implementation
class AnthropicProvider(BaseLLMProvider):
    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        from anthropic import Anthropic
        
        self.client = Anthropic(
            api_key=self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatMessage:
        # Anthropic processes system messages separately
        system_instructions = []
        conversation_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                if msg.content:
                    system_instructions.append(msg.content)
            else:
                conversation_messages.append(msg)

        system_prompt = "\n".join(system_instructions) if system_instructions else None
        
        # Convert the remaining messages to Anthropic's block format
        anthropic_messages = self._convert_messages(conversation_messages)
        anthropic_tools = self._convert_tools(tools) if tools else None

        params = {
            "model": self.model_name,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_prompt:
            params["system"] = system_prompt
        if anthropic_tools:
            params["tools"] = anthropic_tools

        response = self.client.messages.create(**params)
        return self._parse_response(response)

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        raw_msgs = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                raw_msgs.append({
                    "role": "user",
                    "content": msg.content or ""
                })
            elif msg.role == MessageRole.ASSISTANT:
                content_blocks = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                
                for tc in msg.tool_calls or []:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments
                    })
                raw_msgs.append({
                    "role": "assistant",
                    "content": content_blocks if content_blocks else ""
                })
            elif msg.role == MessageRole.TOOL:
                raw_msgs.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content or "",
                        }
                    ]
                })

        # Anthropic requires alternating user/assistant messages.
        # Let's merge sequential messages with the same role.
        merged_msgs = []
        for msg in raw_msgs:
            if not merged_msgs:
                merged_msgs.append(msg)
                continue
            
            last_msg = merged_msgs[-1]
            if last_msg["role"] == msg["role"]:
                # Merge content
                last_content = last_msg["content"]
                new_content = msg["content"]
                
                # Normalize both to lists of blocks for merging
                if isinstance(last_content, str):
                    last_content = [{"type": "text", "text": last_content}]
                if isinstance(new_content, str):
                    new_content = [{"type": "text", "text": new_content}]
                
                last_msg["content"] = last_content + new_content
            else:
                merged_msgs.append(msg)

        return merged_msgs

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        converted = []
        for t in tools:
            converted.append({
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters
            })
        return converted

    def _parse_response(self, response) -> ChatMessage:
        content_text = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input
                    )
                )

        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=content_text if content_text else None,
            tool_calls=tool_calls if tool_calls else None
        )


# Gemini Provider Implementation
class GeminiProvider(BaseLLMProvider):
    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        from google import genai
        
        self.client = genai.Client(
            api_key=self.api_key or os.environ.get("GEMINI_API_KEY")
        )

    def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatMessage:
        from google.genai import types

        # Extract system messages for system_instruction
        system_instructions = []
        chat_contents = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                if msg.content:
                    system_instructions.append(msg.content)
            else:
                chat_contents.append(msg)

        system_instruction = "\n".join(system_instructions) if system_instructions else None
        
        # Convert chat history to Gemini types
        gemini_contents = self._convert_messages(chat_contents)
        
        # Build Configuration
        config_params = {}
        if system_instruction:
            config_params["system_instruction"] = system_instruction
        if temperature is not None:
            config_params["temperature"] = temperature
        if max_tokens is not None:
            config_params["max_output_tokens"] = max_tokens
        if tools:
            config_params["tools"] = self._convert_tools(tools)

        config = types.GenerateContentConfig(**config_params) if config_params else None

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=gemini_contents,
            config=config
        )

        return self._parse_response(response)

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Any]:
        from google.genai import types
        gemini_contents = []

        for msg in messages:
            if msg.role == MessageRole.USER:
                gemini_contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg.content or "")]
                    )
                )
            elif msg.role == MessageRole.ASSISTANT:
                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))
                
                for tc in msg.tool_calls or []:
                    parts.append(
                        types.Part.from_function_call(
                            name=tc.name,
                            args=tc.arguments
                        )
                    )
                gemini_contents.append(
                    types.Content(
                        role="model",
                        parts=parts
                    )
                )
            elif msg.role == MessageRole.TOOL:
                # Format response as dictionary for Gemini
                response_dict = {}
                if msg.content:
                    try:
                        response_dict = json.loads(msg.content)
                        if not isinstance(response_dict, dict):
                            response_dict = {"result": response_dict}
                    except Exception:
                        response_dict = {"result": msg.content}
                
                gemini_contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=msg.name or "tool",
                                response=response_dict
                            )
                        ]
                    )
                )

        return gemini_contents

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Any]:
        from google.genai import types
        declarations = []
        for t in tools:
            declarations.append(
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters=t.parameters
                )
            )
        return [types.Tool(function_declarations=declarations)]

    def _parse_response(self, response) -> ChatMessage:
        if not response or not hasattr(response, "candidates") or not response.candidates:
            block_reason = ""
            if hasattr(response, "prompt_feedback") and response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason = f" (Blocked: {response.prompt_feedback.block_reason})"
            raise ValueError(f"Gemini returned an empty response or no candidates.{block_reason}")

        tool_calls = []
        
        # Handle function calls
        if response.function_calls:
            for fc in response.function_calls:
                call_id = f"call_{fc.name}_{uuid.uuid4().hex[:6]}"
                args = dict(fc.args) if fc.args else {}
                tool_calls.append(
                    ToolCall(
                        id=call_id,
                        name=fc.name,
                        arguments=args
                    )
                )

        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=response.text if response.text else None,
            tool_calls=tool_calls if tool_calls else None
        )


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
