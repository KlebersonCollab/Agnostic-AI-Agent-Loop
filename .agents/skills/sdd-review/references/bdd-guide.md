# BDD Guide: Writing Effective Scenarios

Behavior-Driven Development (BDD) focuses on the behavior of the software from the perspective of the user. Effective scenarios provide clarity, documentation, and a basis for automated testing.

## The Gherkin Syntax: Given / When / Then

Scenarios follow a structured format to ensure they are readable by both technical and non-technical stakeholders.

### 1. GIVEN (The Context)
Describes the initial state of the system before the action occurs.
- **Rule**: Avoid technical implementation details (e.g., "Given the user is in the database").
- **Good Example**: "Given a user with a premium subscription is logged in."

### 2. WHEN (The Action)
Describes the specific event or action performed by the user or triggered by a system event.
- **Rule**: Focus on the primary action being tested.
- **Good Example**: "When the user attempts to download a high-resolution video."

### 3. THEN (The Outcome)
Describes the expected result or change in state after the action.
- **Rule**: State what is observable to the user or external systems.
- **Good Example**: "Then the download should begin immediately without advertisements."

## Best Practices for AI Agents

1. **One Scenario, One Behavior**: Each scenario should test a single, atomic behavior to simplify debugging and validation.
2. **Ubiquitous Language**: Use the same terms used by business stakeholders and in the codebase.
3. **Avoid UI Details**: Don't say "When the user clicks the blue button at the bottom-right". Say "When the user confirms the purchase".
4. **Declarative, not Imperative**: Describe *what* the user does, not *how* they do it.

## Example Scenario

**Feature**: User Authentication

**Scenario**: Successful login with valid credentials
- **Given** a registered user exists with email "user@example.com"
- **And** the user is on the login page
- **When** the user submits valid credentials
- **Then** the user should be redirected to the dashboard
- **And** a welcome notification should be displayed

## Integration with SDD
- Include BDD scenarios in your `spec.md` for Medium+ complexity tasks.
- Use these scenarios to drive your test implementation and validation report.

---
