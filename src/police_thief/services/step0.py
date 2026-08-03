"""Step-0 computational-fairness declaration (Chapter 5, Sec. 5.5).

Before the first move, each side declares its own hardware spec, code
version, team name, and game/sub-game count, cryptographically signed with
a pre-shared key so it cannot be forged after the fact. This does not by
itself equalize hardware -- it makes any hardware advantage *visible* and
auditable, feeding into the league's computational-fairness scoring
incentive (Chapter 9), which is not implemented here.
"""

from __future__ import annotations

import hmac
import os
import platform
import subprocess
from dataclasses import asdict, dataclass
from hashlib import sha256

from police_thief.services.commit_reveal import canonical_json


class GitCommitHashError(RuntimeError):
    """Raised when the current git commit hash cannot be determined."""


def get_git_commit_hash(cwd: str | None = None) -> str:
    """Sec. 5.5.5-5.5.6: the exact commit hash used must be recorded per game."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitCommitHashError(f"could not determine git commit hash: {exc}") from exc
    return result.stdout.strip()


def _detect_ram_gb() -> float:
    """Best-effort, stdlib-only RAM detection; 0.0 on any failure/unsupported OS.

    Never raises -- a Step-0 declaration with an unknown RAM figure is far
    better than one that crashes the match before it starts.
    """
    try:
        system = platform.system()
        if system == "Windows":
            import ctypes

            class _MemStatus(ctypes.Structure):
                # Must match Windows' MEMORYSTATUSEX exactly, field-for-field:
                # GlobalMemoryStatusEx validates dwLength against its own
                # (fixed, 9-field) struct size and silently no-ops if it
                # doesn't match -- a partial struct looks like it "works"
                # but leaves ullTotalPhys at 0.
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MemStatus()
            stat.dwLength = ctypes.sizeof(_MemStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return round(stat.ullTotalPhys / (1024**3), 2)
        if system == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return round(int(line.split()[1]) / (1024**2), 2)
        if system == "Darwin":
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True
            )
            return round(int(out.stdout.strip()) / (1024**3), 2)
    except Exception:  # noqa: BLE001 -- hardware detection must never crash Step-0
        pass
    return 0.0


@dataclass(frozen=True)
class HardwareSpec:
    """docs/tasks.md Sec. 5.5.3: OS, cores, RAM, GPU presence, LLM model."""

    os_name: str
    cpu_count: int
    ram_gb: float
    gpu_present: bool
    llm_model: str


def gather_hardware_spec(llm_model: str, gpu_present: bool = False) -> HardwareSpec:
    """`gpu_present` is caller-supplied: GPU detection is vendor/platform
    specific and out of scope for a lightweight, dependency-free fairness
    declaration -- callers that know their own setup can report it directly.
    """
    return HardwareSpec(
        os_name=platform.system(),
        cpu_count=os.cpu_count() or 0,
        ram_gb=_detect_ram_gb(),
        gpu_present=gpu_present,
        llm_model=llm_model,
    )


@dataclass(frozen=True)
class Step0Declaration:
    """Everything Sec. 5.5.3/5.5.6 require before the first real move.

    config_fingerprint (Sec. 4.2.6/5.5) cryptographically locks the shared
    config/game.json -- including the otherwise-fixed scent parameters --
    at Step-0 time: see shared/game_config.py::config_fingerprint.
    """

    hardware: HardwareSpec
    code_version: str
    team_name: str
    game_id: str
    sub_game_number: int
    git_commit_hash: str
    config_fingerprint: str


@dataclass(frozen=True)
class SignedStep0:
    """The declaration plus its HMAC-SHA256 signature over canonical JSON."""

    declaration: Step0Declaration
    signature: str


def sign_step0(declaration: Step0Declaration, shared_key: bytes) -> SignedStep0:
    """HMAC-SHA256, not a bare hash: a pre-shared *key* authenticates the
    declaration's origin, which a keyless hash cannot do.
    """
    payload = canonical_json(asdict(declaration))
    signature = hmac.new(shared_key, payload, sha256).hexdigest()
    return SignedStep0(declaration=declaration, signature=signature)


def verify_step0_signature(signed: SignedStep0, shared_key: bytes) -> bool:
    payload = canonical_json(asdict(signed.declaration))
    expected = hmac.new(shared_key, payload, sha256).hexdigest()
    return hmac.compare_digest(expected, signed.signature)


@dataclass
class TokenUsage:
    """Running LLM token counter (Sec. 5.5.4). Wired to real LLM calls in
    Chapter 6; sealed into the Step-0/results JSON reporting in Chapter 9.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    available: bool = False

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.available = True

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens
