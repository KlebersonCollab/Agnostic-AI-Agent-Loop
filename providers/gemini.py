import os
import json
import uuid
from typing import List, Any, Optional
from .base import BaseLLMProvider, ChatMessage, MessageRole, ToolCall, ToolDefinition

# Gemini Provider Implementation
class GeminiProvider(BaseLLMProvider):
    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        self.api_key = self.api_key or os.environ.get("GEMINI_API_KEY")
        from google import genai
        
        self.client = genai.Client(
            api_key=self.api_key
        )

    def _generate(
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

        chat_msg = self._parse_response(response)
        if chat_msg.response_metadata is None:
            chat_msg.response_metadata = {}
        chat_msg.response_metadata["model_name"] = self.model_name
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            chat_msg.response_metadata.update({
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
            })
        else:
            chat_msg.response_metadata.update({
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            })
        return chat_msg


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
