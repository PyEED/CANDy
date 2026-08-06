"""Client for InterPro's MD5 match-lookup and entry-name APIs.

The notebook queried the same match-lookup endpoint twice with two separate,
near-duplicate implementations: once to check which sequences have a UniParc
entry at all (:mod:`candy.uniparc`), and again to fetch full domain hits
(``domain_detection``). Both are consolidated here into a single
:func:`match_lookup`, which both call sites now share.
"""

from __future__ import annotations

import hashlib
import logging
import time
import urllib.error
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from urllib.parse import urlencode
from urllib.request import urlopen

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

MATCH_LOOKUP_URL = "https://www.ebi.ac.uk/interpro/match-lookup/matches"
ENTRY_API_URL = "https://www.ebi.ac.uk/interpro/api/entry/"
_MD5_BATCH_SIZE = 5000

# Maps InterPro's member-database labels to the URL path segment used by the
# entry API. Databases not in this map (TMHMM, MOBIDB_LITE, PHOBIUS, COILS,
# FUNFAM, ...) don't have resolvable "names" via this API; their raw domain
# code is used as the name instead, same as the original notebook.
_DATABASE_TO_ENTRY_PATH = {
    "GENE3D": "cathgene3d",
    "CDD": "cdd",
    "HAMAP": "hamap",
    "PANTHER": "panther",
    "PFAM": "pfam",
    "PIRSF": "pirsf",
    "PRINTS": "prints",
    "PROSITE_PROFILES": "profile",
    "PROSITE_PATTERNS": "prosite",
    "SFLD": "sfld",
    "SMART": "smart",
    "SUPERFAMILY": "ssf",
    "TIGRFAMS": "tigrfams",
    "NCBIfam": "ncbifam",
}


@dataclass(frozen=True)
class DomainHit:
    database: str
    domain_code: str
    start: int
    end: int


@dataclass
class ProteinMatch:
    protein_id: str
    hits: list[DomainHit] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedHit:
    database: str
    name: str
    start: int
    end: int


def _md5_of(sequence: str) -> str:
    return hashlib.md5(sequence.encode()).hexdigest().upper()


def _batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _query_md5_batch(md5_list: Sequence[str], max_retries: int = 10, retry_delay: float = 5.0) -> ET.Element:
    data = urlencode({"md5": list(md5_list)}, doseq=True).encode("ascii")

    attempts = 0
    while True:
        try:
            with urlopen(MATCH_LOOKUP_URL, data) as response:
                payload = response.read().decode("utf-8")
            return ET.fromstring(payload)
        except urllib.error.HTTPError:
            attempts += 1
            if attempts >= max_retries:
                raise
            logger.info("InterPro match-lookup busy, retrying in %.0fs.", retry_delay)
            time.sleep(retry_delay)


def _parse_hits(hit_text: str) -> DomainHit:
    columns = hit_text.split(",")
    database = columns[0]
    domain_code = columns[2]
    # Discontinuous domains report multiple ';'-separated fragments; only the
    # first fragment's boundaries are used (matching the published tool).
    first_fragment = columns[6].split(";")[0]
    start, end, _ = first_fragment.split("-")
    return DomainHit(database, domain_code, int(start), int(end))


def match_lookup(proteins: Mapping[str, str]) -> tuple[dict[str, ProteinMatch], list[str]]:
    """Query InterPro's MD5 match-lookup for every sequence in ``proteins``.

    ``proteins`` maps sequence ID -> amino-acid sequence. Sequences are
    queried by MD5 hash, so IDs sharing an identical sequence share a single
    lookup and all receive the same result. Returns ``(matches, unmatched_ids)``.
    """
    sequence_to_ids: dict[str, list[str]] = {}
    for identifier, sequence in proteins.items():
        sequence_to_ids.setdefault(sequence, []).append(identifier)

    md5_to_sequence = {_md5_of(sequence): sequence for sequence in sequence_to_ids}
    matches: dict[str, ProteinMatch] = {}
    matched_md5s: set[str] = set()

    for batch in _batched(list(md5_to_sequence.keys()), _MD5_BATCH_SIZE):
        root = _query_md5_batch(batch)
        for match_el in root.findall(".//match"):
            md5 = match_el.find("proteinMD5").text
            sequence = md5_to_sequence[md5]
            hits = [_parse_hits(hit_el.text) for hit_el in match_el.findall("hit")]

            for identifier in sequence_to_ids[sequence]:
                matches[identifier] = ProteinMatch(identifier, hits)
            matched_md5s.add(md5)

    unmatched_ids = [
        identifier
        for md5, sequence in md5_to_sequence.items()
        if md5 not in matched_md5s
        for identifier in sequence_to_ids[sequence]
    ]

    return matches, unmatched_ids


def detect_domains(proteins: Mapping[str, str]) -> tuple[dict[str, ProteinMatch], list[str]]:
    """Query InterPro for domain hits on every sequence in ``proteins``."""
    matches, unmatched = match_lookup(proteins)
    for protein_id in unmatched:
        logger.warning("No domains found for %s; try running InterProScan directly.", protein_id)
    return matches, unmatched


def _fetch_entry_name(
    database: str, domain_code: str, session: requests.Session, max_retries: int = 3
) -> str | None:
    entry_path = _DATABASE_TO_ENTRY_PATH.get(database)
    if entry_path is None:
        return None

    url = f"{ENTRY_API_URL}{entry_path}/{domain_code}"
    attempts = 0
    while True:
        try:
            response = session.get(url, headers={"Accept": "application/json"}, timeout=30)
        except requests.RequestException:
            attempts += 1
            if attempts > max_retries:
                raise
            time.sleep(61)
            continue

        if response.status_code == 408:
            time.sleep(61)
            continue
        if response.status_code in (204, 404):
            logger.warning("No InterPro entry data for %s/%s.", database, domain_code)
            return None
        if not response.ok:
            attempts += 1
            if attempts > max_retries:
                response.raise_for_status()
            time.sleep(61)
            continue

        return response.json()["metadata"]["name"]["name"]


def resolve_domain_names(
    matches: Mapping[str, ProteinMatch], session: requests.Session | None = None
) -> dict[str, list[ResolvedHit]]:
    """Resolve each hit's InterPro domain code into a human-readable name.

    Names are cached per (database, code) pair for the whole call, since the
    same domain accession is typically hit across many proteins.
    """
    session = session or requests.Session()
    name_cache: dict[tuple[str, str], str] = {}
    resolved: dict[str, list[ResolvedHit]] = {}

    for protein_id, match in tqdm(matches.items(), total=len(matches), desc="Resolving domain names"):
        resolved_hits = []
        for hit in match.hits:
            cache_key = (hit.database, hit.domain_code)
            if cache_key not in name_cache:
                name = _fetch_entry_name(hit.database, hit.domain_code, session)
                name_cache[cache_key] = name if name is not None else hit.domain_code
                time.sleep(1)  # stay polite to the API, same pacing as the original notebook
            resolved_hits.append(ResolvedHit(hit.database, name_cache[cache_key], hit.start, hit.end))
        resolved[protein_id] = resolved_hits

    return resolved


def build_domain_tables(
    resolved: Mapping[str, Sequence[ResolvedHit]],
) -> tuple[dict[str, list[list[int]]], dict[str, list[list[str]]], dict[str, dict[str, str]]]:
    """Convert resolved hits into the (position, name, database) tables :mod:`candy.domains` expects."""
    position_dict: dict[str, list[list[int]]] = {}
    domain_name_list: dict[str, list[list[str]]] = {}
    name_to_database: dict[str, dict[str, str]] = {}

    for protein_id, hits in resolved.items():
        position_dict[protein_id] = [[hit.start, hit.end] for hit in hits]
        domain_name_list[protein_id] = [[hit.database, hit.name] for hit in hits]
        name_to_database[protein_id] = {hit.name: hit.database for hit in hits}

    return position_dict, domain_name_list, name_to_database
