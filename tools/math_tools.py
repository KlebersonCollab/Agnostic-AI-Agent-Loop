def calculate(expression: str) -> str:
    """Evaluates a basic math expression safely."""
    allowed_chars = "0123456789+-*/(). "
    if not all(c in allowed_chars for c in expression):
        return "Error: Invalid characters. Only numbers and basic math operators are allowed."
    try:
        # Safe evaluation
        result = eval(expression, {"__builtins__": None})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {e}"
