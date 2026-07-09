import os
from tools.io_tools import read_file, write_file, list_project_files

def test_write_and_read_file():
    test_file = "test_io_temp.txt"
    test_content = "Hello, SOLID ReAct Agent World!"
    
    try:
        # Test writing
        write_result = write_file(test_file, test_content)
        assert "success" in write_result.lower()
        assert os.path.exists(test_file)
        
        # Test reading
        read_result = read_file(test_file)
        assert read_result == test_content
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)

def test_read_non_existent_file():
    result = read_file("non_existent_file_987654.txt")
    assert "does not exist" in result

def test_security_access_denied():
    # Attempting to read a file outside the workspace
    result = read_file("../outside_workspace.txt")
    assert "access denied" in result.lower()
    
    result_write = write_file("../outside_workspace.txt", "data")
    assert "access denied" in result_write.lower()

def test_list_project_files():
    # Should list some python files in the workspace
    files_list = list_project_files()
    assert "main.py" in files_list
    assert "agent.py" in files_list
    assert "[FILE] tools/math_tools.py" in files_list or "tools/math_tools.py" in files_list
