import time
import pytest
from providers.base import BaseLLMProvider, ChatMessage, MessageRole, ToolCall, ToolDefinition
from agent import Agent, AgentListener

class MockParallelProvider(BaseLLMProvider):
    def __init__(self, responses):
        super().__init__("mock-model")
        self.responses = responses
        self.call_count = 0

    def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


class TrackingListener(AgentListener):
    def __init__(self):
        self.tool_calls = []
        self.tool_outputs = []
        self.completed = False

    def on_tool_call(self, name, arguments, call_id):
        self.tool_calls.append((name, arguments, call_id))

    def on_tool_output(self, name, result):
        self.tool_outputs.append((name, result))

    def on_complete(self):
        self.completed = True


def test_concurrent_tool_execution_time_and_order():
    # Define a tool that sleeps
    def sleep_tool(seconds: float):
        time.sleep(seconds)
        return f"Slept for {seconds}s"

    # Define mock LLM responses:
    # Step 1: LLM returns TWO parallel tool calls
    # Step 2: Final response
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="I will run two sleep tasks in parallel.",
            tool_calls=[
                ToolCall(id="call_t1", name="sleep_tool", arguments={"seconds": 0.5}),
                ToolCall(id="call_t2", name="sleep_tool", arguments={"seconds": 0.5})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Both tasks finished. I am done."
        )
    ]
    
    provider = MockParallelProvider(responses)
    
    tools_metadata = [
        ToolDefinition(
            name="sleep_tool",
            description="Sleeps for a given number of seconds",
            parameters={"type": "object", "properties": {"seconds": {"type": "number"}}}
        )
    ]
    tools_map = {
        "sleep_tool": sleep_tool
    }
    
    listener = TrackingListener()
    agent = Agent(
        provider=provider,
        tools=tools_metadata,
        tools_map=tools_map,
        listener=listener,
        max_steps=5,
        write_checkpoint_file=False
    )
    
    start_time = time.monotonic()
    agent.run("Run two sleep tasks.")
    end_time = time.monotonic()
    
    elapsed = end_time - start_time
    
    # Assert elapsed time is closer to 0.5s than 1.0s (running sequentially would take >= 1.0s)
    # Give a bit of buffer for environment thread scheduling overhead
    assert elapsed < 0.9, f"Parallel execution took too long: {elapsed:.2f} seconds"
    
    # Verify listener output order matches the requested calls order
    assert len(listener.tool_calls) == 2
    assert listener.tool_calls[0][2] == "call_t1"
    assert listener.tool_calls[1][2] == "call_t2"
    
    assert len(listener.tool_outputs) == 2
    assert listener.tool_outputs[0][1] == "Slept for 0.5s"
    assert listener.tool_outputs[1][1] == "Slept for 0.5s"
    
    # Verify history order
    # history[0] = SYSTEM
    # history[1] = USER
    # history[2] = ASSISTANT (with tool calls)
    # history[3] = TOOL response 1
    # history[4] = TOOL response 2
    # history[5] = ASSISTANT (final summary)
    assert len(agent.history) == 6
    assert agent.history[3].role == MessageRole.TOOL
    assert agent.history[3].name == "sleep_tool"
    assert agent.history[3].tool_call_id == "call_t1"
    assert agent.history[3].content == "Slept for 0.5s"
    
    assert agent.history[4].role == MessageRole.TOOL
    assert agent.history[4].name == "sleep_tool"
    assert agent.history[4].tool_call_id == "call_t2"
    assert agent.history[4].content == "Slept for 0.5s"
    
    assert listener.completed is True


def test_concurrent_tool_execution_error_safety():
    # Define a tool that crashes, and one that succeeds
    def crash_tool():
        raise ValueError("Something went wrong!")

    def ok_tool():
        return "OK"

    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="I will run one failing tool and one succeeding tool.",
            tool_calls=[
                ToolCall(id="call_crash", name="crash_tool", arguments={}),
                ToolCall(id="call_ok", name="ok_tool", arguments={})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Handled the outputs."
        )
    ]
    
    provider = MockParallelProvider(responses)
    
    tools_metadata = [
        ToolDefinition(name="crash_tool", description="Fails", parameters={}),
        ToolDefinition(name="ok_tool", description="Succeeds", parameters={})
    ]
    tools_map = {
        "crash_tool": crash_tool,
        "ok_tool": ok_tool
    }
    
    listener = TrackingListener()
    agent = Agent(
        provider=provider,
        tools=tools_metadata,
        tools_map=tools_map,
        listener=listener,
        max_steps=5,
        write_checkpoint_file=False
    )
    
    # Run agent loop
    agent.run("Run both tools.")
    
    # Assert agent did not crash and recorded the failure safely in the history
    assert len(agent.history) == 6
    
    # Check crash tool output in history
    assert agent.history[3].tool_call_id == "call_crash"
    assert "Error executing tool" in agent.history[3].content
    assert "Something went wrong!" in agent.history[3].content
    
    # Check ok tool output in history
    assert agent.history[4].tool_call_id == "call_ok"
    assert agent.history[4].content == "OK"
    
    assert listener.completed is True
