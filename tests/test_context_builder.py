import os
import shutil
import pytest
from context_builder import ContextBuilder
from providers.base import BaseLLMProvider, ChatMessage, MessageRole, ToolCall
from agent import Agent

# Setup temporary skills and rules directories for test isolation
TEST_SKILLS_DIR = "temp_test_skills"
TEST_RULES_DIR = "temp_test_rules"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup directories
    os.makedirs(TEST_SKILLS_DIR, exist_ok=True)
    os.makedirs(TEST_RULES_DIR, exist_ok=True)
    
    # Create a dummy skill with frontmatter
    debug_skill_dir = os.path.join(TEST_SKILLS_DIR, "debug")
    os.makedirs(debug_skill_dir, exist_ok=True)
    with open(os.path.join(debug_skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("""---
name: debug
description: Analyzes errors and reports bugs.
keywords: ["debug", "bug", "error"]
---
This is the full detailed guideline for debugging code.
Step 1: Check logs.
Step 2: Trace stack.
""")
        
    # Create another dummy skill
    refactor_skill_dir = os.path.join(TEST_SKILLS_DIR, "refactor")
    os.makedirs(refactor_skill_dir, exist_ok=True)
    with open(os.path.join(refactor_skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("""---
name: refactor
description: Improves code quality.
keywords: ["clean", "solid"]
---
Refactoring guidelines: keep it simple.
""")

    # Create a dummy rule
    with open(os.path.join(TEST_RULES_DIR, "RESEARCH_FIRST.md"), "w", encoding="utf-8") as f:
        f.write("Always research the codebase before implementing changes.")

    yield

    # Clean up directories
    if os.path.exists(TEST_SKILLS_DIR):
        shutil.rmtree(TEST_SKILLS_DIR)
    if os.path.exists(TEST_RULES_DIR):
        shutil.rmtree(TEST_RULES_DIR)


def test_context_builder_initialization():
    base_prompt = "You are a coding assistant."
    builder = ContextBuilder(
        base_system_prompt=base_prompt,
        skills_dir=TEST_SKILLS_DIR,
        rules_dir=TEST_RULES_DIR
    )
    
    # Verify skills cache
    assert "debug" in builder.skills_cache
    assert "refactor" in builder.skills_cache
    
    debug_meta = builder.skills_cache["debug"]["metadata"]
    assert debug_meta["name"] == "debug"
    assert debug_meta["description"] == "Analyzes errors and reports bugs."
    assert debug_meta["keywords"] == ["debug", "bug", "error"]
    
    # Verify body
    assert "This is the full detailed guideline for debugging code." in builder.skills_cache["debug"]["body"]
    
    # Verify rules cache
    assert "RESEARCH_FIRST" in builder.rules_cache
    assert builder.rules_cache["RESEARCH_FIRST"] == "Always research the codebase before implementing changes."
    assert "RESEARCH_FIRST" in builder.active_rules


def test_context_builder_load_unload_skill():
    builder = ContextBuilder(
        base_system_prompt="Base prompt.",
        skills_dir=TEST_SKILLS_DIR,
        rules_dir=TEST_RULES_DIR
    )
    
    # Initially inactive
    assert "debug" not in builder.active_skills
    
    # Load skill
    assert builder.load_skill("debug") is True
    assert "debug" in builder.active_skills
    
    # Unload skill
    assert builder.unload_skill("debug") is True
    assert "debug" not in builder.active_skills
    
    # Non-existent skill
    assert builder.load_skill("non_existent") is False


def test_context_builder_build_prompt():
    builder = ContextBuilder(
        base_system_prompt="Base prompt.",
        skills_dir=TEST_SKILLS_DIR,
        rules_dir=TEST_RULES_DIR
    )
    
    # 1. Prompt with default loaded rules, and skills metadata only
    prompt = builder.build_prompt()
    assert "Base prompt." in prompt
    assert "## Active Rules & Instructions Constraints" in prompt
    assert "Rule: RESEARCH_FIRST" in prompt
    assert "Always research the codebase before implementing changes." in prompt
    assert "## Available Skills" in prompt
    assert "debug" in prompt
    assert "Analyzes errors and reports bugs." in prompt
    
    # Should NOT contain full body of debug skill yet
    assert "This is the full detailed guideline for debugging code." not in prompt
    
    # 2. Load the debug skill and rebuild
    builder.load_skill("debug")
    prompt_with_skill = builder.build_prompt()
    assert "## Active Skills Detailed Guidelines" in prompt_with_skill
    assert "Skill Guideline: debug" in prompt_with_skill
    assert "This is the full detailed guideline for debugging code." in prompt_with_skill


def test_agent_tool_interception():
    # Setup mock provider to simulate agent calling load_skill and unload_skill
    responses = [
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="I need to debug, let me load the debug skill.",
            tool_calls=[
                ToolCall(id="call_load", name="load_skill", arguments={"name": "debug"})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="I am done, let me unload the debug skill.",
            tool_calls=[
                ToolCall(id="call_unload", name="unload_skill", arguments={"name": "debug"})
            ]
        ),
        ChatMessage(
            role=MessageRole.ASSISTANT,
            content="Task complete."
        )
    ]
    
    class MockLLM(BaseLLMProvider):
        def __init__(self, responses):
            super().__init__("mock-model")
            self.responses = responses
            self.call_count = 0
            self.prompt_histories = []

        def _generate(self, messages, tools=None, temperature=0.7, max_tokens=None):
            self.prompt_histories.append(messages[0].content)
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp

    provider = MockLLM(responses)
    agent = Agent(
        provider=provider,
        tools=[],
        tools_map={},
        max_steps=5,
        write_checkpoint_file=False
    )
    
    # Override skills/rules dirs to use the test ones
    agent.context_builder.skills_dirs = [TEST_SKILLS_DIR]
    agent.context_builder.rules_dirs = [TEST_RULES_DIR]
    agent.context_builder.skills_cache.clear()
    agent.context_builder.rules_cache.clear()
    agent.context_builder.active_rules.clear()
    agent.context_builder.load_all_skills()
    agent.context_builder.load_all_rules()
    
    agent.run("Fix the bug")
    
    # 3 steps occurred
    assert provider.call_count == 3
    
    # Check that in step 1, the debug skill body was NOT in the system prompt
    assert "This is the full detailed guideline for debugging code." not in provider.prompt_histories[0]
    
    # Check that in step 2 (after load_skill interception), the debug skill body WAS in the system prompt
    assert "This is the full detailed guideline for debugging code." in provider.prompt_histories[1]
    
    # Check that in step 3 (after unload_skill interception), the debug skill body WAS removed
    assert "This is the full detailed guideline for debugging code." not in provider.prompt_histories[2]
