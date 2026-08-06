from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from candy.config import ClusteringConfig
from candy.external_tools import require_binary, run_tool

logger = logging.getLogger(__name__)


class Mmseqs2Clusterer:
    name = "mmseqs2"

    def cluster(self, input_fasta: Path, output_fasta: Path, config: ClusteringConfig) -> Path:
        binary = require_binary("mmseqs")
        min_seq_id = config.identity_cutoff / 100
        min_coverage = config.mmseqs_min_coverage / 100

        logger.info("Clustering with MMseqs2 at %.0f%% identity.", config.identity_cutoff)
        with tempfile.TemporaryDirectory(prefix="candy_mmseqs2_") as tmp_dir:
            tmp_dir = Path(tmp_dir)
            output_prefix = tmp_dir / "cluster"
            run_tool(
                [
                    binary,
                    "easy-cluster",
                    str(input_fasta),
                    str(output_prefix),
                    str(tmp_dir / "tmp"),
                    "--min-seq-id", f"{min_seq_id}",
                    "-c", f"{min_coverage}",
                    "--cov-mode", str(config.mmseqs_cov_mode),
                ]
            )
            representative_sequences = Path(f"{output_prefix}_rep_seq.fasta")
            shutil.copyfile(representative_sequences, output_fasta)

        return output_fasta
