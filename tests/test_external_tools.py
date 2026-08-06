from unittest.mock import patch

import pytest

from candy.external_tools import ExternalToolError, MissingDependencyError, require_binary, run_tool


def test_require_binary_raises_when_missing():
    with patch("candy.external_tools.shutil.which", return_value=None):
        with pytest.raises(MissingDependencyError):
            require_binary("nonexistent-tool")


def test_require_binary_returns_path_when_found():
    with patch("candy.external_tools.shutil.which", return_value="/usr/bin/mafft"):
        assert require_binary("mafft") == "/usr/bin/mafft"


def test_run_tool_raises_with_stderr_message(tmp_path):
    import sys

    script = tmp_path / "fail.py"
    script.write_text("import sys; sys.stderr.write('boom'); sys.exit(2)")

    with pytest.raises(ExternalToolError, match="boom"):
        run_tool([sys.executable, str(script)])


def test_run_tool_succeeds_and_redirects_stdout(tmp_path):
    import sys

    script = tmp_path / "ok.py"
    script.write_text("print('hello')")
    out_path = tmp_path / "out.txt"

    run_tool([sys.executable, str(script)], stdout_path=out_path)

    assert out_path.read_text().strip() == "hello"
