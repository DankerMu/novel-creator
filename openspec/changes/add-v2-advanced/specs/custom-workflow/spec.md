## ADDED Requirements

### Requirement: User-Defined Workflow DSL
The system SHALL allow users to define custom workflows using a Python DSL executed in a RestrictedPython sandbox with AST whitelist validation.

#### Scenario: Execute user-defined workflow safely
- **WHEN** user submits a Python DSL script that attempts `import os`
- **THEN** the sandbox blocks the import and returns a security error
