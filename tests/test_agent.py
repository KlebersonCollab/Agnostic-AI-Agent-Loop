from providers.base import BaseLLMProvider, ChatMessage, MessageRole, ToolCall, ToolDefinition
from agent import Agent, AgentListener

class MockProvider(BaseLLMProvider):
    def __init__(self, responses):
        super().__init__("mock-model")
        self.responses = responses
        self.call_count = 0

    def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


class CountingListener(AgentListener):
    def __init__(self):
        self.steps = 0
        self.thoughts = []
        self.tool_calls = []
        self.tool_outputs = []
        self.completed = False

    def on_step_start(self, step, max_steps):
        self.steps += 1

    def on_thought(self, thought):
        self.thoughts.append(thought)

    def on_tool_call(self, name, arguments, call_id):
        self.tool_calls.append((name, arguments))

    def on_tool_output(self, name, result):
        self.tool_outputs.append((name, result))

    def on_error(self, message):
        pass

    def on_complete(self):
        self.completed = True


def test_agent_react_loop_with_tool_call():
    # Define a mock flow:
    # 1. First call: Thought + Tool Call (calculate 2+2)
    # 2. Second call: Final Answer summarization
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="I need to calculate 2 + 2.",
            tool_calls=[
                ToolCall(id="call_1", name="calculate", arguments={"expression": "2 + 2"})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="The result of the calculation is 4. I am finished."
        )
    ]
    
    provider = MockProvider(responses)
    
    # Mock tools mapping
    tools_metadata = [
        ToolDefinition(
            name="calculate",
            description="Evaluate a math expression",
            parameters={"type": "object", "properties": {"expression": {"type": "string"}}}
        )
    ]
    tools_map = {
        "calculate": lambda expression: str(eval(expression))
    }
    
    listener = CountingListener()
    agent = Agent(
        provider=provider,
        tools=tools_metadata,
        tools_map=tools_map,
        listener=listener,
        max_steps=5
    )
    
    agent.run("What is 2 + 2?")
    
    assert listener.steps == 2
    assert len(listener.thoughts) == 2
    assert listener.tool_calls == [("calculate", {"expression": "2 + 2"})]
    assert listener.tool_outputs == [("calculate", "4")]
    assert listener.completed is True
