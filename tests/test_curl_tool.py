from unittest.mock import patch, MagicMock
import urllib.error
from tools.web_tools import curl

def test_curl_invalid_url():
    result = curl("ftp://example.com")
    assert "Error: Invalid URL" in result

@patch("urllib.request.urlopen")
def test_curl_get_success(mock_urlopen):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.reason = "OK"
    mock_response.info.return_value = {"Content-Type": "text/html"}
    mock_response.read.return_value = b"Hello, world!"
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = curl("https://example.com/test", method="GET")

    assert "Status: 200 OK" in result
    assert "Content-Type: text/html" in result
    assert "Hello, world!" in result

    # Check urlopen call
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert req.full_url == "https://example.com/test"
    assert req.method == "GET"

@patch("urllib.request.urlopen")
def test_curl_post_success(mock_urlopen):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.reason = "Created"
    mock_response.info.return_value = {"Content-Type": "application/json"}
    mock_response.read.return_value = b'{"success": true}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = curl(
        "https://example.com/api",
        method="POST",
        headers={"Authorization": "Bearer token123"},
        data='{"foo": "bar"}'
    )

    assert "Status: 201 Created" in result
    assert "Content-Type: application/json" in result
    assert '{"success": true}' in result

    # Check urlopen call
    args, kwargs = mock_urlopen.call_args
    req = args[0]
    assert req.full_url == "https://example.com/api"
    assert req.method == "POST"
    assert req.get_header("Authorization") == "Bearer token123"
    assert req.data == b'{"foo": "bar"}'

@patch("urllib.request.urlopen")
def test_curl_http_error(mock_urlopen):
    # Setup HTTPError mock
    mock_fp = MagicMock()
    mock_fp.read.return_value = b"Access Denied"

    headers = {"Content-Type": "text/plain"}
    # HTTPError signature: url, code, msg, hdrs, fp
    http_error = urllib.error.HTTPError(
        "https://example.com/403", 403, "Forbidden", headers, mock_fp
    )

    mock_urlopen.side_effect = http_error

    result = curl("https://example.com/403")

    assert "Status: 403 Forbidden" in result
    assert "Content-Type: text/plain" in result
    assert "Access Denied" in result

@patch("urllib.request.urlopen")
def test_curl_url_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

    result = curl("https://nonexistent.example.com")

    assert "Error: URL Error: Connection refused" in result

@patch("urllib.request.urlopen")
def test_curl_generic_exception(mock_urlopen):
    mock_urlopen.side_effect = Exception("Something went wrong")

    result = curl("https://example.com")

    assert "Error: Something went wrong" in result


@patch("urllib.request.urlopen")
def test_curl_truncation_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.reason = "OK"
    mock_response.info.return_value = {"Content-Type": "text/html"}
    mock_response.read.return_value = b"A" * 1000
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = curl("https://example.com/large", max_response_chars=100)

    assert "Status: 200 OK" in result
    # Body should have exactly 100 'A's + notice
    assert "A" * 100 in result
    assert "A" * 101 not in result
    assert "...[Response body truncated to 100 characters to prevent context bloating]..." in result


@patch("urllib.request.urlopen")
def test_curl_truncation_error(mock_urlopen):
    mock_fp = MagicMock()
    mock_fp.read.return_value = b"E" * 1000

    headers = {"Content-Type": "text/plain"}
    http_error = urllib.error.HTTPError(
        "https://example.com/error-large", 500, "Internal Server Error", headers, mock_fp
    )
    mock_urlopen.side_effect = http_error

    result = curl("https://example.com/error-large", max_response_chars=50)

    assert "Status: 500 Internal Server Error" in result
    assert "E" * 50 in result
    assert "E" * 51 not in result
    assert "...[Response body truncated to 50 characters to prevent context bloating]..." in result

