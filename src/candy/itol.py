"""Generate iTOL annotation files: domain architectures and characterized-enzyme styling.

The notebook used ``ete3`` to load the phylogenetic tree in both annotation
functions. In ``domain_vis`` (here: :func:`build_domain_annotation`) the tree
was loaded into a ``Tree`` object that was then never referenced again --
dead code, dropped entirely, so this function no longer needs a tree at all.
In ``characterized_labeling`` (here: :func:`build_characterized_style_annotation`)
the tree genuinely is used, to find which leaf names correspond to a given
characterized enzyme's accession; that's done here with ``Bio.Phylo``
instead, avoiding the largely-unmaintained ``ete3`` dependency entirely.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from Bio import Phylo

logger = logging.getLogger(__name__)

_DOMAIN_SHAPES = ["RE", "EL", "HH", "HV", "DI", "TR", "TL", "PL", "PR", "PU", "PD", "OC"]
_DOMAIN_COLORS = [
    "#BF0F0F", "#217D3B", "#23A5D9", "#F2C641", "#A276DB", "#D9560B", "#F294B6", "#1DF2DD",
    "#E80C7A", "#A6A6A6", "#000000", "#352310", "#4F0B79", "#CE07F3", "#12FC4F", "#79D626",
    "#4C45FE", "#DDFBE6", "#0842AF", "#83634C", "#82D4FF",
]
_CHARACTERIZED_COLORS = [
    "#BF0F0F", "#217D3B", "#23A5D9", "#F2C641", "#A276DB", "#D9560B", "#F294B6", "#1DF2DD",
    "#E80C7A", "#A6A6A6", "#352310", "#4F0B79", "#CE07F3", "#12FC4F", "#79D626", "#4C45FE",
    "#DDFBE6", "#0842AF", "#83634C", "#82D4FF", "#FF5733", "#33FF57", "#5733FF", "#FFD700",
    "#00BFFF", "#FF69B4", "#8A2BE2", "#7FFF00", "#DC143C", "#20B2AA", "#008080", "#FF4500",
    "#DA70D6", "#4682B4", "#D2691E", "#9ACD32", "#00CED1", "#FF1493", "#1E90FF", "#B22222",
    "#FF6347", "#00FF7F", "#8B4513", "#2E8B57", "#6A5ACD", "#FFDAB9", "#7B68EE", "#32CD32",
    "#FF00FF", "#FFDEAD",
]


def _umbrella_name(raw_name: str, curated_domains: Mapping[str, Sequence[str]]) -> str:
    for umbrella, raw_names in curated_domains.items():
        if raw_name in raw_names:
            return umbrella
    return raw_name


def _protein_id_for_matching(record_id: str) -> str:
    """Recover the bare protein ID from a '{accession}_{organism}_{taxcode}'-style header.

    Ported as-is from the notebook's ``domain_vis``: IDs whose first ``_``
    occurs at index < 2 are used verbatim (covers custom-FASTA-mode headers,
    which don't follow the accession/organism/taxcode convention at all),
    otherwise the leading accession segment (or, when the accession itself
    contains a very short prefix before an underscore, its first two
    underscore-separated segments) is used.
    """
    first_underscore = record_id.find("_")
    if first_underscore > 2:
        return record_id.split("_")[0]
    if first_underscore < 2:
        return record_id
    parts = record_id.split("_")
    return f"{parts[0]}_{parts[1]}"


def build_domain_annotation(
    jobname: str,
    domain_architecture: Mapping[str, Sequence[tuple[list[int], str]]],
    curated_domains: Mapping[str, Sequence[str]],
    protein_records: Sequence,
) -> str:
    """Build an iTOL DATASET_DOMAINS annotation file mapping each leaf to its domain motifs."""
    shape_dict: dict[str, str] = {}
    color_dict: dict[str, str] = {}
    data = ""

    for protein_id, domains in domain_architecture.items():
        motif = ""
        for position, raw_name in domains:
            name = _umbrella_name(raw_name, curated_domains)
            if name not in shape_dict:
                shape_dict[name] = _DOMAIN_SHAPES[len(shape_dict) % len(_DOMAIN_SHAPES)]
            if name not in color_dict:
                color_dict[name] = _DOMAIN_COLORS[len(color_dict) % len(_DOMAIN_COLORS)]
            start, end = position
            motif += f"\t{shape_dict[name]}|{start}|{end}|{color_dict[name]}|{name}"

        for record in protein_records:
            if _protein_id_for_matching(record.id) == protein_id:
                data += f"{record.id}\t{len(record.seq)}{motif}\n"

    header = (
        "DATASET_DOMAINS\n"
        "SEPARATOR TAB\n"
        "DATASET_LABEL\tSMART architecture export\n"
        "COLOR\t#0000ff\n"
        "BORDER_WIDTH\t1\n"
        "GRADIENT_FILL\t1\n"
        "SHOW_DOMAIN_LABELS\t1\n"
        f"LEGEND_TITLE\t {jobname} domains\n"
    )
    legend = (
        "LEGEND_LABELS\t\t" + "\t".join(shape_dict.keys()) + "\n"
        "LEGEND_SHAPES\t\t" + "\t".join(shape_dict.values()) + "\n"
        "LEGEND_COLORS\t\t" + "\t".join(color_dict[name] for name in shape_dict) + "\n"
    )
    return header + legend + "DATA\n" + data


def build_characterized_style_annotation(
    tree_path: str | Path,
    characterized_ids: Sequence[str],
    ec_numbers: Mapping[str, str],
    legend_title: str,
) -> str:
    """Build an iTOL DATASET_STYLE file coloring characterized-enzyme leaf labels by EC number.

    .. note::
       The notebook only assigned an ``ecnumber``/color for IDs present in
       ``ec_numbers``, but then unconditionally used that (possibly stale,
       possibly unset) ``ecnumber`` variable to style *every* ID's matching
       leaf -- so a characterized enzyme with no known EC number got styled
       with whichever EC color happened to be left over from the previous
       one in the loop (or crashed with an ``UnboundLocalError`` if it was
       first). Here, only IDs with a resolved EC number are styled.
    """
    tree = Phylo.read(str(tree_path), "newick")
    leaf_names = [leaf.name for leaf in tree.get_terminals()]

    color_dict: dict[str, str] = {}
    data = ""

    for genbank_id in characterized_ids:
        if genbank_id not in ec_numbers:
            continue

        ec_values = ec_numbers[genbank_id].split(" ")
        ec_number = ec_values[0]
        if len(ec_values) > 1:
            logger.info(
                "%s has multiple EC numbers: %s. EC number %s will be used for annotation.",
                genbank_id, ec_numbers[genbank_id], ec_number,
            )
        if ec_number not in color_dict:
            color_dict[ec_number] = _CHARACTERIZED_COLORS[len(color_dict) % len(_CHARACTERIZED_COLORS)]

        for leaf_name in leaf_names:
            if genbank_id in leaf_name:
                data += f"{leaf_name} label node {color_dict[ec_number]} 1 bold\n"

    header = (
        "DATASET_STYLE\n"
        "SEPARATOR SPACE\n"
        "DATASET_LABEL Characterized enzymes\n"
        "COLOR #0000ff\n"
        "BORDER_WIDTH 1\n"
        "GRADIENT_FILL 1\n"
        "SHOW_DOMAIN_LABELS 1\n"
        f"LEGEND_TITLE {legend_title} characterized enzymes\n"
    )
    # All legend swatches intentionally share shape code "1" (a single
    # uniform marker), same as the published notebook.
    legend = (
        "LEGEND_LABELS " + " ".join(color_dict.keys()) + "\n"
        "LEGEND_SHAPES " + " ".join("1" for _ in color_dict) + "\n"
        "LEGEND_COLORS " + " ".join(color_dict.values()) + "\n"
    )
    return header + legend + "DATA\n" + data
