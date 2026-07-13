import os
import sys
import importlib.util
from typing import List, Dict, Any, Tuple, Callable

class HooksManager:
    def __init__(self, hooks_dir: str = None):
        self.hooks_dirs: List[str] = []
        if hooks_dir is not None:
            self.hooks_dirs.append(hooks_dir)
        else:
            # Package root directory (where hooks/manager.py is located)
            package_root = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(package_root)
            builtin_hooks = os.path.join(project_root, ".agents", "hooks")
            if os.path.exists(builtin_hooks):
                self.hooks_dirs.append(builtin_hooks)
            
            # Current working directory hooks directory
            cwd_hooks = os.path.join(os.getcwd(), ".agents", "hooks")
            if os.path.abspath(cwd_hooks) not in [os.path.abspath(d) for d in self.hooks_dirs]:
                self.hooks_dirs.append(cwd_hooks)

        self.hooks: Dict[str, List[Callable]] = {
            "on_session_start": [],
            "on_session_complete": [],
            "on_session_clear": [],
            "pre_step": [],
            "post_step": [],
            "pre_tool_call": [],
            "post_tool_call": [],
            "on_tool_error": [],
            "pre_api_request": [],
            "post_api_request": [],
            "on_error": []
        }
        self.load_hooks()

    def load_hooks(self):
        temp_hooks = {event: {} for event in self.hooks.keys()}
        
        for h_dir in self.hooks_dirs:
            if not os.path.exists(h_dir):
                # Auto-create local CWD hooks directory if missing
                if h_dir == os.path.join(os.getcwd(), ".agents", "hooks"):
                    try:
                        os.makedirs(h_dir, exist_ok=True)
                    except Exception:
                        pass
                continue

            for event in self.hooks.keys():
                event_dir = os.path.join(h_dir, event)
                if not os.path.exists(event_dir):
                    if h_dir == os.path.join(os.getcwd(), ".agents", "hooks"):
                        try:
                            os.makedirs(event_dir, exist_ok=True)
                        except Exception:
                            pass
                    continue

                for file in sorted(os.listdir(event_dir)):
                    if file.endswith(".py") and not file.startswith("_"):
                        file_path = os.path.join(event_dir, file)
                        module_name = f"hooks.{event}.{file[:-3]}"
                        try:
                            spec = importlib.util.spec_from_file_location(module_name, file_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                if hasattr(module, "handler"):
                                    # Workspace hooks will overwrite built-in hooks if they share the same filename
                                    temp_hooks[event][file] = module.handler
                        except Exception as e:
                            print(f"Error loading hook {file_path}: {e}", file=sys.stderr)
                            
        # Populate final self.hooks preserving alphabetical file order
        for event in self.hooks.keys():
            sorted_files = sorted(temp_hooks[event].keys())
            for file in sorted_files:
                self.hooks[event].append(temp_hooks[event][file])

    # Trigger Methods
    def trigger_on_session_start(self, agent):
        for h in self.hooks["on_session_start"]:
            try:
                h(agent)
            except Exception as e:
                print(f"Error in on_session_start hook: {e}", file=sys.stderr)

    def trigger_on_session_complete(self, agent):
        for h in self.hooks["on_session_complete"]:
            try:
                h(agent)
            except Exception as e:
                print(f"Error in on_session_complete hook: {e}", file=sys.stderr)

    def trigger_on_session_clear(self, agent):
        for h in self.hooks["on_session_clear"]:
            try:
                h(agent)
            except Exception as e:
                print(f"Error in on_session_clear hook: {e}", file=sys.stderr)

    def trigger_pre_step(self, agent, step: int):
        for h in self.hooks["pre_step"]:
            try:
                h(agent, step)
            except Exception as e:
                print(f"Error in pre_step hook: {e}", file=sys.stderr)

    def trigger_post_step(self, agent, step: int):
        for h in self.hooks["post_step"]:
            try:
                h(agent, step)
            except Exception as e:
                print(f"Error in post_step hook: {e}", file=sys.stderr)

    def trigger_pre_tool_call(self, name: str, arguments: dict) -> Tuple[str, dict]:
        for h in self.hooks["pre_tool_call"]:
            try:
                res = h(name, arguments)
                if res:
                    name, arguments = res
            except Exception as e:
                print(f"Error in pre_tool_call hook: {e}", file=sys.stderr)
        return name, arguments

    def trigger_post_tool_call(self, name: str, arguments: dict, result: str) -> str:
        for h in self.hooks["post_tool_call"]:
            try:
                res = h(name, arguments, result)
                if res is not None:
                    result = res
            except Exception as e:
                print(f"Error in post_tool_call hook: {e}", file=sys.stderr)
        return result

    def trigger_on_tool_error(self, name: str, arguments: dict, exception: Exception) -> str:
        result = None
        for h in self.hooks["on_tool_error"]:
            try:
                res = h(name, arguments, exception)
                if res is not None:
                    result = res
            except Exception as e:
                print(f"Error in on_tool_error hook: {e}", file=sys.stderr)
        return result

    def trigger_pre_api_request(self, messages: list, tools: list) -> Tuple[list, list]:
        for h in self.hooks["pre_api_request"]:
            try:
                res = h(messages, tools)
                if res:
                    messages, tools = res
            except Exception as e:
                print(f"Error in pre_api_request hook: {e}", file=sys.stderr)
        return messages, tools

    def trigger_post_api_request(self, response_message):
        for h in self.hooks["post_api_request"]:
            try:
                res = h(response_message)
                if res is not None:
                    response_message = res
            except Exception as e:
                print(f"Error in post_api_request hook: {e}", file=sys.stderr)
        return response_message

    def trigger_on_error(self, agent, error_message: str):
        for h in self.hooks["on_error"]:
            try:
                h(agent, error_message)
            except Exception as e:
                print(f"Error in on_error hook: {e}", file=sys.stderr)
