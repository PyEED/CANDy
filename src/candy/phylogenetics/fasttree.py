from __future__ import annotations

import logging
from pathlib import Path

from candy.external_tools import MissingDependencyError, find_binary, run_tool

logger = logging.getLogger(__name__)

# Different packagers ship this binary under different casings
# (bioconda historically used 'FastTree', some distros use 'fasttree').
_CANDIDATE_NAMES = ["FastTree", "fasttree"]


class FastTreeBuilder:
    name = "fasttree"

    def build_tree(self, alignment_fasta: Path, output_newick: Path) -> Path:
        binary = self._locate_binary()
        logger.info("Building phylogenetic tree with FastTree.")
        run_tool([binary, str(alignment_fasta)], stdout_path=output_newick)
        return output_newick

    def _locate_binary(self) -> str:
        for candidate in _CANDIDATE_NAMES:
            path = find_binary(candidate)
            if path is not None:
                return path
        raise MissingDependencyError(
            f"Required external tool 'FastTree' was not found on PATH "
            f"(tried: {', '.join(_CANDIDATE_NAMES)}). Install it via the bundled conda "
            "environment: `conda env create -f environment.yml && conda activate candy`."
        )
