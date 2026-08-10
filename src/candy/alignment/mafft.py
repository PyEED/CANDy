from __future__ import annotations

import logging
from pathlib import Path

from candy.external_tools import require_binary, run_tool

logger = logging.getLogger(__name__)


class MafftAligner:
    """Runs MAFFT directly via subprocess.

    The notebook used Biopython's ``Bio.Align.Applications.MafftCommandline``
    wrapper, which is deprecated upstream and slated for removal from
    Biopython; calling the CLI directly avoids that dependency.
    """

    name = "mafft"

    def align(self, input_fasta: Path, output_fasta: Path) -> Path:
        binary = require_binary(
            "mafft",
            hint=(
                "Install it separately and ensure it's on PATH (e.g. `brew install mafft` on "
                "Intel Mac/Linux, or see https://mafft.cbrc.jp/alignment/software/) -- it isn't "
                "in CANDy's conda environment.yml, which has no macOS arm64 build for it."
            ),
        )
        logger.info("Aligning %s with MAFFT.", input_fasta)
        run_tool([binary, str(input_fasta)], stdout_path=output_fasta)
        return output_fasta
