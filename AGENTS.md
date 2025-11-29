# AGENTS.md

## Build/lint/test commands

- **Build**: `python setup.py build`
- **Lint**: `flake8 .`
- **Test**: `pytest tests/` (to run all tests)
  - To run a single test: `pytest tests/<test_file>.py::<TestClass>::<test_method>`

## Code Style Guidelines

1. **Imports**:
   - Import standard library modules first.
   - Followed by third-party libraries.
   - Local application imports last.

2. **Formatting**:
   - Use black for code formatting: `black .`
   - Line length should not exceed 80 characters.

3. **Types**:
   - Use type hints where appropriate.
   - Ensure all functions and variables have clear types.

4. **Naming Conventions**:
   - Use snake_case for variable and function names.
   - Use PascalCase for class names.
   - Constants should be in ALL_CAPS.

5. **Error Handling**:
   - Handle exceptions using try-except blocks.
   - Log errors appropriately using the logging module.
   - Avoid catching general exceptions unless absolutely necessary.

## Additional Guidelines

- Follow Cursor rules if they exist in `.cursor/rules/` or `.cursorrules`.
- Follow Copilot rules if they exist in `.github/copilot-instructions.md`.
