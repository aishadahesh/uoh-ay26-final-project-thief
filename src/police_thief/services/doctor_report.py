"""The doctor report shape and its text/JSON renderings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    role: str
    offline: bool
    checks: list[DoctorCheck]

    @property
    def exit_code(self) -> int:
        return 1 if any(check.status == "FAIL" for check in self.checks) else 0

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "offline": self.offline,
            "exit_code": self.exit_code,
            "checks": [asdict(check) for check in self.checks],
        }


def render_text(report: DoctorReport) -> str:
    lines = [f"doctor role={report.role} offline={str(report.offline).lower()}"]
    for check in report.checks:
        lines.append(f"{check.status:12} {check.name}: {check.detail}")
    return "\n".join(lines)


def save_json_report(report: DoctorReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
