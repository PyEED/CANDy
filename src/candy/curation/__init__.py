"""Pluggable domain-name curation backends.

InterPro's member databases often have several different names for what is
functionally the same domain. Curation groups those synonymous names under
one umbrella name. The notebook hard-required a Gemini API key for its
"automated" path; here that's one optional backend among others behind a
common protocol, with manual curation as the dependency-free default.
"""

from __future__ import annotations

from typing import Protocol


class CurationBackend(Protocol):
    name: str

    def curate(self, domain_names: list[str], *, family: str | None = None) -> dict[str, list[str]]:
        """Group synonymous domain names.

        Returns ``{umbrella_name: [raw_name, ...]}``. Every name in
        ``domain_names`` should appear in exactly one group (domains that
        can't be grouped with anything else become their own singleton group).
        """
        ...


def get_curation_backend(name: str, **kwargs) -> CurationBackend:
    if name == "manual":
        from candy.curation.manual import ManualCurationBackend

        return ManualCurationBackend(**kwargs)
    if name == "gemini":
        from candy.curation.gemini import GeminiCurationBackend

        return GeminiCurationBackend(**kwargs)
    raise ValueError(f"Unknown curation backend: {name}")
