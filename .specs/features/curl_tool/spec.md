# SDD Specification: curl_tool

This is the source of truth for functional requirements and business logic of the `curl` tool.

---

## 1. Context & Goals
- **Problem Statement**: The agent needs a way to make HTTP requests (similar to the system `curl` command) to interact with external web APIs, fetch web page content, or trigger webhooks.
- **Scope**: 
  - Support GET, POST, PUT, DELETE, PATCH, and other standard HTTP methods.
  - Support passing custom HTTP headers.
  - Support sending request body data (payload).
  - Support disabling SSL verification (similar to curl's `-k`/`--insecure` flag).
  - Support custom timeouts.
  - Support response body truncation via `max_response_chars` to prevent context length bloat.
  - Handle connection timeouts, status code errors, and invalid URLs gracefully.
  - Out of scope: A full command-line parser of all curl arguments (e.g., `-X`, `-H`, `-d`). Instead, we will provide a clean, structured programmatic interface conforming to the agent's tool standard.
- **Success Criteria**:
  - A tool named `curl` is registered in `tools/__init__.py`.
  - The tool can successfully perform HTTP requests using Python's standard library.
  - The tool returns the response details (status code, headers, and body) in a readable string format.
  - Extensive unit tests verify the correctness of the tool including error handling.

## 2. Requirements (BDD Scenarios)

### Feature: Curl HTTP Request Tool

**Scenario 1: Perform a successful GET request**
- **Given** a valid URL `https://httpbin.org/get`
- **When** the `curl` tool is invoked with `url="https://httpbin.org/get"`, `method="GET"`
- **Then** the request is made, and a string containing the status code `200`, the response headers, and the response body is returned.

**Scenario 2: Perform a successful POST request with headers and data**
- **Given** a valid URL `https://httpbin.org/post`
- **When** the `curl` tool is invoked with `url="https://httpbin.org/post"`, `method="POST"`, `headers={"Content-Type": "application/json"}`, and `data='{"key": "value"}'`
- **Then** the request is made with the specified headers and body, and the response details are returned.

**Scenario 3: Handle request timeout or connection errors**
- **Given** an invalid or unreachable URL or a host that times out
- **When** the `curl` tool is invoked
- **Then** the tool catches the exception and returns a descriptive error message instead of crashing.

**Scenario 4: Truncate large response body**
- **Given** a URL returning a large response body (e.g., 100,000 characters)
- **When** the `curl` tool is invoked with `max_response_chars=100`
- **Then** the returned response body is truncated to 100 characters and ends with a truncation notice.


## 3. Constraints & Risks
- **Security**: Prevent fetching local or internal resources if requested (though this agent runs locally, standard HTTP client rules apply). No sensitive files or credentials should be leaked.
- **Dependencies**: Use Python's built-in `urllib` package to avoid introducing external dependencies.
- **Performance**: Enforce a default timeout (e.g., 10 seconds) to prevent the agent from hanging indefinitely.

---

## 4. Status
- **AGREE**
