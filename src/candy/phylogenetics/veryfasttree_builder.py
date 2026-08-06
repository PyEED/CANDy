from __future__ import annotations

import logging
from pathlib import Path

import veryfasttree

logger = logging.getLogger(__name__)

_SIMD_TO_EXT = {"avx512f": "AVX512", "avx2": "AVX2", "sse2": "SSE"}


class VeryFastTreeBuilder:
    """Phylogenetics via VeryFastTree (through the ``veryfasttree`` bindings).

    Runs a bundled, precompiled binary shipped inside the ``veryfasttree``
    wheel -- no external FastTree/VeryFastTree installation needed. This is
    the default, zero-install phylogenetics backend;
    :class:`candy.phylogenetics.fasttree.FastTreeBuilder` remains available
    for anyone who specifically wants the original FastTree binary.

    .. note::
       ``veryfasttree.run()`` defaults to ``ext="AUTO"`` (let the binary
       self-detect vector extensions). During testing, both ``AUTO`` and the
       explicit scalar path ``ext="NONE"`` reliably crashed (access
       violation) on a Windows/AVX2 machine, while explicitly requesting the
       same SIMD tier the package itself already selected for the bundled
       binary (``SSE``/``AVX2``/``AVX512``, matched via ``veryfasttree._simd``)
       ran correctly. This builder always passes that explicit ``ext``
       rather than relying on the library's ``AUTO`` default.
    """

    name = "veryfasttree"

    def build_tree(self, alignment_fasta: Path, output_newick: Path) -> Path:
        ext = _SIMD_TO_EXT.get(getattr(veryfasttree, "_simd", None), "SSE")
        logger.info("Building phylogenetic tree with VeryFastTree (ext=%s).", ext)
        veryfasttree.run(str(alignment_fasta), out=str(output_newick), quiet=True, nopr=True, ext=ext)
        return output_newick
