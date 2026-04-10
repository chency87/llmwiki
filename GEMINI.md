# llmwiki

@.agents/shared.md
@.agents/rules/avoid-these.md
@.agents/rules/compound-engineering.mdc

## Gemini CLI Notes

- Use `AGENTS.md` as the repository entrypoint for workflow and layout guidance.
- Treat `.agents/rules/compound-engineering.mdc` as the canonical definition of the compound engineering loop.
- Review `.agents/rules/patterns.md`, `.agents/rules/architecture.md`, and `.agents/rules/tools.md` when they are relevant to the task.
- For non-trivial work, check `.agents/learnings/` before planning and write plans under `.agents/plans/`.
- For bug fixes and behavior changes, prefer test-driven development: establish the failing test first, then implement the smallest passing change.

## Code Quality
1. Documentation: Keep user-facing docs aligned with `src/llmwiki/cli.py` and `src/llmwiki/utils/config.py`.
2. Tests: Cover behavior changes with targeted `pytest` tests.
3. Type Safety: Prefer explicit types and `pydantic` models for config and interfaces.

## Dependencies
1. Avoid unnecessary dependencies

## Common Issues to Flag
1. Unhandled errors or generic error messages
2. Missing input validation
3. Hardcoded credentials or secrets
4. Missing documentation updates for CLI/config/schema changes
5. Inadequate test coverage on critical paths
6. Performance issues (unnecessary repeated I/O or expensive loops)
7. Breaking CLI/config behavior without migration notes

## Anti-Patterns
1. Do not add speculative config/feature flags "just in case".
2. Do not mix massive formatting-only changes with functional changes.
3. Do not modify unrelated modules "while here".
4. Do not bypass failing checks without explicit explanation.
5. Do not hide behavior-changing side effects in refactor commits.
6. Do not include personal identity or sensitive information in test data, examples, docs, or commits.
