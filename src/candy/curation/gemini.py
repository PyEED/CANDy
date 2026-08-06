from __future__ import annotations

import ast
import os

_PROMPT_TEMPLATE = (
    "I have the following list of protein domains, retrieved from InterPro's member "
    "databases: {domain_names}. These sequences {family_clause}. I want you to group "
    "these domains in overarching domains. For instance, all domains related to the "
    "catalytic activity need to be grouped under the term 'Catalytic domain', domains "
    "related to carbohydrate binding need to be grouped as 'CBM', and so on. Fibronectin "
    "III domains can be considered as immunoglobulin-like. Determine the overarching "
    "names yourself. If a domain can't be grouped with another one, keep the name. If a "
    "catalytic domain is found that is not expected for this family, don't include it in "
    "the 'Catalytic domain' name, but give it a separate name. I want you to output only a "
    "dictionary in the following format: {{'overarching name': ['domain 1', 'domain 2', "
    "'domain 3'], ... }}"
)


class GeminiCurationBackend:
    """Automated curation via Google Gemini, ported from the notebook's default path.

    Requires the optional ``gemini`` extra (``pip install candy-cazyme[gemini]``)
    and an API key, passed explicitly or read from ``GOOGLE_API_KEY`` /
    ``GEMINI_API_KEY``.
    """

    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini curation requires an API key. Pass api_key=, or set the "
                "GOOGLE_API_KEY or GEMINI_API_KEY environment variable."
            )
        self.model = model

    def curate(self, domain_names: list[str], *, family: str | None = None) -> dict[str, list[str]]:
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError(
                "Gemini curation requires the optional 'gemini' extra: "
                "pip install candy-cazyme[gemini]"
            ) from exc

        family_clause = (
            f"belong to enzymes from CAZy family {family}" if family else "are carbohydrate-active enzymes"
        )
        prompt = _PROMPT_TEMPLATE.format(domain_names=domain_names, family_clause=family_clause)

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(model=self.model, contents=prompt)

        cleaned = response.text.replace("python", "").replace("```", "")
        return ast.literal_eval(cleaned)
