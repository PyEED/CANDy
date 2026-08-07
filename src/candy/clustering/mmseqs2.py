from __future__ import annotations

import logging
import platform
import shutil
import tempfile
from pathlib import Path

from candy.clustering.mmseqs2_download import resolve_mmseqs2_binary
from candy.config import ClusteringConfig
from candy.external_tools import ExternalToolError, run_tool

logger = logging.getLogger(__name__)


class Mmseqs2Clusterer:
    """Sequence clustering via MMseqs2.

    Prefers an ``mmseqs`` already on PATH; otherwise transparently downloads
    and caches a static build for the current platform on first use (see
    :mod:`candy.clustering.mmseqs2_download`). This is the default clustering
    backend precisely because that auto-download is possible for MMseqs2 but
    not for CD-HIT (source-only, no Windows build).

    .. note::
       This deliberately does *not* use MMseqs2's ``easy-cluster`` convenience
       workflow, and instead runs its constituent steps individually
       (``createdb`` -> ``cluster`` -> ``result2repseq`` -> ``convert2fasta``).
       Three Windows-specific issues were found running the real thing:

       1. ``mmseqs.bat`` always exits 0 regardless of whether the underlying
          command actually succeeded (its final line is a hardcoded
          ``exit /b 0``), so a non-zero return code can't be used to detect
          failure there -- worked around by always checking that the
          expected output file was actually produced.
       2. MMseqs2's clustering workflow runs through a bundled Cygwin/busybox
          POSIX-shell layer internally (see ``mmseqs2_download``), which
          mishandles Windows paths containing spaces (e.g. a project
          directory under "...\\OneDrive - Org\\..."). Avoided by always
          running from a space-free temporary directory with relative
          filenames, regardless of where the real input/output paths live.
       3. ``easy-cluster``'s internal script runs its final DB-to-FASTA
          conversion step (``result2flat``) through that same Cygwin process-
          spawning layer, which was observed to segfault on a real (155
          sequence) clustering run despite every preceding step completing
          successfully. The equivalent public step, ``convert2fasta``, runs
          reliably when invoked directly (bypassing the shell entirely) --
          so only the one step that genuinely needs a POSIX shell (the
          cascaded-clustering algorithm inside ``cluster`` itself) goes
          through ``mmseqs.bat``; everything else uses the plain compiled
          binary directly.
    """

    name = "mmseqs2"

    def cluster(self, input_fasta: Path, output_fasta: Path, config: ClusteringConfig) -> Path:
        shell_binary = resolve_mmseqs2_binary()
        direct_binary = self._direct_binary(shell_binary)
        if platform.system() == "Windows" and shell_binary.lower().endswith(".bat"):
            logger.info(
                "Clustering on Windows uses MMseqs2's mmseqs.bat wrapper, which may ask for "
                "administrator permission once (to install a small POSIX-shell helper it "
                "needs internally). This only happens on the very first clustering run."
            )
        min_seq_id = config.identity_cutoff / 100
        min_coverage = config.mmseqs_min_coverage / 100
        cov_mode = str(config.mmseqs_cov_mode)

        logger.info("Clustering with MMseqs2 at %.0f%% identity.", config.identity_cutoff)
        with tempfile.TemporaryDirectory(prefix="candy_mmseqs2_") as tmp_dir:
            tmp_dir = Path(tmp_dir)
            shutil.copyfile(input_fasta, tmp_dir / "input.fasta")

            run_tool([direct_binary, "createdb", "input.fasta", "db"], cwd=tmp_dir)
            result = run_tool(
                [
                    shell_binary,
                    "cluster", "db", "db_clu", "tmp",
                    "--min-seq-id", f"{min_seq_id}",
                    "-c", f"{min_coverage}",
                    "--cov-mode", cov_mode,
                ],
                cwd=tmp_dir,
            )
            run_tool([direct_binary, "result2repseq", "db", "db_clu", "db_clu_rep"], cwd=tmp_dir)
            run_tool([direct_binary, "convert2fasta", "db_clu_rep", "cluster_rep_seq.fasta"], cwd=tmp_dir)

            representative_sequences = tmp_dir / "cluster_rep_seq.fasta"
            if not representative_sequences.exists():
                raise ExternalToolError(
                    "MMseqs2 clustering reported success but did not produce the expected "
                    f"output ({representative_sequences.name}). Captured output from the "
                    f"clustering step:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
            shutil.copyfile(representative_sequences, output_fasta)

        return output_fasta

    @staticmethod
    def _direct_binary(shell_binary: str) -> str:
        """Resolve the plain compiled ``mmseqs`` binary, bypassing any shell wrapper.

        On Windows, ``resolve_mmseqs2_binary()`` returns ``mmseqs.bat`` (one
        directory above a ``bin/`` folder containing ``mmseqs.exe``); steps
        that don't need a POSIX shell run against that ``.exe`` directly
        instead. Everywhere else, the shell binary already *is* the plain
        binary, so this is a no-op.
        """
        if platform.system() == "Windows" and shell_binary.lower().endswith(".bat"):
            candidate = Path(shell_binary).parent / "bin" / "mmseqs.exe"
            if candidate.is_file():
                return str(candidate)
        return shell_binary
