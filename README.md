# QA Testing AI Team

An AI-powered test case generation system using CrewAI that analyzes GitHub repositories and generates comprehensive test cases based on user requirements.

## Overview

This project uses CrewAI to create a team of AI agents that collaborate to:
1. Analyze a GitHub repository and user requirements
2. Create a test strategy based on the analysis
3. Generate comprehensive test cases for the repository

## Features

- **Repository Analysis**: Analyzes GitHub repositories to understand code structure and functionality
- **Test Strategy Planning**: Creates prioritized test plans based on user requirements (happy path, edge cases, failure cases)
- **Test Case Generation**: Generates executable test cases with proper imports, fixtures, and setup
- **Multiple Interface Options**: 
  - Command-line interface (`main.py`)
  - Graphical user interface using Streamlit (`gui.py`)
- **Multi-Language Support**: Generates tests in the language and framework matching the target project
- **Output Organization**: Saves generated tests and reports in organized output directories

## Architecture

The system consists of three main AI agents working in sequence:

1. **Repository Analyst**: Examines the GitHub repository and user request to understand the codebase
2. **Test Strategy Planner**: Creates a prioritized test plan based on the analysis and user requirements
3. **Test Writer Agent**: Generates actual test cases from the test plan

Configuration is managed through YAML files:
- `config/agents.yaml`: Defines the AI agents and their roles
- `config/tasks.yaml`: Defines the tasks each agent performs
- `config/.env`: Stores API keys and configuration.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/qa-testing-ai-team.git
   cd qa-testing-ai-team
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set up environment variables:
   - Copy `config/.sample_env` to `config/.env`
   - Edit `.env` to add your API keys:
     - `GOOGLE_API_KEY`: Your Google Generative AI API key
     - `MODEL`: Optional - defaults to `gemini/gemini-3.1-flash-lite`

## Usage

### Command Line Interface

```bash
python main.py
```

The CLI will prompt you for:
1. GitHub repository URL
2. GitHub Personal Access Token
3. Your testing request (e.g., "Write unit tests for the auth module, focus on edge cases")

### Graphical User Interface

```bash
streamlit run gui.py
```

The GUI provides a user-friendly interface to:
- Enter GitHub repository URL
- Enter GitHub Personal Access Token (securely masked)
- Describe what you want to test
- View progress animations during processing
- Browse generated test cases and summary reports

## Output Structure

Generated tests and reports are saved in the `outputs/` directory:

```
outputs/
└── {repository_name}/
    ├── analysis_report.md          # Repository analysis
    ├── test_plan.md               # Test strategy and plan
    ├── testcases/                 # Generated test files
    │   ├── test_module1.py
    │   ├── test_module2.js
    │   └── ...
    └── testcases_summary.md       # Summary of generated tests
```

## Development Guidelines

- When modifying agents or tasks, update the corresponding YAML configuration files
- Add new dependencies to `pyproject.toml`
- Test changes using either the CLI (`python main.py`) or GUI (`streamlit run gui.py`)
- The `outputs/` directory is generated at runtime and should not be committed to version control

## Example Usage

1. Start the application: `streamlit run gui.py`
2. Enter a GitHub repository URL (e.g., `https://github.com/username/repository.git`)
3. Provide your GitHub Personal Access Token
4. Describe what you want to test (e.g., "Create unit tests for all authentication functions")
5. Click "Generate Tests" and wait for the AI team to complete the analysis and test generation
6. Browse the generated test cases in the "Test Cases" tab
7. Review the summary in the "Summary" tab

## License

This project is licensed under the MIT License - see the LICENSE file for details.