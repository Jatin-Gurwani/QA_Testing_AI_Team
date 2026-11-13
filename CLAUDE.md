# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the application (CLI)**: `uv run python main.py`
- **Run the application (GUI)**: `uv run streamlit run gui.py`
- **Run tests**: `pytest` (note: currently no tests exist, but this is the test runner)

## Code Architecture and Structure

The project is a CrewAI-based application (Phase 2) designed to generate, execute, and audit test cases for a given repository. It consists of:

- **main.py**: Entry point for command-line interface. Prompts for repository path/URL and user request, supports Langfuse observability, and selectable pipeline modes (`only_generation`, `run_testcase`, `both`).
- **gui.py**: Streamlit-based graphical interface (wide layout, sidebar) that provides a full-featured dashboard with pipeline mode selection, animated progress, tabbed results (Test Cases, Analysis, Test Plan, Sandbox, Execution, QA Audit), run history, and Langfuse status.
- **app/crew.py**: Defines the `QACrew` class which takes a repo path/URL, supports local paths, git repos, and remote `.git` URLs. Uses `FAST_MODEL`, `STRONG_MODEL`, and `NVIDIA_MODEL` LLMs. Sets up 6 agents and 6 tasks via CrewAI decorators. Supports task filtering via `tasks_name_list` parameter.
- **config/agents.yaml**: Defines 6 agents:
  - `repository_analyst`: Code analysis & triage
  - `test_strategy_planner`: Test plan design
  - `test_writer_agent`: Test code generation
  - `sandbox_engineer`: Docker environment provisioning
  - `senior_test_engineer`: Test execution & root cause analysis
  - `qa_expert`: QA audit & final report
- **config/tasks.yaml**: Defines 6 tasks:
  - `repository_analysis_task`: Analyzes repo structure, conventions, risk flags
  - `test_strategy_task`: Creates prioritized test plan (P1/P2/P3)
  - `test_generation_task`: Generates runnable test files
  - `env_setup_task`: Provisions Docker sandbox
  - `test_execution_task`: Runs tests, performs RCA on failures
  - `qa_audit_task`: Audits all artifacts, produces graded final report
- **config/.env**: Stores API keys and model configuration (`GOOGLE_API_KEY`, `FAST_MODEL`, `STRONG_MODEL`, `LANGFUSE_*`, `OUTPUT_FOLDER`, `REPO_FOLDER`, etc.)
- **outputs/**: Directory where all generated artifacts are saved (created at runtime).

### Pipeline Modes
- **only_generation**: Analyze → Plan → Write tests (3 agents)
- **run_testcase**: Full pipeline with Docker execution + QA audit (6 agents)
- **both**: All tasks in default sequential order

The application uses MCP servers for filesystem access, git operations, and Docker management.

## Important Notes

- `QACrew(path)` constructor requires a path argument (GitHub URL, local git repo, or local folder).
- API keys are configured in `config/.env` (see `config/.sample_env` for template).
- Models: `FAST_MODEL` (for analysis/sandbox/audit), `STRONG_MODEL` (for planning/writing/execution).
- Langfuse observability is optional — the app gracefully degrades if unavailable.
- The GUI removes the GitHub PAT field (now handled via `.env` config).

## Development Guidelines

- When modifying agents or tasks, update the corresponding YAML configuration files.
- Ensure any new dependencies are added to `pyproject.toml`.
- Test the application using either the CLI or GUI to verify changes.
- The output directory (`outputs/`) is generated at runtime and should not be committed to version control.