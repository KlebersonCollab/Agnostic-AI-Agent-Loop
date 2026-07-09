import os
from typing import Dict, Any, List, Set

class ContextBuilder:
    """
    Registry and compiler for agent system prompts, constraints (rules), and guidelines (skills).
    Parses frontmatter metadata on startup to enable dynamic loading/unloading of detailed contents.
    """
    def __init__(self, base_system_prompt: str, skills_dir: str = ".agents/skills", rules_dir: str = ".agents/rules"):
        self.base_system_prompt = base_system_prompt
        self.skills_dir = skills_dir
        self.rules_dir = rules_dir
        
        # Cache structures:
        # name -> {"metadata": dict, "body": str}
        self.skills_cache: Dict[str, Dict[str, Any]] = {}
        # filename -> content
        self.rules_cache: Dict[str, str] = {}
        
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
        """Discovers and caches all SKILL.md files under the skills directory."""
        if not os.path.exists(self.skills_dir):
            return
        
        for item in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(skill_path):
                skill_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_file):
                    try:
                        with open(skill_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        metadata, body = self._parse_frontmatter(content)
                        name = metadata.get("name", item)
                        self.skills_cache[name] = {
                            "metadata": metadata,
                            "body": body
                        }
                    except Exception:
                        # Silently skip malformed skills to ensure robust startup
                        pass

    def load_all_rules(self):
        """Discovers and caches all markdown files under the rules directory."""
        if not os.path.exists(self.rules_dir):
            return
        
        for item in os.listdir(self.rules_dir):
            if item.endswith(".md"):
                rule_path = os.path.join(self.rules_dir, item)
                try:
                    with open(rule_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    rule_name = os.path.splitext(item)[0]
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

    def build_prompt(self) -> str:
        """Compiles the dynamic system prompt with active rules, skills metadata, and active skills details."""
        prompt_parts = [self.base_system_prompt.strip()]
        
        # 1. Rules & Constraints
        if self.active_rules:
            prompt_parts.append("\n## Active Rules & Instructions Constraints")
            for rule_name in sorted(self.active_rules):
                rule_content = self.rules_cache[rule_name]
                prompt_parts.append(f"### Rule: {rule_name}\n{rule_content}")
                
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
