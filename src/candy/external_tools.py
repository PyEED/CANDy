"""Locate external CLI tools (CD-HIT, MMseqs2, MAFFT, FastTree) on PATH.

The notebook installed these itself at runtime with Colab-only shell magics
(``!apt-get install mafft``, downloading a Linux MMseqs2 binary, compiling
CD-HIT from source). A pip package can't do that portably, so CANDy instead
expects these tools to already be on PATH -- the documented install path is
the bundled conda ``environment.yml`` (bioconda ships all four).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_CONDA_HINT = (
    "Install it via the bundled conda environment: "
    "`conda env create -f environment.yml && conda activate candy`."
)


class MissingDependencyError(RuntimeError):
    """Raised when a required external CLI tool isn't available on PATH."""


def require_binary(name: str, *, hint: str = _CONDA_HINT) -> str:
    """Return the resolved path to ``name`` on PATH, or raise a clear error."""
    path = shutil.which(name)
    if path is None:
        raise MissingDependencyError(
            f"Required external tool '{name}' was not found on PATH. {hint}"
        )
    return path


def find_binary(name: str) -> str | None:
    """Return the resolved path to ``name`` on PATH, or None if not found."""
    return shutil.which(name)


class ExternalToolError(RuntimeError):
    """Raised when an external CLI tool exits with a non-zero status."""


def run_tool(
    args: list[str], *, cwd: Path | None = None, stdout_path: Path | None = None
) -> subprocess.CompletedProcess:
    """Run an external CLI tool, raising a readable error (with stderr) on failure.

    If ``stdout_path`` is given, the subprocess's stdout is streamed straight
    to that file (used for tools like FastTree that write results to stdout).
    """
    if stdout_path is not None:
        with open(stdout_path, "w") as stdout_file:
            result = subprocess.run(
                args, cwd=cwd, stdout=stdout_file, stderr=subprocess.PIPE, text=True
            )
    else:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)

    if result.returncode != 0:
        raise ExternalToolError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n{result.stderr}"
        )
    return result
