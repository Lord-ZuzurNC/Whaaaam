# 3M-MinecracftModpackMatrix Constitution
<!-- Example: Spec Constitution, TaskFlow Constitution, etc. -->

## Core Principles

### I. Clean Code
<!-- Example: I. Library-First -->
Code must be clean, readable, and maintainable; Follow PEP 8 guidelines; Use meaningful variable and function names.
<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented; Clear purpose required - no organizational-only libraries -->

### II. Simple UX
<!-- Example: II. CLI Interface -->
User interfaces must be simple, intuitive, and easy to navigate; Follow accessibility guidelines; Ensure a consistent user experience across all platforms.
<!-- Example: Every library exposes functionality via CLI; Text in/out protocol: stdin/args → stdout, errors → stderr; Support JSON + human-readable formats -->

### III. Responsive Design
<!-- Example: III. Test-First (NON-NEGOTIABLE) -->
Designs must be responsive and adapt to different screen sizes and devices; Use media queries and flexible layouts; Ensure optimal performance on all platforms.
<!-- Example: TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced -->

### IV. Minimal Dependencies
<!-- Example: IV. Integration Testing -->
Use minimal free and open-source dependencies; Avoid proprietary software; Ensure all dependencies are well-maintained and secure.
<!-- Example: Focus areas requiring integration tests: New library contract tests, Contract changes, Inter-service communication, Shared schemas -->

### V. Testing and Security
<!-- Example: V. Observability, VI. Versioning & Breaking Changes, VII. Simplicity -->
Use flake8 for linting and pytest for testing; Ensure all code is thoroughly tested; Follow security best practices to protect against vulnerabilities.
<!-- Example: Text I/O ensures debuggability; Structured logging required; Or: MAJOR.MINOR.BUILD format; Or: Start simple, YAGNI principles -->

## Additional Constraints
<!-- Example: Additional Constraints, Security Requirements, Performance Standards, etc. -->

- The project must use Python 3.10
- Use Flask and Flask-CORS for backend development
- Use JavaScript for frontend development
- Use Next.js for server-side rendering and static site generation
- Use Tailwind CSS for styling
- Dependencies must be listed in the package.json file
<!-- Example: Technology stack requirements, compliance standards, deployment policies, etc. -->

## Development Workflow
<!-- Example: Development Workflow, Review Process, Quality Gates, etc. -->

- Follow the Git workflow for version control
- Use pull requests for code reviews and collaboration
- Ensure all changes are tested before merging
- Maintain a clean and organized codebase
<!-- Example: Code review requirements, testing gates, deployment approval process, etc. -->

## Governance
<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

- Amendments require documentation, approval, and a migration plan
- Constitution supersedes all other practices
- Use AGENTS.md for runtime development guidance
<!-- Example: All PRs/reviews must verify compliance; Complexity must be justified; Use [GUIDANCE_FILE] for runtime development guidance -->

**Version**: 1.0.0 | **Ratified**: 2025-11-28 | **Last Amended**: 2025-11-28
<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->
