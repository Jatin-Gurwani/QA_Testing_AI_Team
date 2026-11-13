from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PIPELINE_MODES_PATH = _PROJECT_ROOT / "config" / "pipeline_modes.yaml"
_TASKS_PATH = _PROJECT_ROOT / "config" / "tasks.yaml"


@dataclass(frozen=True)
class PipelineMode:
    key: str
    label: str
    description: str
    icon: str
    tasks: tuple[str, ...]
    agents_used: tuple[str, ...]


def load_task_names(path: Path = _TASKS_PATH) -> tuple[str, ...]:
    """Return task names in the crew's configured default order."""
    with path.open(encoding="utf-8") as task_file:
        task_configs = yaml.safe_load(task_file)

    if not isinstance(task_configs, dict) or not task_configs:
        raise ValueError(f"Expected a non-empty task mapping in {path}")

    task_names = []
    for task_key, task_config in task_configs.items():
        if not isinstance(task_config, dict) or not isinstance(task_config.get("name"), str):
            raise ValueError(f"Task {task_key!r} in {path} must define a string name")
        task_names.append(task_config["name"])
    return tuple(task_names)


def load_pipeline_modes(
    path: Path = _PIPELINE_MODES_PATH,
    task_names: tuple[str, ...] | None = None,
) -> dict[str, PipelineMode]:
    """Load and validate shared mode definitions for the CLI and GUI."""
    with path.open(encoding="utf-8") as modes_file:
        config: Any = yaml.safe_load(modes_file)

    if not isinstance(config, dict) or not isinstance(config.get("modes"), dict) or not config["modes"]:
        raise ValueError(f"Expected a non-empty 'modes' mapping in {path}")

    available_tasks = set(task_names if task_names is not None else load_task_names())
    modes = {}
    for key, definition in config["modes"].items():
        if not isinstance(key, str) or not key.strip() or not isinstance(definition, dict):
            raise ValueError(f"Each pipeline mode in {path} must have a non-empty key and mapping")

        for field in ("label", "description", "icon"):
            if not isinstance(definition.get(field), str) or not definition[field].strip():
                raise ValueError(f"Pipeline mode {key!r} in {path} must define a non-empty {field}")

        tasks = definition.get("tasks")
        agents_used = definition.get("agents_used")
        if not isinstance(tasks, list) or not all(isinstance(task, str) for task in tasks):
            raise ValueError(f"Pipeline mode {key!r} in {path} must define a list of task names")
        if not isinstance(agents_used, list) or not all(
            isinstance(agent, str) and agent.strip() for agent in agents_used
        ):
            raise ValueError(f"Pipeline mode {key!r} in {path} must define a list of agent names")

        unknown_tasks = set(tasks) - available_tasks
        if unknown_tasks:
            raise ValueError(
                f"Pipeline mode {key!r} in {path} references unknown tasks: "
                f"{', '.join(sorted(unknown_tasks))}"
            )

        modes[key] = PipelineMode(
            key=key,
            label=definition["label"],
            description=definition["description"],
            icon=definition["icon"],
            tasks=tuple(tasks),
            agents_used=tuple(agents_used),
        )
    return modes
