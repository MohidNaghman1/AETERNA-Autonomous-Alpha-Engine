"""Cryptocurrency entity extraction utility.

Extracts cryptocurrency ticker symbols and keywords from text content
using regex pattern matching against a predefined list of major crypto assets.
"""

import re
from typing import List

CRYPTO_KEYWORDS = [
    "BTC",
    "ETH",
    "USDT",
    "USDC",
    "BNB",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "TON",
    "TRX",
    "DOT",
    "MATIC",
    "SHIB",
    "DAI",
    "LTC",
    "BCH",
    "LINK",
    "XLM",
    "ATOM",
    "FIL",
]

CRYPTO_REGEX = re.compile(r"\b(" + "|".join(CRYPTO_KEYWORDS) + r")\b", re.IGNORECASE)


def extract_crypto_mentions(text: str) -> List[str]:
    """Extract unique cryptocurrency ticker mentions from text.

    Args:
        text: Text content to search for crypto mentions

    Returns:
        List[str]: Unique cryptocurrency symbols found (uppercase), empty list if none found
    """
    if not text:
        return []
    return list(set(match.upper() for match in CRYPTO_REGEX.findall(text)))
