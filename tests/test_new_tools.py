import os
from tools.io_tools import search_grep, patch_file, write_file, read_file, get_outline

def test_search_grep():
    test_file = "test_search_temp.txt"
    content = "This is a line containing SearchPatternXYZ\nAnd another normal line\n"
    
    try:
        write_file(test_file, content)
        
        # Test finding match
        result = search_grep("SearchPatternXYZ")
        assert test_file in result
        assert "1:" in result
        assert "SearchPatternXYZ" in result
        
        # Test case-insensitive
        result_lower = search_grep("searchpatternxyz")
        assert test_file in result_lower
        
        # Construct query dynamically to avoid self-matching this test source file
        query = "non-existent-" + "pattern-12345"
        result_not_found = search_grep(query)
        assert "No matches found" in result_not_found
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_patch_file():
    test_file = "test_patch_temp.txt"
    content = "Header\nTargetLineToReplace\nFooter\n"
    
    try:
        write_file(test_file, content)
        
        # Test successful patch
        patch_result = patch_file(test_file, "TargetLineToReplace", "ReplacedLine")
        assert "success" in patch_result.lower()
        
        # Test file content after patch
        new_content = read_file(test_file)
        assert new_content == "Header\nReplacedLine\nFooter\n"
        
        # Test patch target not found error
        fail_result = patch_file(test_file, "NonExistentLine", "Something")
        assert "error" in fail_result.lower()
        assert "not found" in fail_result.lower()
        
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_patch_file_duplicate_target():
    test_file = "test_patch_dup_temp.txt"
    content = "TargetLine\nBody\nTargetLine\n"
    
    try:
        write_file(test_file, content)
        
        # Test error when target occurs multiple times
        dup_result = patch_file(test_file, "TargetLine", "NewValue")
        assert "error" in dup_result.lower()
        assert "found 2 times" in dup_result.lower()
        
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_get_outline():
    test_file = "test_outline_temp.py"
    content = """import os
from sys import argv

class MyClass:
    \"\"\"This is MyClass docstring\"\"\"
    def my_method(self, arg1):
        \"\"\"Method docstring\"\"\"
        pass

def my_function(param1, param2):
    \"\"\"Function docstring\"\"\"
    return True
"""
    try:
        write_file(test_file, content)
        
        result = get_outline(test_file)
        
        assert "Structure outline for 'test_outline_temp.py':" in result
        assert "[IMPORT] import os" in result
        assert "[IMPORT] from sys import argv" in result
        assert "[CLASS] class MyClass - \"This is MyClass docstring\"" in result
        assert "[METHOD] def my_method(self, arg1) - \"Method docstring\"" in result
        assert "[FUNCTION] def my_function(param1, param2) - \"Function docstring\"" in result
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_tools_registry_mismatch():
    import pytest
    from providers import ToolDefinition
    
    # Test the duplicate name validation logic
    def check_duplicates(metadata):
        tool_names = [t.name for t in metadata]
        if len(tool_names) != len(set(tool_names)):
            duplicates = {x for x in tool_names if tool_names.count(x) > 1}
            raise ImportError(f"Duplicate tool registration detected for: {duplicates}")
            
    # Should raise ImportError on duplicate name
    with pytest.raises(ImportError) as excinfo:
        check_duplicates([
            ToolDefinition(name="calculate", description="..."),
            ToolDefinition(name="calculate", description="...")
        ])
    assert "Duplicate tool registration" in str(excinfo.value)

