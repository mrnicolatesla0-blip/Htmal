"""Licensed market-data provider adapter.

Implement this module for the provider whose subscription and display rights
cover this application. Do not scrape exchange websites or invent quotes.
"""
from typing import Any


class ProviderNotConfigured(RuntimeError):
    pass


def fetch_quotes(symbols: list[str]) -> dict[str, Any]:
    """Return normalized real quotes from the configured provider.

    Required top-level response: {"quotes": [normalized quote, ...]}.
    Provider-specific authentication and response mapping belong here.
    """
    raise ProviderNotConfigured(
        "No licensed market-data provider is configured. "
        "No prices will be fabricated."
    )
