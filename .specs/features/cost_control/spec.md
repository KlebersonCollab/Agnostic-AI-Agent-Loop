# SDD Specification: Cost Control (post_api_request hook)

This specification defines the functional requirements and BDD scenarios for implementing a cost control hook on `post_api_request`.

---

## 1. Context & Goals
- **Problem Statement**: Running LLM agents can be expensive. Without tracking, a buggy loop or massive context window can quickly drain API credits. We need a way to track token usage (input/output/total) and latency per API call, maintain a ledger for the active session, and trigger clear alerts when session spending exceeds safe limits.
- **Scope**:
  - Extend `ChatMessage` to support a `response_metadata` dictionary containing token usage, model name, and latency.
  - Implement token usage extraction and latency measurement in the active LLM providers (`openai`, `gemini`, `anthropic`).
  - Create a hook file `cost_control.py` under `.agents/hooks/post_api_request/`.
  - The hook must maintain a cumulative ledger (total tokens and estimated USD cost) across the active session.
  - The hook must support configurable limits via environment variables: `SESSION_COST_LIMIT` (in USD) and `SESSION_TOKEN_LIMIT`.
  - Present a warning when the cumulative session cost or token count exceeds the limits.
- **Success Criteria**:
  - Token counts and latency are successfully measured and stored in the response.
  - The cost control hook aggregates these metrics correctly.
  - When limits are exceeded, a visible warning alert is printed to the console.
  - Tests verify that token aggregation, pricing mapping, and warning conditions behave correctly.

## 2. Requirements (BDD Scenarios)

### Feature: Session Cost and Token Limit Monitoring

**Scenario 1: Provider response populates metadata**
- **Given** a configured LLM provider (`openai`, `gemini`, or `anthropic`)
- **When** an API call is made and returns successfully
- **Then** the returned `ChatMessage` has `response_metadata` containing:
  - `prompt_tokens` (integer)
  - `completion_tokens` (integer)
  - `total_tokens` (integer)
  - `latency` (float, in seconds)
  - `model_name` (string)

**Scenario 2: Cost hook accumulates usage**
- **Given** the `cost_control` hook is registered in `post_api_request`
- **When** multiple API requests are made during a session
- **Then** the hook maintains a cumulative count of prompt tokens, completion tokens, latency, and estimated cost in USD.

**Scenario 3: Alert when cost limit is exceeded**
- **Given** `SESSION_COST_LIMIT` is set to `0.10` USD
- **When** the cumulative estimated cost exceeds `0.10` USD
- **Then** the hook prints a prominent warning alert to the console indicating that the session cost limit has been exceeded.

**Scenario 4: Alert when token limit is exceeded**
- **Given** `SESSION_TOKEN_LIMIT` is set to `5000`
- **When** the cumulative token count exceeds `5000`
- **Then** the hook prints a prominent warning alert to the console indicating that the session token limit has been exceeded.

## 3. Constraints & Risks
- **Performance**: The cost tracking overhead must be negligible (microseconds) and not block the execution flow.
- **Robustness**: If a model is not recognized in the pricing dictionary, it should fallback to a safe default pricing (e.g. `$0.00000015` per prompt token and `$0.00000060` per completion token, equivalent to gpt-4o-mini) and output a warning/info log, but NOT crash the agent.
- **Security**: No credentials or private information should be logged.

---

## 4. Status
- **AGREE** - Agree with the specification plan
