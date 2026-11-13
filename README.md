# QA Testing AI Team

An AI-powered test case generation, execution, and auditing system using CrewAI that analyzes repositories and generates comprehensive test cases based on user requirements.

## Overview

This project uses CrewAI to create a team of 6 AI agents that collaborate to:
1. **Analyze** a repository and user requirements
2. **Plan** a prioritized test strategy
3. **Generate** comprehensive, runnable test cases
4. **Provision** an isolated Docker sandbox
5. **Execute** tests and perform root cause analysis on failures
6. **Audit** the entire pipeline and produce a graded final report

## Features

- **Repository Analysis**: Analyzes repos (GitHub URLs, local git repos, or local folders) to understand code structure, conventions, and risk areas
- **Test Strategy Planning**: Creates prioritized test plans (P1/P2/P3) based on user requirements (happy path, edge cases, failure cases)
- **Test Case Generation**: Generates executable test cases with proper imports, fixtures, and setup matching project conventions
- **Docker Sandbox Execution**: Provisions isolated Docker containers, runs tests, and performs root cause analysis on failures
- **QA Audit**: Comprehensive graded audit of all pipeline artifacts with actionable recommendations
- **Langfuse Observability**: Optional tracing and monitoring via Langfuse integration
- **Multiple Interface Options**:
  - Command-line interface (`main.py`)
  - Streamlit GUI with dashboard (`gui.py`)
- **Pipeline Modes**: Choose between test generation only, full pipeline with execution, or all tasks
- **Multi-Language Support**: Generates tests matching the target project's language and framework
- **Output Organization**: Saves generated tests, reports, and audit artifacts in organized directories

## Architecture

The system consists of six AI agents working in sequence:

| # | Agent | Role |
|---|-------|------|
| 1 | 🔍 Repository Analyst | Code analysis, convention detection, risk flagging |
| 2 | 📋 Test Strategy Planner | Prioritized test plan design (P1/P2/P3) |
| 3 | ✍️ Test Writer Agent | Test code generation following project conventions |
| 4 | 🐳 Sandbox Engineer | Docker environment provisioning |
| 5 | 🏃 Senior Test Engineer | Test execution & root cause analysis |
| 6 | 📊 QA Expert | Pipeline audit & graded final report |

### Pipeline Modes

| Mode | Description | Agents Used |
|------|-------------|-------------|
| `only_generation` | Analyze → Plan → Write tests | 1, 2, 3 |
| `run_testcase` | Full pipeline with Docker execution + audit | 1-6 |
| `both` | All tasks in default order | 1-6 |

Configuration is managed through YAML files:
- `config/agents.yaml`: Defines the AI agents and their roles
- `config/tasks.yaml`: Defines the tasks each agent performs
- `config/pipeline_modes.yaml`: Defines the selectable task modes shared by the CLI and GUI
- `config/.env`: Stores API keys and configuration

To customize the pipeline modes shown in both interfaces, edit `config/pipeline_modes.yaml`.
Each entry defines a mode key, label, description, icon, task names, and agents shown in the GUI.
Task names must exactly match the `name` values in `config/tasks.yaml`; invalid names are reported
when the configuration loads. An empty `tasks` list runs all tasks in the default order.

For example, add another entry under `modes` to make a custom selection available in both the
CLI and GUI:

```yaml
modes:
  # Keep the existing modes and add this entry alongside them.
  analysis_and_tests:
    label: "Analysis and Tests"
    description: "Analyze the repository and generate tests"
    icon: "🧪"
    tasks:
      - Repository Analysis
      - Test Strategy Planning
      - Test Code Generation
    agents_used:
      - Repository Analyst
      - Strategy Planner
      - Test Writer
```

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
     - `FAST_MODEL`: Model for analysis/sandbox/audit agents
     - `STRONG_MODEL`: Model for planning/writing/execution agents
     - `LANGFUSE_*`: (Optional) Langfuse keys for observability
     - `OUTPUT_FOLDER`: Custom output directory path
     - `REPO_FOLDER`: Custom repo clone directory path

## Usage

### Command Line Interface

```bash
uv run python main.py
```

The CLI will prompt you for:
1. Repository path or GitHub URL
2. Your testing request
3. Pipeline mode selection from `config/pipeline_modes.yaml`

### Graphical User Interface

```bash
uv run streamlit run gui.py
```

The GUI provides:
- **Wide layout** with sidebar navigation
- **Repository input** supporting GitHub URLs and local paths
- **Pipeline mode selection** with visual preview of agents and phases
- **Animated progress** showing active agents during execution
- **Tabbed results dashboard**: Test Cases, Analysis Report, Test Plan, Sandbox Handoff, Execution Report (with RCA), QA Audit, and Raw Output
- **Session run history** in the sidebar
- **Langfuse status** indicator
- **Metric cards** showing artifact counts

## Output Structure

Generated tests and reports are saved in the `outputs/` directory:

```
outputs/
└── {repository_name}/
    ├── analysis_report.md              # Repository analysis
    ├── test_plan.md                    # Test strategy and plan
    ├── testcases/                      # Generated test files
    │   ├── test_module1.py
    │   ├── test_module2.js
    │   └── ...
    ├── testcases_summary.md            # Summary of generated tests
    ├── sandbox_handoff.md              # Docker sandbox details
    ├── Dockerfile                      # (if created by sandbox agent)
    ├── test_results/
    │   ├── test_report.md              # Execution results
    │   ├── container_logs.txt          # Full container logs
    │   └── fail_cases/
    │       ├── test_name_rca.md        # Root cause analysis per failure
    │       └── ...
    └── final_audit_report.md           # QA audit with grades
```

## Development Guidelines

- When modifying agents or tasks, update the corresponding YAML configuration files
- Add new dependencies to `pyproject.toml`
- Test changes using either the CLI (`uv run python main.py`) or GUI (`uv run streamlit run gui.py`)
- The `outputs/` directory is generated at runtime and should not be committed to version control

## License

This project is licensed under the MIT License - see the LICENSE file for details.
