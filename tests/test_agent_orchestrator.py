import argparse
from unittest.mock import patch, MagicMock
from providers.base import ChatMessage, MessageRole, ToolCall
from agent import Agent, ORCHESTRATOR_SYSTEM_PROMPT, SYSTEM_PROMPT
from tools import get_orchestrator_tools, get_classic_tools, ORCHESTRATOR_TOOL_NAMES
from tests.test_agent import MockProvider, CountingListener
from cli import run_cli


def test_tool_filtering():
    # Verify Orchestrator tools
    orch_metadata, orch_map = get_orchestrator_tools()
    orch_names = {t.name for t in orch_metadata}
    
    assert orch_names == ORCHESTRATOR_TOOL_NAMES
    assert "spawn_subagents_parallel" in orch_names
    assert "search_memory" in orch_names
    assert "read_file" not in orch_names
    assert "write_file" not in orch_names
    assert "execute_command" not in orch_names

    # Verify Classic tools
    classic_metadata, classic_map = get_classic_tools()
    classic_names = {t.name for t in classic_metadata}
    
    assert "spawn_subagents_parallel" in classic_names
    assert "read_file" in classic_names
    assert "write_file" in classic_names
    assert "execute_command" in classic_names


def test_agent_orchestrator_prompt():
    # Verify that the system prompt passed to the agent matches the expected orchestrator prompt
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="I am ready to coordinate."
        )
    ]
    provider = MockProvider(responses)
    orch_metadata, orch_map = get_orchestrator_tools()
    
    agent = Agent(
        provider=provider,
        tools=orch_metadata,
        tools_map=orch_map,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT
    )
    
    # Run the agent step
    agent.run("Delegate some work")
    
    # Verify that history[0] (system prompt) contains ORCHESTRATOR_SYSTEM_PROMPT elements
    assert "strategic orchestrator and leader" in agent.history[0].content


@patch("cli.argparse.ArgumentParser.parse_args")
@patch("cli.get_provider")
@patch("cli.Agent")
def test_cli_mode_parsing(mock_agent_class, mock_get_provider, mock_parse_args):
    # Mock CLI arguments
    mock_args = argparse.Namespace(
        provider="gemini",
        model="gemini-2.5-flash",
        api_key=None,
        base_url=None,
        prompt="List files",
        max_steps=10,
        front_host="127.0.0.1",
        front_port=8090,
        no_front=True,
        no_browser=True,
        mode="orchestrator"
    )
    mock_parse_args.return_value = mock_args
    
    # Setup mock provider and listener
    mock_provider = MagicMock()
    mock_get_provider.return_value = mock_provider
    
    # Run CLI
    try:
        run_cli()
    except SystemExit:
        pass
    
    # Assert Agent constructor was called with Orchestrator prompt and tools
    mock_agent_class.assert_called_once()
    kwargs = mock_agent_class.call_args[1]
    
    assert kwargs["system_prompt"] == ORCHESTRATOR_SYSTEM_PROMPT
    tool_names = {t.name for t in kwargs["tools"]}
    assert tool_names == ORCHESTRATOR_TOOL_NAMES
