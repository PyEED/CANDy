from __future__ import annotations

import logging
from pathlib import Path

from Bio import SeqIO
from pyfamsa import Aligner, Sequence

logger = logging.getLogger(__name__)


class FamsaAligner:
    """MSA via FAMSA (through the ``pyfamsa`` bindings).

    Runs in-process (no subprocess, no external binary) -- ``pyfamsa`` ships
    prebuilt wheels for Linux/macOS/Windows, making this the default,
    zero-install alignment backend. :class:`candy.alignment.mafft.MafftAligner`
    remains available for anyone who specifically wants MAFFT.
    """

    name = "famsa"

    def __init__(self, threads: int = 0) -> None:
        # threads=0 lets FAMSA pick a sensible default (all available cores).
        self.threads = threads

    def align(self, input_fasta: Path, output_fasta: Path) -> Path:
        with open(input_fasta) as handle:
            records = list(SeqIO.parse(handle, "fasta"))

        sequences = [Sequence(record.id.encode(), str(record.seq).encode()) for record in records]

        logger.info("Aligning %d sequences with FAMSA.", len(sequences))
        aligner = Aligner(threads=self.threads)
        alignment = aligner.align(sequences)

        with open(output_fasta, "w") as out:
            for gapped in alignment:
                out.write(f">{gapped.id.decode()}\n{gapped.sequence.decode()}\n")

        return output_fasta
