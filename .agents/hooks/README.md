# Agent Execution Hooks

This directory allows you to extend the agent's behavior dynamically at various stages of execution without editing core files.

## Event Directory Structure

Create subdirectories matching the event names under this directory:

- `.agents/hooks/on_session_start/`
- `.agents/hooks/on_session_complete/`
- `.agents/hooks/on_session_clear/`
- `.agents/hooks/pre_step/`
- `.agents/hooks/post_step/`
- `.agents/hooks/pre_tool_call/`
- `.agents/hooks/post_tool_call/`
- `.agents/hooks/on_tool_error/`
- `.agents/hooks/pre_api_request/`
- `.agents/hooks/post_api_request/`
- `.agents/hooks/on_error/`
