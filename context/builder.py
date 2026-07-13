import os
from typing import Dict, Any, List, Set

class ContextBuilder:
    """
    Registry and compiler for agent system prompts, constraints (rules), and guidelines (skills).
    Parses frontmatter metadata on startup to enable dynamic loading/unloading of detailed contents.
    Searches both the package builtin directory and the current working directory.
    """
    def __init__(self, base_system_prompt: str, skills_dir: str = None, rules_dir: str = None):
        self.base_system_prompt = base_system_prompt
        
        self.skills_dirs: List[str] = []
        self.rules_dirs: List[str] = []
        
        # If directories are specified explicitly, use ONLY those (useful for test isolation)
        if skills_dir or rules_dir:
            if skills_dir:
                self.skills_dirs.append(skills_dir)
            if rules_dir:
                self.rules_dirs.append(rules_dir)
        else:
            # Package root directory (where context/builder.py is located)
            package_root = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(package_root)
            
            # 1. Package builtin dirs
            builtin_agents = os.path.join(project_root, ".agents")
            if os.path.exists(builtin_agents):
                builtin_skills = os.path.join(builtin_agents, "skills")
                builtin_rules = os.path.join(builtin_agents, "rules")
                if os.path.exists(builtin_skills):
                    self.skills_dirs.append(builtin_skills)
                if os.path.exists(builtin_rules):
                    self.rules_dirs.append(builtin_rules)
                    
            # 2. Current working directory dirs (if different from package root)
            cwd_agents = os.path.join(os.getcwd(), ".agents")
            if os.path.abspath(cwd_agents) != os.path.abspath(builtin_agents):
                cwd_skills = os.path.join(cwd_agents, "skills")
                cwd_rules = os.path.join(cwd_agents, "rules")
                if os.path.exists(cwd_skills):
                    self.skills_dirs.append(cwd_skills)
                if os.path.exists(cwd_rules):
                    self.rules_dirs.append(cwd_rules)
        
        # Cache structures:
        # name -> {"metadata": dict, "body": str}
        self.skills_cache: Dict[str, Dict[str, Any]] = {}
        # filename -> content
        self.rules_cache: Dict[str, str] = {}
        
        # AGENTS.md caching
        self.agents_md_mtime: float = 0.0
        self.agents_md_content: str = ""
        
        # DESIGN.md caching
        self.design_md_mtime: float = 0.0
        self.design_md_content: str = ""
        
        # Active sets
        self.active_skills: Set[str] = set()
        self.active_rules: Set[str] = set()
        
        # Discover and parse files
        self.load_all_skills()
        self.load_all_rules()

    def _parse_frontmatter(self, content: str):
        """Parses YAML frontmatter block at the start of a markdown file."""
        if not content.startswith("---"):
            return {}, content
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content
            
        yaml_text = parts[1]
        body = parts[2].strip()
        
        metadata = {}
        for line in yaml_text.strip().split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            # Handle list parsing like ["a", "b"]
            if value.startswith("[") and value.endswith("]"):
                items = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",") if item.strip()]
                metadata[key] = items
            else:
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                metadata[key] = value
                
        return metadata, body

    def load_all_skills(self):
        """Discovers and caches all SKILL.md files under the configured skills directories."""
        for s_dir in self.skills_dirs:
            if not os.path.exists(s_dir):
                continue
            
            for item in os.listdir(s_dir):
                skill_path = os.path.join(s_dir, item)
                if os.path.isdir(skill_path):
                    skill_file = os.path.join(skill_path, "SKILL.md")
                    if os.path.exists(skill_file):
                        try:
                            with open(skill_file, "r", encoding="utf-8") as f:
                                content = f.read()
                            metadata, body = self._parse_frontmatter(content)
                            name = metadata.get("name", item)
                            # CWD skills can override package builtin skills
                            self.skills_cache[name] = {
                                "metadata": metadata,
                                "body": body
                            }
                        except Exception:
                            # Silently skip malformed skills to ensure robust startup
                            pass

    def load_all_rules(self):
        """Discovers and caches all markdown files under the configured rules directories."""
        for r_dir in self.rules_dirs:
            if not os.path.exists(r_dir):
                continue
            
            for item in os.listdir(r_dir):
                if item.endswith(".md"):
                    rule_path = os.path.join(r_dir, item)
                    try:
                        with open(rule_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        rule_name = os.path.splitext(item)[0]
                        # CWD rules can override package builtin rules
                        self.rules_cache[rule_name] = content.strip()
                        # By default, rules are structural constraints and are active
                        self.active_rules.add(rule_name)
                    except Exception:
                        pass

    def load_skill(self, name: str) -> bool:
        """Loads a skill's detailed content into active prompt context."""
        if name in self.skills_cache:
            self.active_skills.add(name)
            return True
        return False

    def unload_skill(self, name: str) -> bool:
        """Unloads a skill's detailed content from active prompt context."""
        if name in self.active_skills:
            self.active_skills.remove(name)
            return True
        return False

    def load_rule(self, name: str) -> bool:
        """Loads a rule/constraint into active prompt context."""
        if name in self.rules_cache:
            self.active_rules.add(name)
            return True
        return False

    def unload_rule(self, name: str) -> bool:
        """Unloads a rule/constraint from active prompt context."""
        if name in self.active_rules:
            self.active_rules.remove(name)
            return True
        return False

    def build_prompt(self, history: List[Any] = None) -> str:
        """Compiles the dynamic system prompt with active rules, skills metadata, and active skills details."""
        prompt_parts = [self.base_system_prompt.strip()]

        # Dynamic loading and caching of local AGENTS.md in the current working directory
        agents_md_path = os.path.join(os.getcwd(), "AGENTS.md")
        if os.path.exists(agents_md_path):
            try:
                mtime = os.path.getmtime(agents_md_path)
                if mtime != self.agents_md_mtime:
                    with open(agents_md_path, "r", encoding="utf-8") as f:
                        self.agents_md_content = f.read().strip()
                    self.agents_md_mtime = mtime
                if self.agents_md_content:
                    prompt_parts.append(f"\n## Project Context (AGENTS.md)\n{self.agents_md_content}")
            except Exception:
                pass
        else:
            self.agents_md_content = ""
            self.agents_md_mtime = 0.0

        # Dynamic loading and caching of local DESIGN.md in the current working directory (only when design/frontend is relevant)
        design_md_path = os.path.join(os.getcwd(), "DESIGN.md")
        if os.path.exists(design_md_path):
            is_design_needed = False
            if history:
                design_keywords = {
                    "design", "frontend", "ui", "ux", "css", "html", "style", "layout", 
                    "component", "color", "tailwind", "react", "vue", "aesthetic", 
                    "visual", "interface", "mockup", "glassmorphism", "animation",
                    "web app", "website", "button", "pixel", "typography", "responsive",
                    "frontend", "figma", "sass", "less", "bootstrap"
                }
                for msg in history:
                    # Check both message content and any tool call names/arguments
                    text_to_check = ""
                    if getattr(msg, "content", None):
                        text_to_check += msg.content.lower()
                    if getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            text_to_check += f" {tc.name.lower()} {str(tc.arguments).lower()}"
                    
                    if any(kw in text_to_check for kw in design_keywords):
                        is_design_needed = True
                        break
            
            if is_design_needed:
                try:
                    mtime = os.path.getmtime(design_md_path)
                    if mtime != self.design_md_mtime:
                        with open(design_md_path, "r", encoding="utf-8") as f:
                            self.design_md_content = f.read().strip()
                        self.design_md_mtime = mtime
                    if self.design_md_content:
                        prompt_parts.append(f"\n## Design & Frontend Guidelines (DESIGN.md)\n{self.design_md_content}")
                except Exception:
                    pass
        else:
            self.design_md_content = ""
            self.design_md_mtime = 0.0
        
        # Memory & Source of Truth Constraints
        prompt_parts.append(
            "\n## Memory & Source of Truth Constraints\n"
            "- You have access to a SQLite FTS5 search index via the `search_memory` tool. This index contains historical logs "
            "(thoughts, tool outputs, task objectives, and handover checkpoints) from past runs.\n"
            "- **CRITICAL**: Memory logs are historical. Code files change. Always treat the physical workspace files "
            "as the ultimate source of truth. If a memory log describes a file or function signature that contradicts the "
            "contents of the file as read by `read_file` or `get_outline`, the current file content is correct. Use memory as a guide, not a final truth."
        )
        
        # 1. Rules & Constraints
        if self.active_rules:
            prompt_parts.append("\n## Active Rules & Instructions Constraints")
            for rule_name in sorted(self.active_rules):
                rule_content = self.rules_cache[rule_name]
                prompt_parts.append(f"### Rule: {rule_name}\n{rule_content}")
                
        # Available MCP Servers (Configuration metadata only)
        if hasattr(self, "mcp_manager") and self.mcp_manager:
            try:
                self.mcp_manager.check_and_update_cache()
                available_mcp = self.mcp_manager.get_available_mcp_servers()
                if available_mcp:
                    prompt_parts.append("\n## Available Model Context Protocol (MCP) Servers")
                    prompt_parts.append(
                        "You have access to the following MCP servers. Only their configurations are cached. "
                        "To load a server and list its available tools, you MUST call the `load_mcp(server_name)` tool. "
                        "To expose a tool to your active tools schema, call `load_mcp_tool(server_name, tool_name)`. "
                        "Once done, call `unload_mcp(server_name)` to free context space."
                    )
                    for server_name, details in sorted(available_mcp.items()):
                        config = details.get("config", {})
                        servers = config.get("mcpServers", {})
                        desc = f"MCP server '{server_name}'"
                        if server_name in servers:
                            cmd = servers[server_name].get("command", "")
                            args = servers[server_name].get("args", [])
                            desc += f" (command: {cmd} {' '.join(str(a) for a in args)})"
                        prompt_parts.append(f"- **{server_name}**: {desc}")
            except Exception:
                pass

        # 2. Available Skills (Metadata only)
        if self.skills_cache:
            prompt_parts.append("\n## Available Skills")
            prompt_parts.append(
                "You have access to specialized skills. Only their metadata is currently loaded. "
                "To load the detailed guidelines for a skill, you MUST call the `load_skill(name)` tool. "
                "Once you no longer need the skill's guidelines, call the `unload_skill(name)` tool to free context space."
            )
            for name, data in sorted(self.skills_cache.items()):
                meta = data["metadata"]
                desc = meta.get("description", "No description available.")
                kws = meta.get("keywords", [])
                prompt_parts.append(f"- **{name}**: {desc} (Keywords: {kws})")
                
        # 3. Active Skills (Detailed Body)
        if self.active_skills:
            prompt_parts.append("\n## Active Skills Detailed Guidelines")
            for skill_name in sorted(self.active_skills):
                skill_data = self.skills_cache[skill_name]
                prompt_parts.append(f"### Skill Guideline: {skill_name}\n{skill_data['body']}")
                
        return "\n".join(prompt_parts)
