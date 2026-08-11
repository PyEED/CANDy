import os
import subprocess
from unittest.mock import patch

import pytest

from candy.external_tools import MissingDependencyError
from candy.phylogenetics import fasttree_download as m


def test_prefers_binary_already_on_path():
    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value="/usr/bin/FastTree"):
        assert m.resolve_fasttree_binary() == "/usr/bin/FastTree"


def test_falls_back_to_lowercase_binary_name_on_path():
    def fake_find_binary(name):
        return "/usr/bin/fasttree" if name == "fasttree" else None

    with patch("candy.phylogenetics.fasttree_download.find_binary", side_effect=fake_find_binary):
        assert m.resolve_fasttree_binary() == "/usr/bin/fasttree"


def test_uses_cached_binary_if_present(tmp_path):
    cached = tmp_path / m._binary_name()
    cached.write_text("fake binary")

    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value=None), patch(
        "candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path
    ):
        assert m.resolve_fasttree_binary() == str(cached)


def test_raises_when_no_auto_download_env_set_and_nothing_available(tmp_path):
    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value=None), patch(
        "candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path
    ), patch.dict(os.environ, {m.NO_AUTO_DOWNLOAD_ENV: "1"}):
        with pytest.raises(MissingDependencyError, match="automatic download is disabled"):
            m.resolve_fasttree_binary()


def test_download_failure_raises_missing_dependency_error(tmp_path):
    import requests

    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value=None), patch(
        "candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path
    ), patch("candy.phylogenetics.fasttree_download.platform.system", return_value="Linux"), patch(
        "candy.phylogenetics.fasttree_download.requests.get",
        side_effect=requests.ConnectionError("no network"),
    ):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        with pytest.raises(MissingDependencyError, match="Failed to download FastTree"):
            m.resolve_fasttree_binary()


def test_downloads_precompiled_binary_on_linux(tmp_path):
    def fake_download(url, dest):
        assert url == f"{m._RAW_BASE_URL}/FastTree"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("fake linux binary")

    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value=None), patch(
        "candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path
    ), patch("candy.phylogenetics.fasttree_download.platform.system", return_value="Linux"), patch(
        "candy.phylogenetics.fasttree_download._download", side_effect=fake_download
    ):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        binary = m.resolve_fasttree_binary()

    assert binary == str(tmp_path / "FastTree")
    assert (tmp_path / "FastTree").read_text() == "fake linux binary"


def test_downloads_precompiled_exe_on_windows(tmp_path):
    def fake_download(url, dest):
        assert url == f"{m._RAW_BASE_URL}/FastTree.exe"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("fake windows binary")

    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value=None), patch(
        "candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path
    ), patch("candy.phylogenetics.fasttree_download.platform.system", return_value="Windows"), patch(
        "candy.phylogenetics.fasttree_download._download", side_effect=fake_download
    ):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        binary = m.resolve_fasttree_binary()

    assert binary == str(tmp_path / "FastTree.exe")


def test_compiles_from_source_on_macos(tmp_path):
    def fake_download(url, dest):
        assert url == f"{m._RAW_BASE_URL}/FastTree.c"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("/* fake FastTree.c */")

    def fake_run(cmd, **kwargs):
        # simulate the compiler actually producing the output binary
        out_index = cmd.index("-o")
        from pathlib import Path

        Path(cmd[out_index + 1]).write_text("fake compiled binary")
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("candy.phylogenetics.fasttree_download.find_binary", side_effect=lambda name: (
        None if name in ("FastTree", "fasttree") else ("/usr/bin/cc" if name == "cc" else None)
    )), patch("candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path), patch(
        "candy.phylogenetics.fasttree_download.platform.system", return_value="Darwin"
    ), patch("candy.phylogenetics.fasttree_download._download", side_effect=fake_download), patch(
        "candy.phylogenetics.fasttree_download.subprocess.run", side_effect=fake_run
    ):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        binary = m.resolve_fasttree_binary()

    assert binary == str(tmp_path / "FastTree")
    assert (tmp_path / "FastTree").read_text() == "fake compiled binary"


def test_macos_without_a_c_compiler_raises_clear_error(tmp_path):
    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value=None), patch(
        "candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path
    ), patch("candy.phylogenetics.fasttree_download.platform.system", return_value="Darwin"):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        with pytest.raises(MissingDependencyError, match="No C compiler was found"):
            m.resolve_fasttree_binary()


def test_macos_compile_failure_raises_clear_error_with_compiler_output(tmp_path):
    from types import SimpleNamespace

    def fake_download(url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("/* fake FastTree.c */")

    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="clang: error: no such file or directory: 'NOTFOUND'")

    with patch("candy.phylogenetics.fasttree_download.find_binary", side_effect=lambda name: (
        "/usr/bin/cc" if name == "cc" else None
    )), patch("candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path), patch(
        "candy.phylogenetics.fasttree_download.platform.system", return_value="Darwin"
    ), patch("candy.phylogenetics.fasttree_download._download", side_effect=fake_download), patch(
        "candy.phylogenetics.fasttree_download.subprocess.run", side_effect=fake_run
    ):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        with pytest.raises(MissingDependencyError, match="Compiling FastTree from source failed"):
            m.resolve_fasttree_binary()


@pytest.mark.integration
def test_real_download_and_run_fasttree(tmp_path):
    """Exercises the real network download (and, on macOS, compile) against the pinned commit.

    Marked integration since it needs network access (and, on macOS, a C
    compiler); skipped by default runs. Confirmed manually during
    development that the pinned FastTree.exe download works end-to-end on
    Windows (FastTree 2.2.0, exit code 0, real --help output).
    """
    with patch("candy.phylogenetics.fasttree_download.find_binary", return_value=None), patch(
        "candy.phylogenetics.fasttree_download._cache_dir", return_value=tmp_path
    ):
        os.environ.pop(m.NO_AUTO_DOWNLOAD_ENV, None)
        binary = m.resolve_fasttree_binary()

    result = subprocess.run([binary, "-help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "FastTree" in (result.stdout + result.stderr)
