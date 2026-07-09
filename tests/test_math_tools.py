from tools.math_tools import calculate

def test_calculate_basic_addition():
    assert calculate("2 + 2") == "4"

def test_calculate_multiplication_with_parentheses():
    assert calculate("3 * (4 + 5)") == "27"

def test_calculate_division():
    assert calculate("10 / 2") == "5.0"

def test_calculate_invalid_characters():
    result = calculate("2 + 2; import os; os.system('ls')")
    assert "Error: Invalid characters" in result

def test_calculate_syntax_error():
    result = calculate("3 * (4 +")
    assert "Error evaluating expression" in result
