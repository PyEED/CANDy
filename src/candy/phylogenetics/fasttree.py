from __future__ import annotations

import logging
from pathlib import Path

from candy.external_tools import run_tool
from candy.phylogenetics.fasttree_download import resolve_fasttree_binary

logger = logging.getLogger(__name__)


class FastTreeBuilder:
    """Phylogenetics via FastTree.

    Prefers a ``FastTree``/``fasttree`` already on PATH (e.g. from the
    bundled conda environment); otherwise transparently downloads a
    precompiled binary (Linux/Windows) or compiles one from source
    (macOS, which has no precompiled binary upstream) and caches it -- see
    :mod:`candy.phylogenetics.fasttree_download`.
    """

    name = "fasttree"

    def build_tree(self, alignment_fasta: Path, output_newick: Path) -> Path:
        binary = resolve_fasttree_binary()
        logger.info("Building phylogenetic tree with FastTree.")
        run_tool([binary, str(alignment_fasta)], stdout_path=output_newick)
        return output_newick
