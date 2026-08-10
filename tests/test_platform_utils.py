from types import SimpleNamespace
from unittest.mock import patch

from candy.platform_utils import is_apple_silicon_under_rosetta, is_macos_without_native_veryfasttree_wheel


def test_is_apple_silicon_under_rosetta_true_when_translated():
    with patch("candy.platform_utils.platform.system", return_value="Darwin"), patch(
        "candy.platform_utils.platform.machine", return_value="x86_64"
    ), patch(
        "candy.platform_utils.subprocess.run",
        return_value=SimpleNamespace(stdout="1\n"),
    ):
        assert is_apple_silicon_under_rosetta() is True


def test_is_apple_silicon_under_rosetta_false_on_native_arm64():
    with patch("candy.platform_utils.platform.system", return_value="Darwin"), patch(
        "candy.platform_utils.platform.machine", return_value="arm64"
    ), patch("candy.platform_utils.subprocess.run") as mock_run:
        assert is_apple_silicon_under_rosetta() is False

    mock_run.assert_not_called()


def test_is_apple_silicon_under_rosetta_false_on_genuine_intel_mac():
    # On a real Intel Mac, `sysctl -n sysctl.proc_translated` reports "0"
    # (the key exists but the process isn't translated).
    with patch("candy.platform_utils.platform.system", return_value="Darwin"), patch(
        "candy.platform_utils.platform.machine", return_value="x86_64"
    ), patch(
        "candy.platform_utils.subprocess.run",
        return_value=SimpleNamespace(stdout="0\n"),
    ):
        assert is_apple_silicon_under_rosetta() is False


def test_is_apple_silicon_under_rosetta_false_on_non_macos():
    with patch("candy.platform_utils.platform.system", return_value="Windows"), patch(
        "candy.platform_utils.subprocess.run"
    ) as mock_run:
        assert is_apple_silicon_under_rosetta() is False

    mock_run.assert_not_called()


def test_is_apple_silicon_under_rosetta_tolerates_missing_sysctl():
    # Defensive: sysctl.proc_translated not existing (or sysctl missing
    # entirely) must never crash the caller over a best-effort check.
    with patch("candy.platform_utils.platform.system", return_value="Darwin"), patch(
        "candy.platform_utils.platform.machine", return_value="x86_64"
    ), patch("candy.platform_utils.subprocess.run", side_effect=OSError("no such command")):
        assert is_apple_silicon_under_rosetta() is False  # must not raise


def test_is_macos_without_native_veryfasttree_wheel_true_on_native_arm64():
    # No macOS arm64 wheel exists for veryfasttree at all (as of 4.0.4.1).
    with patch("candy.platform_utils.platform.system", return_value="Darwin"), patch(
        "candy.platform_utils.platform.machine", return_value="arm64"
    ):
        assert is_macos_without_native_veryfasttree_wheel() is True


def test_is_macos_without_native_veryfasttree_wheel_true_under_rosetta():
    # A wheel exists for macOS x86_64 and installs fine, but running it
    # translated is a known SIGILL risk -- same class of bug as FAMSA.
    with patch("candy.platform_utils.platform.system", return_value="Darwin"), patch(
        "candy.platform_utils.platform.machine", return_value="x86_64"
    ), patch("candy.platform_utils.is_apple_silicon_under_rosetta", return_value=True):
        assert is_macos_without_native_veryfasttree_wheel() is True


def test_is_macos_without_native_veryfasttree_wheel_false_on_genuine_intel_mac():
    with patch("candy.platform_utils.platform.system", return_value="Darwin"), patch(
        "candy.platform_utils.platform.machine", return_value="x86_64"
    ), patch("candy.platform_utils.is_apple_silicon_under_rosetta", return_value=False):
        assert is_macos_without_native_veryfasttree_wheel() is False


def test_is_macos_without_native_veryfasttree_wheel_false_on_non_macos():
    with patch("candy.platform_utils.platform.system", return_value="Linux"):
        assert is_macos_without_native_veryfasttree_wheel() is False
