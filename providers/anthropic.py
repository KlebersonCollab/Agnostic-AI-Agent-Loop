import os
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ChatMessage, MessageRole, ToolCall, ToolDefinition

# Anthropic Provider Implementation
class AnthropicProvider(BaseLLMProvider):
    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        from anthropic import Anthropic
        
        self.client = Anthropic(
            api_key=self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def _generate(
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
