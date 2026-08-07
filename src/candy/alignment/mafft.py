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
        binary = require_binary("mafft")
        logger.info("Aligning %s with MAFFT.", input_fasta)
        run_tool([binary, str(input_fasta)], stdout_path=output_fasta)
        return output_fasta
