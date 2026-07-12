import urllib.request
import urllib.error
import ssl
from typing import Optional, Dict

def curl(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    verify_ssl: bool = True,
    timeout: int = 15,
    max_response_chars: int = 50000
) -> str:
    """Makes an HTTP request mimicking curl.

    Args:
        url: Target HTTP/HTTPS URL.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.).
        headers: Optional dictionary of HTTP headers.
        data: Optional request payload/body string.
        verify_ssl: If False, disables SSL certificate verification.
        timeout: Request timeout in seconds.
        max_response_chars: Maximum characters to return in response body.

    Returns:
        A formatted string containing status, headers, and response body, or an error.
    """
    if not (url.startswith("http://") or url.startswith("https://")):
        return "Error: Invalid URL. It must start with http:// or https://"

    try:
        # Prepare request headers
        req_headers = {}
        if headers:
            req_headers.update(headers)

        # Default User-Agent to mimic a browser/curl client if not specified
        if "User-Agent" not in req_headers:
            req_headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 agnostic-agent/curl-tool"

        # Handle request data payload
        req_data = None
        if data is not None:
            req_data = data.encode("utf-8")

        # Create Request object
        req = urllib.request.Request(
            url=url,
            data=req_data,
            headers=req_headers,
            method=method.upper()
        )

        # Configure SSL context
        context = None
        if not verify_ssl:
            context = ssl._create_unverified_context()

        # Execute request
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            status_code = response.status
            reason = response.reason
            resp_headers = response.info()
            resp_body = response.read().decode("utf-8", errors="replace")

        # Format response headers
        headers_str = "\n".join(f"  {k}: {v}" for k, v in resp_headers.items())

        # Truncate response body if it exceeds limit
        if len(resp_body) > max_response_chars:
            resp_body = resp_body[:max_response_chars] + f"\n...[Response body truncated to {max_response_chars} characters to prevent context bloating]..."

        return (
            f"Status: {status_code} {reason}\n"
            f"Headers:\n{headers_str}\n\n"
            f"Body:\n{resp_body}"
        )
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
            if len(body) > max_response_chars:
                body = body[:max_response_chars] + f"\n...[Response body truncated to {max_response_chars} characters to prevent context bloating]..."
        except Exception:
            body = "<Could not read error response body>"

        headers_str = "\n".join(f"  {k}: {v}" for k, v in e.headers.items()) if hasattr(e, "headers") else ""
        return (
            f"Status: {e.code} {e.reason}\n"
            f"Headers:\n{headers_str}\n\n"
            f"Body:\n{body}"
        )
    except urllib.error.URLError as e:
        return f"Error: URL Error: {e.reason}"
    except Exception as e:
        return f"Error: {str(e)}"
