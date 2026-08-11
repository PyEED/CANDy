"""Locate, download, or compile a FastTree binary automatically.

FastTree became CANDy's default ``--tree-tool`` on Macs where VeryFastTree
has no working native build (see :mod:`candy.platform_utils`), but until
now the only way to actually get a ``FastTree`` binary was the bundled
conda environment -- a real, unwelcome extra dependency for anyone who
doesn't already have conda installed (confirmed by a real user hitting
exactly that wall).

Upstream (https://github.com/morgannprice/fasttree) publishes precompiled
binaries for Linux and Windows directly in the repository, and FastTree.c
itself is a single, dependency-free C file (no CMake, no OpenMP requirement
for the plain single-threaded build) that compiles in about a second with
whatever C compiler is already on the machine -- Xcode Command Line Tools
on macOS, build-essential-equivalent on Linux. That makes a "just pip
install and run" story possible here too: on first use, if a binary isn't
already on PATH, fetch a precompiled one (Linux/Windows) or fetch the
source and compile it locally (macOS, which has no precompiled binary
upstream), then cache the result and reuse it on every later run.

Pinned to a specific commit for reproducibility; downloads only ever come
from the official morgannprice/fasttree GitHub repository over HTTPS, and
the whole thing can be disabled with the CANDY_NO_AUTO_DOWNLOAD environment
variable (falling back to requiring `FastTree` on PATH, e.g. via the
bundled conda environment).
"""

from __future__ import annotations

import logging
import os
import platform
import stat
import subprocess
from pathlib import Path

import requests
from platformdirs import user_cache_dir

from candy.external_tools import MissingDependencyError, find_binary

logger = logging.getLogger(__name__)

FASTTREE_REF = "a5a2723ea1e64faf3da7ea514521cfa348891add"
_RAW_BASE_URL = f"https://raw.githubusercontent.com/morgannprice/fasttree/{FASTTREE_REF}"

NO_AUTO_DOWNLOAD_ENV = "CANDY_NO_AUTO_DOWNLOAD"

_COMPILER_CANDIDATES = ["cc", "clang", "gcc"]
_COMPILE_FLAGS = ["-O3", "-fopenmp-simd", "-funsafe-math-optimizations", "-march=native"]


def _cache_dir() -> Path:
    return Path(user_cache_dir("candy")) / "fasttree" / FASTTREE_REF


def _binary_name() -> str:
    return "FastTree.exe" if platform.system() == "Windows" else "FastTree"


def _cached_binary() -> Path | None:
    candidate = _cache_dir() / _binary_name()
    return candidate if candidate.is_file() else None


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def _make_executable(path: Path) -> None:
    if platform.system() != "Windows":
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _provision_precompiled(cache_dir: Path) -> Path:
    asset = "FastTree.exe" if platform.system() == "Windows" else "FastTree"
    binary_path = cache_dir / _binary_name()
    logger.info(
        "Downloading FastTree (%s) for phylogenetics -- this happens once and is cached at %s",
        FASTTREE_REF[:12], cache_dir,
    )
    _download(f"{_RAW_BASE_URL}/{asset}", binary_path)
    _make_executable(binary_path)
    return binary_path


def _find_compiler() -> str | None:
    for candidate in _COMPILER_CANDIDATES:
        path = find_binary(candidate)
        if path:
            return path
    return None


def _provision_by_compiling(cache_dir: Path) -> Path:
    compiler_path = _find_compiler()
    if compiler_path is None:
        raise MissingDependencyError(
            "No C compiler was found on PATH to build FastTree from source (tried: "
            f"{', '.join(_COMPILER_CANDIDATES)}). On macOS, install Xcode Command Line Tools: "
            "`xcode-select --install`. Alternatively, install FastTree yourself (e.g. via "
            "`conda env create -f environment.yml`) or set CANDY_NO_AUTO_DOWNLOAD=1 and provide it "
            "on PATH another way."
        )

    cache_dir.mkdir(parents=True, exist_ok=True)
    source_path = cache_dir / "FastTree.c"
    binary_path = cache_dir / _binary_name()
    logger.info(
        "No precompiled FastTree is available for macOS -- compiling it from source with %s "
        "(one-time, cached at %s).",
        compiler_path, cache_dir,
    )
    _download(f"{_RAW_BASE_URL}/FastTree.c", source_path)

    result = subprocess.run(
        [compiler_path, *_COMPILE_FLAGS, "-o", str(binary_path), str(source_path), "-lm"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not binary_path.is_file():
        raise MissingDependencyError(
            f"Compiling FastTree from source failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    _make_executable(binary_path)
    return binary_path


def resolve_fasttree_binary() -> str:
    """Return a path to a usable FastTree binary, downloading/compiling one if needed.

    Resolution order: PATH, then the local cache, then (unless disabled via
    the CANDY_NO_AUTO_DOWNLOAD env var) automatic provisioning for the
    current platform -- a precompiled download on Linux/Windows, or a local
    from-source compile on macOS (where no precompiled binary is published
    upstream).
    """
    for name in ("FastTree", "fasttree"):
        on_path = find_binary(name)
        if on_path:
            return on_path

    cached = _cached_binary()
    if cached:
        return str(cached)

    if os.environ.get(NO_AUTO_DOWNLOAD_ENV):
        raise MissingDependencyError(
            "FastTree was not found on PATH and automatic download is disabled "
            f"({NO_AUTO_DOWNLOAD_ENV} is set). Install it yourself (e.g. via "
            "`conda env create -f environment.yml`) or unset that variable."
        )

    cache_dir = _cache_dir()
    try:
        if platform.system() == "Darwin":
            binary = _provision_by_compiling(cache_dir)
        else:
            binary = _provision_precompiled(cache_dir)
    except requests.RequestException as exc:
        raise MissingDependencyError(
            f"Failed to download FastTree automatically: {exc}. Install it yourself (e.g. via "
            "`conda env create -f environment.yml`) or check your network connection. You can also "
            f"set {NO_AUTO_DOWNLOAD_ENV}=1 to disable this download attempt."
        ) from exc

    return str(binary)
