from unittest.mock import patch

from candy.interpro import (
    DomainHit,
    ProteinMatch,
    ResolvedHit,
    _parse_hits,
    build_domain_tables,
    match_lookup,
)

SAMPLE_MATCH_XML = """<?xml version="1.0"?>
<response>
  <results>
    <match>
      <proteinMD5>{md5}</proteinMD5>
      <hit>PFAM,domain,PF00128,,,,1-100-Y</hit>
    </match>
  </results>
</response>"""


def test_parse_hits_uses_first_fragment_only():
    # database, ?, domain_code, ?, ?, ?, fragments
    hit_text = "PFAM,domain,PF00128,X,Y,Z,1-100-Y;150-200-Y"
    hit = _parse_hits(hit_text)
    assert hit == DomainHit(database="PFAM", domain_code="PF00128", start=1, end=100)


def test_build_domain_tables_shapes_match_domains_module_expectations():
    resolved = {
        "P1": [
            ResolvedHit(database="SMART", name="Catalytic domain", start=1, end=100),
            ResolvedHit(database="PFAM", name="CBM", start=150, end=300),
        ]
    }

    position_dict, domain_name_list, name_to_database = build_domain_tables(resolved)

    assert position_dict == {"P1": [[1, 100], [150, 300]]}
    assert domain_name_list == {"P1": [["SMART", "Catalytic domain"], ["PFAM", "CBM"]]}
    assert name_to_database == {"P1": {"Catalytic domain": "SMART", "CBM": "PFAM"}}


def test_match_lookup_fans_out_identical_sequences_to_all_ids():
    import hashlib

    sequence = "MKVLA"
    md5 = hashlib.md5(sequence.encode()).hexdigest().upper()
    xml_response = SAMPLE_MATCH_XML.format(md5=md5).encode()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return xml_response

    with patch("candy.interpro.urlopen", return_value=FakeResponse()):
        matches, unmatched = match_lookup({"P1": sequence, "P2": sequence, "P3": "DIFFERENT"})

    assert set(matches.keys()) == {"P1", "P2"}
    assert matches["P1"].hits == matches["P2"].hits
    assert matches["P1"].hits[0].domain_code == "PF00128"
    assert unmatched == ["P3"]
