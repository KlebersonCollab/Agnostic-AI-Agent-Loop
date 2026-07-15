import pytest
from providers import get_provider
from providers.openai import OpenAIProvider, OpenAICompatibleProvider, OpenRouterProvider
from providers.base import ChatMessage, MessageRole, BaseLLMProvider

def test_get_provider_factory_validation():
    with pytest.raises(ValueError) as excinfo:
        get_provider("invalid_provider_name", "model-name")
    assert "Unsupported provider" in str(excinfo.value)

def test_get_provider_openai_initialization(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    provider = get_provider("openai", "gpt-4o")
    assert isinstance(provider, OpenAIProvider)
    assert provider.model_name == "gpt-4o"
    assert provider.api_key == "test-key-123"

def test_get_provider_openai_compatible_initialization():
    provider = get_provider("openai_compatible", "local-llama", base_url="http://localhost:8000/v1")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.model_name == "local-llama"
    # Base URL should be set in client
    assert provider.client.base_url == "http://localhost:8000/v1/"

def test_get_provider_openrouter_initialization(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key-456")
    provider = get_provider("openrouter", "meta-llama/llama-3")
    assert isinstance(provider, OpenRouterProvider)
    assert provider.client.default_headers["X-Title"] == "Antigravity Agent"

def test_chat_message_metadata():
    msg = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="hello",
        response_metadata={"key": "val"}
    )
    assert msg.response_metadata == {"key": "val"}

def test_base_provider_latency():
    import time
    class MockLLMProvider(BaseLLMProvider):
        def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
            time.sleep(0.05)  # Simulate API latency
            return ChatMessage(role=MessageRole.ASSISTANT, content="mocked response")
            
    provider = MockLLMProvider(model_name="mock-model")
    res = provider.generate(messages=[])
    assert res.response_metadata is not None
    assert "latency" in res.response_metadata
    assert res.response_metadata["latency"] >= 0.05


