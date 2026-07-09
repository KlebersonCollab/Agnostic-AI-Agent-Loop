import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
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
