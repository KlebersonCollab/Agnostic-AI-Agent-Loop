# Knowledge Base

This directory stores project-specific patterns and anti-patterns discovered during development.

## Structure

- `patterns/` — Good practices to follow in this project
- `anti-patterns/` — Bad practices to avoid in this project

## Format

Each entry is a markdown file with:

- **Title**: Short descriptive name
- **Category**: architecture | code | testing | security | performance | devops
- **Description**: What it is
- **Example**: Code showing correct/incorrect usage
- **When to Use**: Applicable situations
- **When NOT to Use**: Exceptions
- **Tags**: For searchability

## How to Add

After discovering a pattern or anti-pattern during development:

1. Determine type (pattern or anti-pattern)
2. Create file: `.specs/knowledge/{type}s/{slug}.md`
3. Fill all sections with concrete examples
4. Reference it in relevant code reviews

---

*Entries are created as the project evolves — not pre-populated.*
