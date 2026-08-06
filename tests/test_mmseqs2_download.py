import os
from pathlib import Path
from unittest.mock import patch

import pytest

from candy.external_tools import MissingDependencyError
from candy.clustering import mmseqs2_download as m


def test_prefers_binary_already_on_path():
    with patch("candy.clustering.mmseqs2_download.find_binary", return_value="/usr/bin/mmseqs"):
        assert m.resolve_mmseqs2_binary() == "/usr/bin/mmseqs"


def test_uses_cached_binary_if_present(tmp_path):
    cached = tmp_path / "extracted" / "mmseqs" / "bin" / m._binary_name()
    cached.parent.mkdir(parents=True)
    cached.write_text("fake binary")

    with patch("candy.clustering.mmseqs2_download.find_binary", return_value=None), patch(
        "candy.clustering.mmseqs2_download._cache_dir", return_value=tmp_path
    ):
        assert m.resolve_mmseqs2_binary() == str(cached)


def test_raises_when_no_auto_download_env_set_and_nothing_available(tmp_path):
    with patch("candy.clustering.mmseqs2_download.find_binary", return_value=None), patch(
        "candy.clustering.mmseqs2_download._cache_dir", return_value=tmp_path
    ), patch.dict(os.environ, {m.NO_AUTO_DOWNLOAD_ENV: "1"}):
        with pytest.raises(MissingDependencyError, match="automatic download is disabled"):
            m.resolve_mmseqs2_binary()


def test_raises_clear_error_for_unknown_platform(tmp_path):
    with patch("candy.clustering.mmseqs2_download.find_binary", return_value=None), patch(
        "candy.clustering.mmseqs2_download._cache_dir", return_value=tmp_path
    ), patch("candy.clustering.mmseqs2_download.platform.system", return_value="Plan9"), patch(
        "candy.clustering.mmseqs2_download.platform.machine", return_value="mips"
    ), patch.dict(os.environ, {}, clear=False):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        with pytest.raises(MissingDependencyError, match="No known MMseqs2 static build"):
            m.resolve_mmseqs2_binary()


def test_download_failure_raises_missing_dependency_error(tmp_path):
    import requests

    with patch("candy.clustering.mmseqs2_download.find_binary", return_value=None), patch(
        "candy.clustering.mmseqs2_download._cache_dir", return_value=tmp_path
    ), patch("candy.clustering.mmseqs2_download.platform.system", return_value="Linux"), patch(
        "candy.clustering.mmseqs2_download.platform.machine", return_value="x86_64"
    ), patch("candy.clustering.mmseqs2_download.requests.get", side_effect=requests.ConnectionError("no network")):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        with pytest.raises(MissingDependencyError, match="Failed to download MMseqs2"):
            m.resolve_mmseqs2_binary()


def test_asset_selection_covers_major_platforms():
    assert m._ASSET_BY_PLATFORM[("Linux", "x86_64")] == "mmseqs-linux-sse41.tar.gz"
    assert m._ASSET_BY_PLATFORM[("Darwin", "arm64")] == "mmseqs-osx-universal.tar.gz"
    assert m._ASSET_BY_PLATFORM[("Windows", "AMD64")] == "mmseqs-win64.zip"


@pytest.mark.integration
def test_real_download_and_run_mmseqs2(tmp_path):
    """Exercises the real network download + extraction against the pinned release.

    Marked integration since it needs network access; skipped by default runs
    that filter out that marker, but was run manually during development to
    confirm the auto-download path genuinely works end-to-end.

    On Windows this deliberately does NOT invoke the resolved mmseqs.bat
    directly: .bat always attempts its one-time busybox self-install (even
    for a plain "version" call), which can pop a UAC prompt -- unsuitable
    for an unattended/CI test run. Instead it locates the underlying
    mmseqs.exe inside the same extracted tree and runs that directly, which
    validates the download+extraction worked without touching the
    self-install path. On Linux/macOS, resolve_mmseqs2_binary() already
    returns the plain binary, so it's exercised directly either way.
    """
    import platform
    import subprocess

    with patch("candy.clustering.mmseqs2_download.find_binary", return_value=None), patch(
        "candy.clustering.mmseqs2_download._cache_dir", return_value=tmp_path
    ):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        binary = m.resolve_mmseqs2_binary()

    if platform.system() == "Windows":
        binary = str(next(Path(binary).parent.glob("bin/mmseqs.exe")))

    result = subprocess.run([binary, "version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip()
