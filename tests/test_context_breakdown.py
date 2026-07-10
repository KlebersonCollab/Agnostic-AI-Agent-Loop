from context.breakdown import calculate_context_breakdown
from providers.base import BaseLLMProvider, ChatMessage, MessageRole, ToolDefinition
from agent import Agent

class DummyProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__("dummy-model")
    def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
        return ChatMessage(role=MessageRole.ASSISTANT, content="Done")

def test_calculate_context_breakdown():
    provider = DummyProvider()
    tools = [
        ToolDefinition(name="test_tool", description="A test tool", parameters={"type": "object", "properties": {}})
    ]
    agent = Agent(provider=provider, tools=tools, tools_map={})
    
    # Run breakdown on clean agent state
    bd = calculate_context_breakdown(agent)
    
    assert bd["base_system"] > 0
    assert bd["tools"] > 0
    assert bd["history"] == 0  # no history beyond system prompt yet
    assert bd["total"] == bd["base_system"] + bd["rules"] + bd["skills_metadata"] + bd["skills_body"] + bd["tools"] + bd["history"]
    
    # Load some history
    agent.history.append(ChatMessage(role=MessageRole.USER, content="Hello " * 100)) # ~100 tokens
    bd2 = calculate_context_breakdown(agent)
    assert bd2["history"] > bd["history"]

def test_calculate_breakdown_with_rules_and_skills():
    provider = DummyProvider()
    agent = Agent(provider=provider, tools=[], tools_map={})
    
    # Inject mock rules and skills in the cache
    agent.context_builder.rules_cache = {"TestRule": "This is a test rule constraint."}
    agent.context_builder.active_rules = {"TestRule"}
    
    agent.context_builder.skills_cache = {
        "TestSkill": {
            "metadata": {"name": "TestSkill", "description": "Desc", "keywords": ["test"]},
            "body": "Detailed skill body content guide."
        }
    }
    agent.context_builder.active_skills = {"TestSkill"}
    
    bd = calculate_context_breakdown(agent)
    assert bd["rules"] > 0
    assert bd["skills_metadata"] > 0
    assert bd["skills_body"] > 0
    assert bd["total"] == bd["base_system"] + bd["rules"] + bd["skills_metadata"] + bd["skills_body"] + bd["tools"] + bd["history"]

