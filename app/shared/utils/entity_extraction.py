"""
Entity extraction utility for crypto mentions (BTC, ETH, etc.)
"""
import re
from typing import List

CRYPTO_KEYWORDS = [
    "BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "XRP", "ADA", "DOGE", "TON", "TRX", "DOT", "MATIC", "SHIB", "DAI", "LTC", "BCH", "LINK", "XLM", "ATOM", "FIL"
]

CRYPTO_REGEX = re.compile(r"\b(" + "|".join(CRYPTO_KEYWORDS) + r")\b", re.IGNORECASE)


def extract_crypto_mentions(text: str) -> List[str]:
    """Extract crypto tickers/keywords from text."""
    if not text:
        return []
    return list(set(match.upper() for match in CRYPTO_REGEX.findall(text)))
