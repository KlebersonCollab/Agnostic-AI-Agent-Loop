import os
import time
import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables
load_dotenv()

console = Console()

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
    response_metadata: Optional[Dict[str, Any]] = None


# Standardized tool definition representation
class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


def retry_with_backoff(retries: int = 5, backoff_in_seconds: float = 1.0, max_backoff: float = 32.0):
    """
    Decorator that retries a function with exponential backoff and jitter.
    Catches transient exceptions (rate limits, timeouts, server errors)
    while immediately raising permanent exceptions (auth, bad requests).
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            x = backoff_in_seconds
            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err_str = str(e).lower()
                    is_permanent = False
                    
                    # 1. Check for standard SDK exceptions
                    try:
                        import openai
                        if isinstance(e, (openai.AuthenticationError, openai.PermissionDeniedError, openai.BadRequestError)):
                            is_permanent = True
                    except ImportError:
                        pass
                        
                    try:
                        import anthropic
                        if isinstance(e, (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.BadRequestError)):
                            is_permanent = True
                    except ImportError:
                        pass
                    
                    # 2. String based checks for API gateways (like OpenRouter)
                    permanent_keywords = ["auth", "unauthorized", "api key", "permission", "invalid_api_key", "credentials", "401", "403"]
                    if any(term in err_str for term in permanent_keywords):
                        if "rate limit" not in err_str and "exhausted" not in err_str:
                            is_permanent = True
                    
                    if is_permanent or attempt == retries:
                        raise e
                    
                    # Calculate exponential backoff with jitter
                    sleep_time = x * (2 ** (attempt - 1)) + random.uniform(0, 0.1 * x)
                    sleep_time = min(sleep_time, max_backoff)
                    
                    # Render warning using Rich Console
                    console.print(
                        f"\n[bold yellow]⚠️ API call failed: {e}. "
                        f"Retrying in {sleep_time:.2f}s (Attempt {attempt}/{retries})...[/]"
                    )
                    time.sleep(sleep_time)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Abstract Base Class for all LLM Providers
class BaseLLMProvider(ABC):
    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key
        self.kwargs = kwargs

    @retry_with_backoff(retries=5, backoff_in_seconds=1.0)
    def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatMessage:
        """
        Public entry point with built-in retry and backoff safety.
        Delegates the actual LLM call to subclasses.
        """
        start_time = time.time()
        res = self._generate(messages, tools, temperature, max_tokens)
        duration = time.time() - start_time
        if res.response_metadata is None:
            res.response_metadata = {}
        res.response_metadata["latency"] = duration
        return res


    @abstractmethod
    def _generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> ChatMessage:
        """
        Subclasses implement the concrete API call here.
        """
        pass
