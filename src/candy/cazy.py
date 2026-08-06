"""Retrieve CAZy family sequences and characterized-enzyme data from CAZy/NCBI.

The notebook fetched sequences one GenBank ID at a time via
``Entrez.efetch`` in a tight loop, which is slow and easy to get
rate-limited on for large families. Entrez supports batched fetches (a
comma-separated ``id`` list per request), used here instead; the resulting
FASTA output is identical, just retrieved in ~200-id chunks rather than
one request per sequence.
"""

from __future__ import annotations

import http.client
import io
import logging
import time
from collections.abc import Iterable, Sequence
from urllib.error import URLError

import pandas as pd
import requests
from Bio import Entrez

from candy.config import Taxonomy

logger = logging.getLogger(__name__)

CAZY_FAMILY_URL = "https://www.cazy.org/IMG/cazy_data/{family}.txt"
CAZY_CHARACTERIZED_URL = "https://www.cazy.org/{family}_characterized.html"

_TAXONOMY_NAME_TO_CODE = {
    "BACTERIA": "B",
    "EUKARYOTA": "E",
    "ARCHAEA": "A",
    "VIRUSES": "V",
    "UNCLASSIFIED": "U",
}

_ENTREZ_BATCH_SIZE = 200
_ENTREZ_MAX_RETRIES = 10
_ENTREZ_RETRY_DELAY = 3.0

# urllib.error.HTTPError is a URLError subclass, so this also covers plain
# HTTP error statuses. http.client.HTTPException covers things like
# IncompleteRead (the connection dropping mid-response, which NCBI's Entrez
# endpoints hit occasionally on large batched fetches) and BadStatusLine;
# ConnectionError/TimeoutError cover socket-level drops and timeouts.
_RETRYABLE_NETWORK_ERRORS = (URLError, http.client.HTTPException, ConnectionError, TimeoutError)


def _batched(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_family_page(family: str, max_retries: int = 5, retry_delay: float = 5.0) -> str:
    """Download the raw CAZy family data page (tab-separated GenBank ID listing)."""
    url = CAZY_FAMILY_URL.format(family=family)
    logger.info("Retrieving data from %s", url)

    attempts = 0
    while True:
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            attempts += 1
            if attempts >= max_retries:
                raise
            logger.info("Network error retrieving CAZy data (%s); retrying in %.0fs.", exc, retry_delay)
            time.sleep(retry_delay)


def parse_family_table(raw_text: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Parse a CAZy family page into (table, {genbank_id: taxonomy_code})."""
    df = pd.read_table(io.StringIO(raw_text), engine="python", header=None)

    taxonomy_dict: dict[str, str] = {}
    for _, row in df.iterrows():
        kingdom = row[1].upper()
        genbank_id = row[3]
        taxonomy_dict[genbank_id] = _TAXONOMY_NAME_TO_CODE[kingdom]

    return df, taxonomy_dict


def extract_ncbi_ids(df: pd.DataFrame, taxonomy_dict: dict[str, str], taxonomy: Taxonomy) -> list[str]:
    """Return GenBank IDs sourced from NCBI (excludes JGI-only entries), filtered by taxonomy."""
    is_ncbi = df.iloc[:, -1].astype(str) == "ncbi"
    ids = df.iloc[:, -2][is_ncbi].tolist()

    if taxonomy == Taxonomy.ALL:
        return ids
    return [i for i in ids if taxonomy_dict.get(i) == taxonomy.code]


def fetch_sequences_fasta(ids: Sequence[str], email: str, batch_size: int = _ENTREZ_BATCH_SIZE) -> str:
    """Batch-fetch protein FASTA sequences from NCBI for a list of GenBank IDs."""
    Entrez.email = email
    chunks: list[str] = []

    total_batches = (len(ids) + batch_size - 1) // batch_size or 1
    for batch in _batched(ids, batch_size):
        attempts = 0
        while True:
            try:
                with Entrez.efetch(db="protein", id=",".join(batch), rettype="fasta", retmode="text") as handle:
                    chunks.append(handle.read())
                break
            except _RETRYABLE_NETWORK_ERRORS as exc:
                attempts += 1
                if attempts >= _ENTREZ_MAX_RETRIES:
                    logger.warning(
                        "Giving up on a batch of %d IDs after repeated network errors (%s).", len(batch), exc
                    )
                    break
                logger.info("Network error fetching a sequence batch (%s); retrying in %.0fs.", exc, _ENTREZ_RETRY_DELAY)
                time.sleep(_ENTREZ_RETRY_DELAY)
        logger.info("Fetched %d/%d sequence batches.", len(chunks), total_batches)

    return "".join(chunks)


def extract_family_sequences(family: str, taxonomy: Taxonomy, email: str) -> tuple[str, dict[str, str]]:
    """End-to-end: fetch a CAZy family page and the protein sequences it lists.

    Returns (fasta_text, taxonomy_dict). Raises ``ValueError`` if no
    sequences exist for the requested taxonomy subset.
    """
    raw_text = fetch_family_page(family)
    df, taxonomy_dict = parse_family_table(raw_text)

    if taxonomy != Taxonomy.ALL and taxonomy.code not in taxonomy_dict.values():
        raise ValueError(
            f"No sequences belonging to {taxonomy.value} were found for family {family}."
        )

    ids = extract_ncbi_ids(df, taxonomy_dict, taxonomy)
    logger.info("Extracting %d protein sequences from NCBI.", len(ids))
    fasta_text = fetch_sequences_fasta(ids, email)

    return fasta_text, taxonomy_dict


def fetch_characterized_page(family: str, max_retries: int = 10, retry_delay: float = 5.0) -> list[pd.DataFrame]:
    """Download and parse CAZy's '{family}_characterized.html' page.

    CAZy's servers frequently return 429s under load, so this retries.
    """
    url = CAZY_CHARACTERIZED_URL.format(family=family)
    logger.info("Retrieving data from %s", url)

    attempts = 0
    while True:
        try:
            return pd.read_html(url)
        except _RETRYABLE_NETWORK_ERRORS as exc:
            attempts += 1
            if attempts >= max_retries:
                raise
            logger.info("Network error retrieving CAZy data (%s); retrying in %.0fs.", exc, retry_delay)
            time.sleep(retry_delay)


def extract_characterized_ids(
    tables: list[pd.DataFrame],
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Parse the characterized-enzyme table into (genbank_ids, {id: taxonomy_code}, {id: ec_number}).

    Column 4 is the GenBank identifier, column 1 is the EC number.
    """
    activity_table = tables[1]

    activity_dict: dict[str, str] = {}
    for i in range(len(activity_table)):
        identifier = str(activity_table[4].loc[i]).split(" ")[0]
        if "." in identifier:
            activity_dict[identifier] = activity_table[1].loc[i]

    id_series = tables[1][4].drop_duplicates()

    taxonomy_dict: dict[str, str] = {}
    ids: list[str] = []
    current_taxonomy = ""
    taxonomy_headers = {"Archaea": "A", "Bacteria": "B", "Eukaryota": "E", "Viruses": "V", "Unclassified": "U"}

    for raw_id in id_series:
        entry = str(raw_id)
        if entry in taxonomy_headers:
            current_taxonomy = taxonomy_headers[entry]
            continue

        dot_position = entry.find(".")
        if dot_position == -1:
            continue

        genbank_id = entry[: dot_position + 2]
        if genbank_id not in ids:
            ids.append(genbank_id)
            taxonomy_dict[genbank_id] = current_taxonomy

    return ids, taxonomy_dict, activity_dict


def fetch_characterized_sequences(
    ids: Sequence[str], taxonomy_dict: dict[str, str], taxonomy: Taxonomy, email: str
) -> str:
    """Fetch characterized-enzyme FASTA sequences, annotated with organism + taxonomy code."""
    Entrez.email = email
    filtered_ids = [i for i in ids if taxonomy == Taxonomy.ALL or taxonomy_dict.get(i) == taxonomy.code]

    output = ""
    for genbank_id in filtered_ids:
        text = None
        attempts = 0
        while attempts < _ENTREZ_MAX_RETRIES:
            try:
                with Entrez.efetch(db="protein", id=genbank_id, rettype="fasta", retmode="text") as handle:
                    text = handle.read()
                break
            except _RETRYABLE_NETWORK_ERRORS as exc:
                attempts += 1
                if attempts >= _ENTREZ_MAX_RETRIES:
                    logger.warning(
                        "Giving up on characterized sequence %s after repeated network errors (%s).",
                        genbank_id, exc,
                    )
                    break
                time.sleep(_ENTREZ_RETRY_DELAY)

        if text is None:
            continue

        from Bio import SeqIO

        record = next(SeqIO.parse(io.StringIO(text), "fasta"), None)
        if record is None:
            logger.warning("Could not parse characterized sequence %s.", genbank_id)
            continue

        # The notebook computed this slice index from str(seq_record) (the
        # multi-line repr, not the id itself), via `.id[0:str(seq_record).find('.')+1]`.
        # That offset always overshoots the id's real length, so the slice
        # was a no-op in every realistic case -- it just returns the full id.
        accession = record.id
        organism = record.description[record.description.find("[") + 1 : record.description.find("]")]
        header = f">{accession} {organism}_{taxonomy_dict.get(genbank_id, '')}".replace(" ", "_")
        output += f"{header}\n{record.seq}\n"

    return output
