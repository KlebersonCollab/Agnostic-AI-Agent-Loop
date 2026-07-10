from context.references import parse_context_references, ContextReference

def test_parse_simple_references():
    prompt = "Please look at @diff and @staged"
    refs = parse_context_references(prompt)
    assert len(refs) == 2
    assert refs[0].kind == "diff"
    assert refs[1].kind == "staged"

def test_parse_file_references():
    prompt = "Check @file:agent.py and @file:\"context/builder.py\":10-20"
    refs = parse_context_references(prompt)
    assert len(refs) == 2
    assert refs[0].kind == "file"
    assert refs[0].target == "agent.py"
    assert refs[0].line_start is None
    assert refs[0].line_end is None

    assert refs[1].kind == "file"
    assert refs[1].target == "context/builder.py"
    assert refs[1].line_start == 10
    assert refs[1].line_end == 20

def test_parse_url_references():
    prompt = "Analyze @url:https://example.com/status."
    refs = parse_context_references(prompt)
    assert len(refs) == 1
    assert refs[0].kind == "url"
    assert refs[0].target == "https://example.com/status"
