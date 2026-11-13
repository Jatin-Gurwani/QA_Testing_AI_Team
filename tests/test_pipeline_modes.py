import pytest

from app.pipeline_modes import load_pipeline_modes, load_task_names


def test_pipeline_modes_share_valid_task_names():
    modes = load_pipeline_modes()
    available_tasks = set(load_task_names())

    assert set(modes) == {"only_generation", "run_testcase", "both"}
    assert all(set(mode.tasks) <= available_tasks for mode in modes.values())
    assert modes["only_generation"].tasks == (
        "Repository Analysis",
        "Test Strategy Planning",
        "Test Code Generation",
    )
    assert modes["only_generation"].icon == "🧪"
    assert modes["both"].tasks == ()


def test_pipeline_mode_rejects_unknown_task(tmp_path):
    modes_path = tmp_path / "pipeline_modes.yaml"
    modes_path.write_text(
        """
modes:
  custom:
    label: Custom
    description: Custom test mode
    icon: "🧪"
    tasks:
      - Unknown Task
    agents_used:
      - Test Writer
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="references unknown tasks: Unknown Task"):
        load_pipeline_modes(modes_path, task_names=("Repository Analysis",))


def test_custom_pipeline_mode_is_loaded(tmp_path):
    modes_path = tmp_path / "pipeline_modes.yaml"
    modes_path.write_text(
        """
modes:
  analysis_only:
    label: Analysis Only
    description: Analyze the repository
    icon: "🔍"
    tasks:
      - Repository Analysis
    agents_used:
      - Repository Analyst
""",
        encoding="utf-8",
    )

    mode = load_pipeline_modes(modes_path, task_names=("Repository Analysis",))["analysis_only"]

    assert mode.label == "Analysis Only"
    assert mode.tasks == ("Repository Analysis",)
    assert mode.agents_used == ("Repository Analyst",)
