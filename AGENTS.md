# Kakumi App - Agent Guidelines

This file provides instructions for agentic coding agents working on the kakumi-app repository.

## Project Overview

Kakumi App is a web application for managing Karate-Do tournaments (Kata and Kumite) built entirely with **Reflex (Python)**. The application follows a "Pure Python" architecture where both the user interface and the server logic are defined using Python.

- **Framework**: Reflex
- **Backend & Frontend**: 100% Python
- **Database**: SQLite with SQLModel (and Alembic for migrations)
- **State Management**: Reflex State system

## Tech Stack Constraints (Strict)

1. **Python-First Policy**: All development, including UI components and logic, MUST be written in Python. Do not create or modify `.js`, `.ts`, `.jsx`, `.tsx`, `.html`, or `.css` files. Sub-agents must exhaust all possibilities within `rx.Component` and `rx.State` before even considering custom frontend code.
2. **UI Framework**: Use `reflex` components exclusively for building the frontend.
3. **ORM**: Use `sqlmodel` for all database interactions.
4. **Domain Logic**: All sports regulations and scoring logic (strictly adhering to WKF 2026 rules) must reside within Python methods in `rx.State` classes or dedicated Python helper modules.

## Development Commands

### Python Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application in development mode
reflex run

# Export for production
reflex export
```

### Backend (kakumi_app directory)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the application (from project root)
python -m kakumi_app.kakumi_app

# Run database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Run tests (pytest-style)
python -m pytest test_file.py -v

# Or run specific test function
python -c "from test_file import test_database_flow; test_database_flow()"
```

### Single Test Execution
To run a single test function:
```bash
# Direct execution
python -c "from test_file import test_function_name; test_function_name()"

# Using pytest with specific test
python -m pytest test_file.py::test_function_name -v
```

## Code Style Guidelines

### Python (Reflex Frontend & Backend)
- **Formatting**: Follow PEP 8 standards. Use Black (max 88 characters)
- **Imports**: Standard library first, then third-party, then local.
- **Types**: Use type hints for all function parameters and return values to improve AI assistance.
- **Naming**: 
  - Classes (Models, States, Components): PascalCase
  - Functions/variables: snake_case
  - Constants: UPPER_CASE
- **Components**: Define UIs as Python functions returning Reflex components (e.g., rx.vstack(...)).
- **Error Handling**: Use try/except blocks with specific exception types
- **Documentation**: Docstrings for all classes and functions using triple quotes.
- **Line Length**: Maximum 88 characters (Black default)

### SQL/Model Definitions
- **Naming**: snake_case for table names and columns
- **Inheritance**: Database tables must inherit from rx.Model (which integrates SQLModel).
- **Relationships**: Explicitly define foreign keys and relationships
- **Constraints**: Use appropriate field constraints (unique, index, nullable)
- **Documentation**: Comment complex relationships and business rules

## Architecture Patterns

### Reflex State Management
- State classes inherit from `rx.State`
- State variables defined as class attributes
- Event handlers are methods that modify state
- Use `@rx.var` for computed properties

### Data Flow
1. Backend models (SQLModel) define database schema
2. Reflex session manages database transactions
3. State variables hold UI data
4. Event handlers update state and trigger re-renders
5. Python functions return Reflex components that subscribe to state changes

## Testing Practices

### Backend Testing
- Use reflex's session context for database isolation
- Tests should be transactional or use test databases
- Follow pytest naming conventions (`test_*.py` or `test_*` functions)
- Mock external services when necessary
- Test both positive and negative cases

## Database Migrations

### Alembic Workflow
1. Modify models in `kakumi_app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Apply migration: `alembic upgrade head`
5. For data migrations, create empty revision and add custom SQL

### Best Practices
- Keep migrations small and focused
- Test migrations on copy of production data
- Include both upgrade and downgrade paths
- Document breaking changes in migration notes

## File Organization (Expected)

### Root Level
```
/
├── kakumi_app/          # Main application (100% Python)
│   ├── components/      # Reusable Reflex UI components
│   ├── models/          # SQLModel database models
│   ├── pages/           # Page components (routes)
│   ├── styles/          # Styling configurations (Python dicts/constants)
│   ├── __init__.py
│   ├── kakumi_app.py    # App entry point
│   ├── states.py        # Global state management
│   └── __pycache__/
├── .web/                # Auto-generated by Reflex (DO NOT EDIT)
├── alembic/             # Database migrations
├── docs/                # Documentation (WKF 2026 regulations, PDFs)
├── assets/              # Static assets (images, fonts)
├── requirements.txt     # Python dependencies
├── rxconfig.py          # Reflex configuration
├── test_file.py         # Pytest test cases
└── kakumi.db            # SQLite database
```

## Guidelines for AI Agents

1. **Read First**: Always read existing files before modifying to understand patterns
2. **No JavaScript**: If UI functionality is required, search for the equivalent component in the Reflex documentation first.
3. **WKF Compliance**: All scoring, tie-breaking, and draw logic must strictly follow the WKF 2026 regulations provided in the /docs folder.
4. **Follow Conventions**: Match existing code style and architecture
5. **Test Changes**: Verify modifications don't break existing functionality
6. **Document Decisions**: Add comments for non-obvious implementations, particularly regarding tournament logic
7. **Keep it Simple**: Prefer straightforward solutions over complex abstractions
8. **State Management**: Understand how Reflex state works before modifying
9. **Database Safety**: Use transactions and test migrations carefully. Ensure relationships between Athletes, Categories and Referees are correctly handled
10. **Component Reuse**: Use existing project styles and components instead of creating repetitive inline styles. In case there is no component matching the requirements, build it, as long as it doesn't break the structure
11. **Error Handling**: Implement proper error handling with user feedback (e.g., rx.toast) when actions fail
12. **Performance**: Consider re-renders and database query efficiency

## Future Improvements

Based on current codebase analysis:
1. Add formal testing configuration (pytest)
2. Implement code formatters (Black)
3. Add type checking (ruff)
4. Create developer documentation (README, contributing guide)
5. Add pre-commit hooks for code quality
6. Implement CI/CD pipeline
7. Add logging and monitoring
8. Create API documentation for backend endpoints
