from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from candy.database import (
    DomainAssemblyRow,
    DomainCurationRow,
    create_database,
    populate_database,
    read_protein_sequences,
)


def make_record(id_, seq="MKV"):
    return SeqRecord(Seq(seq), id=id_)


def test_populate_and_read_cazy_mode(tmp_path):
    engine = create_database(tmp_path / "test.db")

    records = [make_record("P1_Escherichia_coli_B")]
    domain_architecture = {"P1": [([1, 100], "Catalytic domain raw name")]}
    domain_to_database = {"P1": {"Catalytic domain raw name": "SMART"}}
    curated_domains = {"Catalytic domain": ["Catalytic domain raw name"]}

    populate_database(
        engine,
        records,
        characterized_ids={"P1"},
        domain_architecture=domain_architecture,
        domain_to_database=domain_to_database,
        curated_domains=curated_domains,
        is_cazy_query=True,
    )

    rows = read_protein_sequences(engine)
    assert len(rows) == 1
    row = rows[0]
    assert row.protein_sequence_id == "P1"
    assert row.taxonomy == "Bacteria"  # not the organism name -- this was the swapped-column bug
    assert row.organism_name == "Escherichia coli"
    assert row.characterized == "C"
    assert row.domain_architecture == "Catalytic domain"
    assert row.domain_locations == "[1, 100]"
    assert row.domain_databases == "SMART"


def test_populate_database_custom_fasta_mode_uses_raw_id(tmp_path):
    engine = create_database(tmp_path / "test2.db")
    records = [make_record("my_custom_header")]

    populate_database(
        engine,
        records,
        characterized_ids={},
        domain_architecture={},
        domain_to_database={},
        curated_domains={},
        is_cazy_query=False,
    )

    rows = read_protein_sequences(engine)
    assert rows[0].protein_sequence_id == "my_custom_header"
    assert rows[0].taxonomy == ""
    assert rows[0].organism_name == ""


def test_populate_database_skips_duplicate_ids(tmp_path, caplog):
    engine = create_database(tmp_path / "test3.db")
    records = [make_record("dup"), make_record("dup")]

    populate_database(
        engine,
        records,
        characterized_ids={},
        domain_architecture={},
        domain_to_database={},
        curated_domains={},
        is_cazy_query=False,
    )

    rows = read_protein_sequences(engine)
    assert len(rows) == 1


def test_populate_database_writes_assembly_and_curation_tables(tmp_path):
    from sqlalchemy.orm import Session

    engine = create_database(tmp_path / "test4.db")
    records = [make_record("P1_Homo_sapiens_E")]
    domain_architecture = {"P1": [([1, 50], "raw")]}
    domain_to_database = {"P1": {"raw": "PFAM"}}
    curated_domains = {"Umbrella": ["raw"]}

    populate_database(
        engine,
        records,
        characterized_ids={},
        domain_architecture=domain_architecture,
        domain_to_database=domain_to_database,
        curated_domains=curated_domains,
        is_cazy_query=True,
    )

    with Session(engine) as session:
        assemblies = session.query(DomainAssemblyRow).all()
        curation = session.query(DomainCurationRow).all()

    assert assemblies[0].protein_domain == "Umbrella"
    assert assemblies[0].protein_sequence_ids == "P1"
    assert curation[0].domain_name == "Umbrella"
    assert curation[0].synonymous_domain_names == "raw"
