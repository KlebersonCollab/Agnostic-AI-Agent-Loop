import os
import pytest
from memory import AgentMemory

TEST_DB_PATH = "temp_test_memory.db"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Ensure cleanup before test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    yield
    
    # Cleanup after test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_memory_creation_and_search():
    memory = AgentMemory(db_path=TEST_DB_PATH)
    
    # Create session
    session_id = "test_sess_123"
    memory.create_session(session_id, "Find and fix authentication bugs in the API")
    
    # Add episodes
    memory.add_episode(session_id, 1, "assistant", "I am thinking about authentication methods", None)
    memory.add_episode(session_id, 2, "tool", "Error: Token invalid at route /auth/login", None)
    memory.add_episode(session_id, 3, "assistant", "Ah, the login route has an auth issue.", None)
    
    # Update results
    memory.update_session_results(session_id, final_summary="Fixed login endpoint by changing token header check.")
    
    # Test FTS Search 1: Match keyword 'authentication'
    results = memory.search("authentication")
    assert len(results) >= 2 # Should match task objective and first thought
    categories = [r["category"] for r in results]
    assert "task" in categories
    assert "thought" in categories
    
    # Test FTS Search 2: Filter by category 'tool_output'
    tool_results = memory.search("login", category="tool_output")
    assert len(tool_results) == 1
    assert tool_results[0]["category"] == "tool_output"
    assert "Token invalid" in tool_results[0]["content"]
    
    # Test FTS Search 3: Match final summary
    summary_results = memory.search("endpoint", category="summary")
    assert len(summary_results) == 1
    assert "Fixed login endpoint" in summary_results[0]["content"]
    
    # Test FTS Search 4: No match
    empty_results = memory.search("non_existent_pattern_12345")
    assert len(empty_results) == 0
    
    memory.close()
