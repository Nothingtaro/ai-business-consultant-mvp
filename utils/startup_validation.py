from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_PROMPTS = (
    "system.md",
    "problem_framing.md",
    "issue_tree.md",
    "hypotheses.md",
    "analysis_plan.md",
    "financial_assumptions.md",
    "executive_memo.md",
    "deck_outline.md",
    "critic.md",
)


@dataclass(frozen=True)
class StartupValidationResult:
    checks: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        return all(self.checks.values()) if self.checks else False


def validate_startup(
    prompts_dir: Path,
    sample_cases_path: Path,
    writable_dirs: tuple[Path, ...],
) -> StartupValidationResult:
    checks: dict[str, bool] = {}
    warnings: list[str] = []

    checks["prompts_dir_exists"] = prompts_dir.exists() and prompts_dir.is_dir()
    missing_prompts = [name for name in REQUIRED_PROMPTS if not (prompts_dir / name).exists()]
    checks["required_prompts_present"] = not missing_prompts
    if missing_prompts:
        warnings.append(f"Missing prompt files: {', '.join(missing_prompts)}")

    checks["sample_cases_valid"] = _sample_cases_are_valid(sample_cases_path)
    if not checks["sample_cases_valid"]:
        warnings.append(f"Sample cases could not be loaded from {sample_cases_path}.")

    writable_ok = True
    for directory in writable_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            test_file = directory / ".startup_check"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
        except OSError:
            writable_ok = False
            warnings.append(f"Directory is not writable: {directory}")
    checks["local_storage_writable"] = writable_ok

    return StartupValidationResult(checks=checks, warnings=warnings)


def _sample_cases_are_valid(path: Path) -> bool:
    if not path.exists():
        return False

    try:
        with path.open(encoding="utf-8") as file:
            cases = json.load(file)
    except json.JSONDecodeError:
        return False

    required_fields = {
        "business_problem",
        "budget",
        "geography",
        "target_customers",
        "constraints",
        "expected_output",
    }
    return isinstance(cases, list) and all(
        isinstance(case, dict) and required_fields.issubset(case)
        for case in cases
    )
