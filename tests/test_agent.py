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


def test_agent_emergency_handover_parent():
    import os
    import json
    from providers.base import ToolCall, ToolDefinition
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Thinking about the task.",
            tool_calls=[
                ToolCall(id="dummy_1", name="calculate", arguments={"expression": "1 + 1"})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Handover report: Completed task A. Blocker: none. Next step: task B."
        )
    ]
    
    class HandoverMockProvider(BaseLLMProvider):
        def __init__(self, responses):
            super().__init__("mock-model")
            self.responses = responses
            self.call_count = 0
            self.received_tools = []

        def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
            self.received_tools.append(tools)
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp

    provider = HandoverMockProvider(responses)
    
    # Ensure any existing checkpoint is removed
    if os.path.exists("checkpoint.json"):
        os.remove("checkpoint.json")

    tools_metadata = [
        ToolDefinition(
            name="calculate",
            description="Evaluate a math expression",
            parameters={"type": "object", "properties": {"expression": {"type": "string"}}}
        )
    ]
    tools_map = {
        "calculate": lambda expression: "2"
    }

    agent = Agent(
        provider=provider,
        tools=tools_metadata,
        tools_map=tools_map,
        max_steps=3,
        write_checkpoint_file=True
    )
    
    agent.run("Do a complex task")
    
    assert agent.exit_reason == "MAX_STEPS_REACHED"
    assert "Handover report" in agent.handover_checkpoint
    
    # Verify that in step 2 (pen-ultimate), tools was set to None
    assert len(provider.received_tools) == 2
    assert provider.received_tools[0] == tools_metadata  # self.tools passed originally
    assert provider.received_tools[1] is None  # emergency step has tools=None
    
    # Verify file was written
    assert os.path.exists("checkpoint.json")
    with open("checkpoint.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exit_reason"] == "MAX_STEPS_REACHED"
    assert "Handover report" in data["handover_checkpoint"]
    assert len(data["history"]) > 0
    
    # Cleanup
    os.remove("checkpoint.json")


def test_agent_emergency_handover_subagent():
    import os
    from providers.base import ToolCall, ToolDefinition
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Thinking about the task.",
            tool_calls=[
                ToolCall(id="dummy_1", name="calculate", arguments={"expression": "1 + 1"})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Handover report: Completed subtask A."
        )
    ]
    
    class HandoverMockProvider(BaseLLMProvider):
        def __init__(self, responses):
            super().__init__("mock-model")
            self.responses = responses
            self.call_count = 0
            self.received_tools = []

        def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
            self.received_tools.append(tools)
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp

    provider = HandoverMockProvider(responses)
    
    if os.path.exists("checkpoint.json"):
        os.remove("checkpoint.json")

    tools_metadata = [
        ToolDefinition(
            name="calculate",
            description="Evaluate a math expression",
            parameters={"type": "object", "properties": {"expression": {"type": "string"}}}
        )
    ]
    tools_map = {
        "calculate": lambda expression: "2"
    }

    agent = Agent(
        provider=provider,
        tools=tools_metadata,
        tools_map=tools_map,
        max_steps=3,
        write_checkpoint_file=False
    )
    
    agent.run("Do a subagent task")
    
    assert agent.exit_reason == "MAX_STEPS_REACHED"
    assert "Handover report" in agent.handover_checkpoint
    assert not os.path.exists("checkpoint.json")


