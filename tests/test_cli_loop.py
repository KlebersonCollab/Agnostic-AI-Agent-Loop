from unittest.mock import patch, MagicMock
import pytest
from cli import run_cli

@patch("cli.Agent")
@patch("cli.get_provider")
@patch("cli.argparse.ArgumentParser.parse_args")
def test_cli_one_shot_loop(mock_parse_args, mock_get_provider, mock_Agent):
    # Setup argument mocking
    mock_args = MagicMock()
    mock_args.provider = "gemini"
    mock_args.model = "gemini-2.5-flash"
    mock_args.api_key = None
    mock_args.base_url = None
    mock_args.prompt = "/loop create a massive web application"
    mock_args.max_steps = 15
    mock_args.no_front = True
    mock_args.no_browser = True
    mock_parse_args.return_value = mock_args

    # Mock agent instance
    mock_agent_instance = MagicMock()
    mock_agent_instance.exit_reason = "FINISHED"
    mock_Agent.return_value = mock_agent_instance

    # Run CLI
    with patch("os.path.exists", return_value=False):
        run_cli()

    # Assert agent max_steps was set to 10000 and run was called with clean prompt
    assert mock_agent_instance.max_steps == 10000
    mock_agent_instance.run.assert_called_once_with("create a massive web application")
