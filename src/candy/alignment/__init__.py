"""Pluggable multiple-sequence-alignment backends."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AlignmentTool(Protocol):
    name: str

    def align(self, input_fasta: Path, output_fasta: Path) -> Path:
        """Align sequences in ``input_fasta``, writing the alignment to ``output_fasta``."""
        ...


def get_alignment_tool(name: str) -> AlignmentTool:
    if name == "mafft":
        from candy.alignment.mafft import MafftAligner

        return MafftAligner()
    raise ValueError(f"Unknown alignment tool: {name}")
