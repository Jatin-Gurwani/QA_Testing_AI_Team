# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- **Run the application (CLI)**: `python main.py`
- **Run the application (GUI)**: `streamlit run gui.py`
- **Run tests**: `pytest` (note: currently no tests exist, but this is the test runner)

## Code Architecture and Structure

The project is a CrewAI-based application designed to generate test cases for a given GitHub repository. It consists of:

- **main.py**: Entry point for command-line interface. Prompts for GitHub repository URL, personal access token, and user request, then runs the QACrew.
- **gui.py**: Streamlit-based graphical interface that provides a user-friendly way to interact with the QACrew.
- **app/crew.py**: Defines the `QACrew` class, which sets up the CrewAI agents and tasks. It uses configurations from `config/agents.yaml` and `config/tasks.yaml`.
- **config/agents.yaml**: Defines the agents used in the crew:
  - `repository_analyst`: Analyzes the repository and user request.
  - `test_strategy_planner`: Creates a test plan based on the analysis.
  - `test_writer_agent`: Writes the test cases.
- **config/tasks.yaml**: Defines the tasks for each agent:
  - `repository_analysis_task`: Analyzes the repository and user request.
  - `test_strategy_task`: Creates a test plan.
  - `test_generation_task`: Generates test cases.
- **config/.env**: Stores API keys (Google, Groq, GitHub PAT) and model configuration. Note: There is a typo in the key for GitHub PAT (`GJTHUB_PAT_` instead of `GITHUB_PAT`), but the code expects `GITHUB_PAT`.
- **outputs/**: Directory where generated test cases and reports are saved (created at runtime).

The workflow is sequential: the repository analyst first analyzes the repository and user request, then the test strategy planner creates a test plan, and finally the test writer agent generates the test cases.

The application uses various tools via CrewAI's MCP (Model Context Protocol) servers, including a filesystem MCP and a GitHub MCP (via GitHub Copilot) to interact with the repository.

## Important Notes

- The application requires API keys for Google Generative AI, Groq, and a GitHub Personal Access Token to function.
- The GitHub PAT is expected to be set in the environment variable `GITHUB_PAT` (note the typo in the sample .env file).
- The model used is configured via the `MODEL` environment variable (default: `gemini/gemini-3.1-flash-lite`).

## Development Guidelines

- When modifying agents or tasks, update the corresponding YAML configuration files.
- Ensure any new dependencies are added to `pyproject.toml`.
- Test the application using either the CLI or GUI to verify changes.
- The output directory (`outputs/`) is generated at runtime and should not be committed to version control.