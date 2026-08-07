from __future__ import annotations

import logging
from pathlib import Path

from candy.config import ClusteringConfig
from candy.external_tools import require_binary, run_tool

logger = logging.getLogger(__name__)

# CD-HIT's word-length and memory-limit flags aren't exposed as pipeline
# parameters (the notebook hardcoded them too); they only affect runtime,
# not clustering results.
_WORD_LENGTH = 5
_MEMORY_LIMIT_MB = 8000
_DESCRIPTION_LENGTH = 20


class CdHitClusterer:
    name = "cd-hit"

    def cluster(self, input_fasta: Path, output_fasta: Path, config: ClusteringConfig) -> Path:
        binary = require_binary("cd-hit")
        identity = config.identity_cutoff / 100
        min_long_coverage = config.cdhit_min_long_coverage / 100
        min_short_coverage = config.cdhit_min_short_coverage / 100

        logger.info("Clustering with CD-HIT at %.0f%% identity.", config.identity_cutoff)
        run_tool(
            [
                binary,
                "-i", str(input_fasta),
                "-o", str(output_fasta),
                "-c", f"{identity}",
                "-n", str(_WORD_LENGTH),
                "-d", str(_DESCRIPTION_LENGTH),
                "-M", str(_MEMORY_LIMIT_MB),
                "-aL", f"{min_long_coverage}",
                "-aS", f"{min_short_coverage}",
            ]
        )
        return output_fasta
