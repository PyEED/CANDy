from __future__ import annotations

import logging
import platform
import shutil
import tempfile
from pathlib import Path

from candy.clustering.mmseqs2_download import resolve_mmseqs2_binary
from candy.config import ClusteringConfig
from candy.external_tools import run_tool

logger = logging.getLogger(__name__)


class Mmseqs2Clusterer:
    """Sequence clustering via MMseqs2.

    Prefers an ``mmseqs`` already on PATH; otherwise transparently downloads
    and caches a static build for the current platform on first use (see
    :mod:`candy.clustering.mmseqs2_download`). This is the default clustering
    backend precisely because that auto-download is possible for MMseqs2 but
    not for CD-HIT (source-only, no Windows build).
    """

    name = "mmseqs2"

    def cluster(self, input_fasta: Path, output_fasta: Path, config: ClusteringConfig) -> Path:
        binary = resolve_mmseqs2_binary()
        if platform.system() == "Windows" and binary.lower().endswith(".bat"):
            logger.info(
                "Clustering on Windows uses MMseqs2's mmseqs.bat wrapper, which may ask for "
                "administrator permission once (to install a small POSIX-shell helper it "
                "needs internally). This only happens on the very first clustering run."
            )
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
