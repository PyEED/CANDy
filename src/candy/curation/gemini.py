from __future__ import annotations

import ast
import logging
import os

logger = logging.getLogger(__name__)

# Bounds a single request attempt so a hung/slow connection can't stall the
# pipeline indefinitely and invisibly -- the underlying SDK retries up to 5
# times by default (on 408/429/5xx) via tenacity, which does not log
# anything itself, so without this a stall here can look identical to a
# genuine hang even though it's just silently backing off and retrying.
_REQUEST_TIMEOUT_MS = 60_000

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

    def __init__(self, api_key: str | None = None, model: str = "gemini-flash-latest") -> None:
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
            from google.genai import types
        except ImportError as exc:
            raise ImportError(
                "Gemini curation requires the optional 'gemini' extra: "
                "pip install candy-cazyme[gemini]"
            ) from exc

        family_clause = (
            f"belong to enzymes from CAZy family {family}" if family else "are carbohydrate-active enzymes"
        )
        prompt = _PROMPT_TEMPLATE.format(domain_names=domain_names, family_clause=family_clause)

        logger.info(
            "Requesting domain-name curation from Gemini (model=%s, %d domain names). This can take "
            "a while if the API is transiently retrying -- it isn't stuck if it takes a few minutes.",
            self.model,
            len(domain_names),
        )
        client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS))
        response = client.models.generate_content(model=self.model, contents=prompt)
        logger.info("Received curation response from Gemini.")

        cleaned = response.text.replace("python", "").replace("```", "")
        return ast.literal_eval(cleaned)
