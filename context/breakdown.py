from __future__ import annotations
import json
import os

def _chars_to_tokens(text_or_len: str | int) -> int:
    if isinstance(text_or_len, int):
        return (text_or_len + 3) // 4
    if not text_or_len:
        return 0
    return (len(text_or_len) + 3) // 4

def calculate_context_breakdown(agent) -> dict:
    builder = agent.context_builder
    
    # 1. Compile the full system prompt to get exact total system size
    full_sys_prompt = builder.build_prompt(agent.history)
    total_sys_tokens = _chars_to_tokens(full_sys_prompt)
    
    # Calculate parts of system prompt to break it down
    # Active Rules
    rules_size = 0
    if builder.active_rules:
        rules_size += len("\n## Active Rules & Instructions Constraints")
        for r in builder.active_rules:
            if r in builder.rules_cache:
                rules_size += len(f"### Rule: {r}\n{builder.rules_cache[r]}")
    rules_tokens = _chars_to_tokens(rules_size)
    
    # Skills Metadata
    skills_meta_size = 0
    if builder.skills_cache:
        skills_meta_size += len("\n## Available Skills\n") + len(
            "You have access to specialized skills. Only their metadata is currently loaded. "
            "To load the detailed guidelines for a skill, you MUST call the `load_skill(name)` tool. "
            "Once you no longer need the skill's guidelines, call the `unload_skill(name)` tool to free context space."
        )
        for name, data in builder.skills_cache.items():
            meta = data["metadata"]
            desc = meta.get("description", "No description available.")
            kws = str(meta.get("keywords", []))
            skills_meta_size += len(f"- **{name}**: {desc} (Keywords: {kws})")
    skills_meta_tokens = _chars_to_tokens(skills_meta_size)
    
    # Active Skills Body
    skills_body_size = 0
    if builder.active_skills:
        skills_body_size += len("\n## Active Skills Detailed Guidelines")
        for s in builder.active_skills:
            if s in builder.skills_cache:
                skills_body_size += len(f"### Skill Guideline: {s}\n{builder.skills_cache[s]['body']}")
    skills_body_tokens = _chars_to_tokens(skills_body_size)
    
    # Base System Prompt (Base + Memory Constraints + AGENTS/DESIGN MDs)
    base_sys_tokens = max(0, total_sys_tokens - rules_tokens - skills_meta_tokens - skills_body_tokens)
    
    # 2. Tool Definitions
    tools_size = 0
    for tool_def in agent.tools:
        tools_size += len(json.dumps(tool_def.model_dump()))
    tools_tokens = _chars_to_tokens(tools_size)
    
    # 3. Conversation History (excluding history[0] system prompt)
    history_size = 0
    if len(agent.history) > 1:
        for msg in agent.history[1:]:
            if msg.content:
                history_size += len(msg.content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    history_size += len(json.dumps(tc.model_dump()))
    history_tokens = _chars_to_tokens(history_size)
    
    total = total_sys_tokens + tools_tokens + history_tokens
    
    return {
        "base_system": base_sys_tokens,
        "rules": rules_tokens,
        "skills_metadata": skills_meta_tokens,
        "skills_body": skills_body_tokens,
        "tools": tools_tokens,
        "history": history_tokens,
        "total": total
    }
