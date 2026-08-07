"""Locate or auto-download a static MMseqs2 binary.

MMseqs2 has no pip-native Python bindings, but -- unlike CD-HIT, which is
source-only and has no Windows build -- upstream publishes genuine static
binaries for every major platform (Linux, macOS, Windows, ARM64, PPC64LE).
That makes it possible to give CANDy a "just pip install and run" clustering
backend: on first use, if ``mmseqs`` isn't already on PATH, download and
cache the correct static build from the official GitHub release, and reuse
it on every later run.

This reaches out to the network and runs a downloaded binary automatically,
which is a real trust decision, not just a convenience one: the exact
release version is pinned below, downloads only ever come from the official
soedinglab/MMseqs2 GitHub release over HTTPS, and the whole thing can be
disabled with the CANDY_NO_AUTO_DOWNLOAD environment variable (falling back
to requiring `mmseqs` on PATH, e.g. via the bundled conda environment --
except on Windows, see below, where bioconda publishes no `mmseqs2` build at
all).

Windows note: MMseqs2's clustering workflows (``cluster``, ``linclust``, and
their ``easy-*`` wrappers) are implemented as shell scripts even inside the
compiled binary, not pure compiled code. On Linux/macOS that's invisible
since a POSIX shell is always present. On Windows there usually isn't one,
so the official release instead ships a `mmseqs.bat` wrapper plus a bundled
`busybox.exe`; on first invocation, `mmseqs.bat` tries to silently install
busybox's POSIX utilities via symlinks, and Windows only allows unprivileged
symlink creation with Developer Mode enabled -- otherwise `mmseqs.bat` falls
back to popping a UAC administrator-elevation prompt. This is documented
upstream (the MMseqs2 user guide lists WSL as the *recommended* Windows
install path, with this static build as a fallback for anyone who can't use
WSL). CANDy resolves to `mmseqs.bat` (not `mmseqs.exe` directly) on Windows
so that self-install happens automatically; expect a one-time UAC prompt on
the first clustering run on a Windows machine without Developer Mode, never
again after that (the installed helpers are cached).
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import stat
import tarfile
import zipfile
from pathlib import Path

import requests
from platformdirs import user_cache_dir

from candy.external_tools import MissingDependencyError, find_binary

logger = logging.getLogger(__name__)

MMSEQS2_VERSION = "18-8cc5c"
_RELEASE_BASE_URL = f"https://github.com/soedinglab/MMseqs2/releases/download/{MMSEQS2_VERSION}"

_ASSET_BY_PLATFORM = {
    ("Linux", "x86_64"): "mmseqs-linux-sse41.tar.gz",
    ("Linux", "aarch64"): "mmseqs-linux-arm64.tar.gz",
    ("Linux", "arm64"): "mmseqs-linux-arm64.tar.gz",
    ("Linux", "ppc64le"): "mmseqs-linux-ppc64le-power9.tar.gz",
    ("Darwin", "x86_64"): "mmseqs-osx-universal.tar.gz",
    ("Darwin", "arm64"): "mmseqs-osx-universal.tar.gz",
    ("Windows", "x86_64"): "mmseqs-win64.zip",
    ("Windows", "AMD64"): "mmseqs-win64.zip",
}

NO_AUTO_DOWNLOAD_ENV = "CANDY_NO_AUTO_DOWNLOAD"


def _cache_dir() -> Path:
    return Path(user_cache_dir("candy")) / "mmseqs2" / MMSEQS2_VERSION


def _binary_name() -> str:
    # On Windows we deliberately resolve to the .bat wrapper, not mmseqs.exe
    # directly -- see the module docstring for why (POSIX-shell workflow
    # scripts + one-time busybox self-install).
    return "mmseqs.bat" if platform.system() == "Windows" else "mmseqs"


def _find_extracted_binary(root: Path) -> Path | None:
    if not root.is_dir():
        return None
    target = _binary_name()
    for path in root.rglob(target):
        if path.is_file():
            return path
    return None


def _download_and_extract(asset: str, cache_dir: Path) -> Path:
    url = f"{_RELEASE_BASE_URL}/{asset}"
    logger.info(
        "Downloading MMseqs2 %s (%s) for clustering -- this happens once and is cached at %s",
        MMSEQS2_VERSION, asset, cache_dir,
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    archive_path = cache_dir / asset
    extract_dir = cache_dir / "extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(archive_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 20):
                f.write(chunk)

    extract_dir.mkdir(exist_ok=True)
    if asset.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(extract_dir)
    else:
        with tarfile.open(archive_path) as tf:
            tf.extractall(extract_dir)
    archive_path.unlink()

    binary = _find_extracted_binary(extract_dir)
    if binary is None:
        raise MissingDependencyError(
            f"Downloaded MMseqs2 archive '{asset}' did not contain a '{_binary_name()}' executable."
        )

    if platform.system() != "Windows":
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return binary


def resolve_mmseqs2_binary() -> str:
    """Return a path to a usable ``mmseqs`` binary, downloading one if needed.

    Resolution order: PATH, then the local cache, then (unless disabled via
    the CANDY_NO_AUTO_DOWNLOAD env var) a fresh download of the pinned
    MMseqs2 release for the current platform.
    """
    on_path = find_binary("mmseqs")
    if on_path:
        return on_path

    cache_dir = _cache_dir()
    cached = _find_extracted_binary(cache_dir)
    if cached:
        return str(cached)

    if os.environ.get(NO_AUTO_DOWNLOAD_ENV):
        raise MissingDependencyError(
            "mmseqs was not found on PATH and automatic download is disabled "
            f"({NO_AUTO_DOWNLOAD_ENV} is set). Install MMseqs2 yourself (e.g. via "
            "`conda env create -f environment.yml`) or unset that variable."
        )

    platform_key = (platform.system(), platform.machine())
    asset = _ASSET_BY_PLATFORM.get(platform_key)
    if asset is None:
        raise MissingDependencyError(
            f"No known MMseqs2 static build for platform {platform_key}. Install "
            "MMseqs2 yourself and ensure it is on PATH."
        )

    try:
        binary = _download_and_extract(asset, cache_dir)
    except requests.RequestException as exc:
        raise MissingDependencyError(
            f"Failed to download MMseqs2 automatically: {exc}. Install it yourself "
            "(e.g. via `conda env create -f environment.yml`) or check your network connection. "
            f"You can also set {NO_AUTO_DOWNLOAD_ENV}=1 to disable this download attempt."
        ) from exc

    return str(binary)
