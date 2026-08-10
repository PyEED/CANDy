"""OS/CPU-architecture detection helpers.

Split out on its own so both ``pipeline.py`` (which warns about a translated
interpreter) and ``config.py`` (which picks a platform-appropriate default
tree-building backend) can share the same detection logic without a
circular import between those two modules.
"""

from __future__ import annotations

import platform
import subprocess


def is_apple_silicon_under_rosetta() -> bool:
    """True if this is x86_64 Python running via Rosetta 2 translation on Apple Silicon."""
    if platform.system() != "Darwin" or platform.machine() != "x86_64":
        return False
    try:
        translated = subprocess.run(
            ["sysctl", "-n", "sysctl.proc_translated"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return translated.stdout.strip() == "1"


def is_macos_without_native_veryfasttree_wheel() -> bool:
    """True if ``veryfasttree`` has no reliable prebuilt wheel on this Mac.

    ``veryfasttree`` (as of 4.0.4.1) only publishes a macOS wheel for
    x86_64 -- there is no ``arm64`` build at all. That makes this true on
    two distinct occasions: genuine Apple Silicon hardware (no wheel
    exists, so installing it falls back to compiling from source, which
    fails on stock macOS due to an upstream OpenMP-detection bug in
    veryfasttree's own CMakeLists.txt), and x86_64 Python running under
    Rosetta 2 translation on Apple Silicon (a wheel *does* exist and
    installs fine, but running translated native SIMD code is a known
    cause of a silent 'illegal hardware instruction' crash -- the same
    class of bug already seen with FAMSA on a translated interpreter).
    """
    if platform.system() != "Darwin":
        return False
    return platform.machine() == "arm64" or is_apple_silicon_under_rosetta()
