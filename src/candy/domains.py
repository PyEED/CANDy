"""Resolve overlapping/duplicate domain annotations into a clean architecture.

InterPro aggregates hits from many member databases (Pfam, SMART, CDD, ...),
so the same physical domain is usually reported multiple times, at slightly
different boundaries, by different databases. This module groups positions
that overlap "enough" to be the same domain, then picks one representative
hit per group according to a configurable database-preference ranking.

Ported from the notebook's ``overlap`` / ``extract_overlap`` / ``clean_domains``
functions with the same resolution semantics (including its pre-existing
asymmetry: the single-hit branch additionally excludes the FUNFAM database
and does not length-filter, while the ambiguous/grouped branch does not
exclude FUNFAM but does length-filter). That asymmetry is preserved rather
than "fixed" here to keep behaviour identical to the published tool.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence

Position = list[int]  # [start, end], 1 excludes 0-based confusion by matching notebook convention
NamedDomain = tuple[Position, str]  # ([start, end], domain_name)

_EXCLUDED_DOMAIN_NAMES = {
    "None",
    "Prokaryotic membrane lipoprotein lipid attachment site profile",
}
_EXCLUDED_DATABASES_SINGLE = {"TMHMM", "MOBIDB_LITE", "PHOBIUS", "FUNFAM"}
_EXCLUDED_DATABASES_GROUPED = {"TMHMM", "MOBIDB_LITE", "PHOBIUS"}


def positions_overlap(a: Position, b: Position, overlap_fraction: float) -> bool:
    """True if two [start, end] positions overlap by more than ``overlap_fraction``."""
    a, b = sorted([a, b])
    x1, y1 = a
    x2, y2 = b
    length1 = y1 - x1
    length2 = y2 - x2

    if x2 <= y1 <= y2:
        if x1 == y1 or x2 == y2:
            identity = 1.0
        else:
            over = y1 - x2
            identity = max(over / length1, over / length2)
    elif x1 <= x2 and y2 <= y1:
        # b falls entirely within a
        identity = 100.0
    else:
        identity = 0.0

    return identity > overlap_fraction


def group_overlapping(
    positions: Sequence[Position], overlap_fraction: float
) -> list[Position | list[Position]]:
    """Group positions considered to represent the same domain.

    Returns a list where each element is either a single ``[start, end]``
    (unambiguous) or a list of ``[start, end]`` pairs considered to be the
    same domain reported at slightly different boundaries.
    """
    ordered = sorted(positions, key=lambda p: (p[0], p[1]))
    grouped: list[Position | list[Position]] = []
    pending: list[Position] = []

    i = 0
    while i < len(ordered):
        if i == len(ordered) - 1:
            if pending:
                grouped.append(_dedupe(pending))
            else:
                grouped.append(ordered[i])
            break

        if positions_overlap(ordered[i], ordered[i + 1], overlap_fraction):
            pending += [ordered[i], ordered[i + 1]]
            i += 1
        else:
            if pending:
                grouped.append(_dedupe(pending))
                pending = []
            else:
                grouped.append(ordered[i])
            i += 1

    return grouped


def _dedupe(positions: list[Position]) -> list[Position]:
    positions = sorted(positions)
    return [p for p, _ in itertools.groupby(positions)]


def map_positions_to_names(
    position_dict: Mapping[str, Sequence[Position]],
    domain_name_list: Mapping[str, Sequence[Sequence[str]]],
) -> dict[str, dict[str, str]]:
    """Re-key each protein's raw InterPro hits from position -> resolved domain name.

    ``domain_name_list[protein_id]`` is a list of ``[database, name]`` pairs in
    the same order as ``position_dict[protein_id]`` (both are built hit-by-hit
    from the same InterPro response in :mod:`candy.interpro`).

    .. note::
       The output is keyed by ``str(position)``, so when two different
       databases report the exact same ``[start, end]`` span (which happens
       routinely, e.g. Pfam and SMART agreeing on boundaries), only one name
       can survive per position either way. The original notebook paired
       these two parallel lists via ``value.index(positions)`` (a lookup *by
       value*), which for duplicate positions always resolves to whichever
       hit happened to occur first in the raw InterPro response -- an
       accident of API ordering, unrelated to the database-preference
       ranking applied later. This version pairs by loop index instead (the
       two lists are built hit-by-hit in lockstep in ``interpro.py``), so for
       duplicate positions the last hit wins, same as any normal dict
       overwrite -- still arbitrary between the tied candidates, but no
       longer silently locked to index 0 regardless of which hit is current.
    """
    result: dict[str, dict[str, str]] = {}
    for protein_id, positions in position_dict.items():
        names_for_protein = domain_name_list[protein_id]
        result[protein_id] = {
            str(position): names_for_protein[index][1] for index, position in enumerate(positions)
        }
    return result


def clean_domains(
    position_dict: Mapping[str, Sequence[Position]],
    position_to_name: Mapping[str, Mapping[str, str]],
    name_to_database: Mapping[str, Mapping[str, str]],
    database_preference: Sequence[str],
    overlap_fraction: float,
    max_domain_length: int,
) -> dict[str, list[NamedDomain]]:
    """Resolve each protein's raw domain hits into a clean, non-overlapping architecture."""
    final: dict[str, list[NamedDomain]] = {}

    for protein_id, raw_positions in position_dict.items():
        positions = list(raw_positions)
        previous_length = -1
        resolved: list[NamedDomain] = []

        while previous_length != len(positions):
            previous_length = len(positions)
            groups = group_overlapping(positions, overlap_fraction)

            resolved = []
            next_positions: list[Position] = []

            for group in groups:
                if _is_single_position(group):
                    resolved_domain = _resolve_single(
                        group, protein_id, position_to_name, name_to_database
                    )
                    if resolved_domain is not None:
                        resolved.append(resolved_domain)
                        next_positions.append(group)
                else:
                    resolved_domain = _resolve_grouped(
                        group,
                        protein_id,
                        position_to_name,
                        name_to_database,
                        database_preference,
                        max_domain_length,
                    )
                    if resolved_domain is not None:
                        resolved.append(resolved_domain)
                        next_positions.append(resolved_domain[0])

            positions = next_positions

        final[protein_id] = resolved

    return final


def _is_single_position(group: Position | list[Position]) -> bool:
    return all(isinstance(x, int) for x in group)


def _resolve_single(
    position: Position,
    protein_id: str,
    position_to_name: Mapping[str, Mapping[str, str]],
    name_to_database: Mapping[str, Mapping[str, str]],
) -> NamedDomain | None:
    name = position_to_name[protein_id][str(position)]
    database = name_to_database[protein_id][name]

    if (
        name in _EXCLUDED_DOMAIN_NAMES
        or database in _EXCLUDED_DATABASES_SINGLE
        or "SIGNAL" in database.upper()
    ):
        return None
    return position, name


def _resolve_grouped(
    group: list[Position],
    protein_id: str,
    position_to_name: Mapping[str, Mapping[str, str]],
    name_to_database: Mapping[str, Mapping[str, str]],
    database_preference: Sequence[str],
    max_domain_length: int,
) -> NamedDomain | None:
    candidates: dict[str, str] = {}  # name -> database
    candidate_positions: dict[str, Position] = {}  # name -> position

    for position in group:
        start, end = position
        length = end - start
        name = position_to_name[protein_id][str(position)]
        database = name_to_database[protein_id][name]

        if (
            name in _EXCLUDED_DOMAIN_NAMES
            or database in _EXCLUDED_DATABASES_GROUPED
            or "SIGNAL" in database.upper()
            or "SIGNAL" in name.upper()
            or not (10 <= length <= max_domain_length)
        ):
            continue

        candidates[name] = database
        candidate_positions[name] = position

    if not candidates:
        return None

    ranked: dict[int, str] = {}
    for name, database in candidates.items():
        if database in database_preference:
            ranked[database_preference.index(database)] = name

    if ranked:
        chosen_name = ranked[min(ranked)]
    else:
        chosen_name = next(iter(candidate_positions))

    return candidate_positions[chosen_name], chosen_name
