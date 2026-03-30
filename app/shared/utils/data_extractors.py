"""
Enhanced data extractors for RSS, price, and social feeds.
Extracts detailed metadata and enriches event data.
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from html.parser import HTMLParser
from urllib.parse import urlparse


class HTMLTagStripper(HTMLParser):
    """Strip HTML tags from text"""

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return "".join(self.text).strip()


def strip_html(html: str) -> str:
    """Remove HTML tags from string"""
    if not html:
        return ""
    try:
        s = HTMLTagStripper()
        s.feed(html)
        return s.get_data()
    except Exception:
        return html


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text"""
    if not text:
        return []
    url_pattern = r"https?://[^\s]+"
    return re.findall(url_pattern, text)


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text"""
    if not text:
        return []
    hashtag_pattern = r"#\w+"
    return re.findall(hashtag_pattern, text.lower())


def extract_mentions(text: str) -> List[str]:
    """Extract @mentions from text"""
    if not text:
        return []
    mention_pattern = r"@\w+"
    return re.findall(mention_pattern, text.lower())


def extract_crypto_entities(text: str) -> List[str]:
    """Extract crypto-related entities/keywords from text."""
    if not text:
        return []

    crypto_keywords = {
        # Major coins
        "bitcoin",
        "btc",
        "ethereum",
        "eth",
        "cardano",
        "ada",
        "solana",
        "sol",
        "xrp",
        "ripple",
        "polkadot",
        "dot",
        "dogecoin",
        "doge",
        "litecoin",
        "ltc",
        # DeFi protocols
        "uniswap",
        "aave",
        "compound",
        "curve",
        "yearn",
        "lido",
        "maker",
        "balancer",
        "sushiswap",
        "pancakeswap",
        "openocean",
        # Layer 2 / Sidechains
        "polygon",
        "matic",
        "arbitrum",
        "optimism",
        "zksync",
        "starknet",
        # Other L1s
        "avalanche",
        "avax",
        "fantom",
        "ftm",
        "near",
        "cosmos",
        "atom",
        "tron",
        "trx",
        # NFT / Metaverse
        "nft",
        "nfts",
        "metaverse",
        "opensea",
        "blur",
        "dydx",
        # Stablecoins
        "usdc",
        "usdt",
        "dai",
        "busd",
        "stablecoin",
        # Concepts
        "defi",
        "cefi",
        "blockchain",
        "web3",
        "dao",
        "token",
        "mining",
        "staking",
        "yield",
        "liquidity",
        "swap",
        "bridge",
        "oracle",
        "validator",
        # Exchanges
        "binance",
        "coinbase",
        "kraken",
        "gemini",
        "bybit",
        "okx",
    }

    text_lower = text.lower()
    found = set()

    for keyword in crypto_keywords:
        if keyword in text_lower:
            found.add(keyword)

    return sorted(list(found))[:15]  # Return max 15 entities


def estimate_read_time(text: str) -> int:
    """Estimate reading time in minutes (average 200 words/min)"""
    if not text:
        return 0
    words = len(text.split())
    return max(1, round(words / 200))


def calculate_content_score(content: Dict[str, Any]) -> float:
    """
    Calculate content quality/importance score (0-100).
    Higher score = more important/detailed content.
    """
    score = 0.0

    # Title length (good titles are 30-100 chars)
    title = str(content.get("title", ""))
    title_len = len(title)
    if 30 <= title_len <= 120:
        score += 20
    elif 120 < title_len:
        score += 15
    elif 15 <= title_len < 30:
        score += 10

    # Summary/description length (good summaries are 100-500 chars)
    summary = str(content.get("summary", "")) or str(content.get("description", ""))
    summary_len = len(summary)
    if 100 <= summary_len <= 500:
        score += 25
    elif 500 < summary_len <= 2000:
        score += 20
    elif summary_len > 2000:
        score += 15

    # Has author
    if content.get("author"):
        score += 10

    # Has multiple entities/categories
    categories = content.get("categories") or []
    if len(categories) >= 2:
        score += 15
    elif len(categories) == 1:
        score += 8

    # Has external links
    links = content.get("links", [])
    if isinstance(links, list) and len(links) > 0:
        score += 15

    # Media presence (image, video)
    if content.get("image_url") or content.get("media"):
        score += 10

    # Content has detailed metadata
    if content.get("source") and content.get("site_name"):
        score += 5

    return min(100.0, score)


def normalize_username(username: Optional[str]) -> str:
    """Normalize social usernames to a consistent @handle format."""
    if not username:
        return ""
    normalized = str(username).strip()
    if normalized.startswith("@"):
        return normalized
    return f"@{normalized}"


# ========== RSS SPECIFIC EXTRACTORS ==========


def extract_rss_entry_detailed(entry: Dict[str, Any], source: str) -> Dict[str, Any]:
    """
    Extract detailed metadata from RSS feed entry.

    Returns enriched content dict with:
    - Basic fields (title, summary, link, published)
    - Metadata (author, categories, image_url)
    - Enhanced fields (urls, hashtags, read_time, word_count)
    - Quality score
    """

    # Core fields
    title = entry.get("title", "").strip()
    summary = entry.get("summary", "") or entry.get("description", "")
    if summary:
        summary = strip_html(summary).strip()

    link = entry.get("link", "")
    published = entry.get("published", "")

    # Author extraction
    author = None
    if entry.get("author"):
        author = entry["author"].strip()
    elif entry.get("author_detail"):
        author = entry.get("author_detail", {}).get("name")

    # Categories/Tags
    categories = []
    if entry.get("tags"):
        categories = [tag.get("term", "").strip() for tag in entry["tags"]]
        categories = [c for c in categories if c]

    # Media extraction
    image_url = None
    media_content = []

    # Try common RSS media fields
    if entry.get("media_content"):
        media_content = entry["media_content"]
        if media_content and media_content[0].get("url"):
            image_url = media_content[0]["url"]

    if entry.get("image"):
        image_url = entry["image"].get("href") or image_url

    # Try to extract image from summary
    if not image_url and summary:
        img_match = re.search(r'<img[^>]+src="([^">]+)"', summary)
        if img_match:
            image_url = img_match.group(1)

    # Extract detailed text content
    full_text = f"{title} {summary}" if summary else title
    word_count = len(full_text.split())
    read_time = estimate_read_time(full_text)

    # Extract URLs, hashtags, mentions
    urls = extract_urls(link + " " + summary) if summary else extract_urls(link)
    urls = list(set(urls))  # Deduplicate

    # Extract crypto entities instead of social media hashtags/mentions
    crypto_entities = extract_crypto_entities(title + " " + summary)

    # Generate hashtags from categories and crypto entities
    hashtags_from_categories = [cat.lower().replace(" ", "") for cat in categories[:5]]
    all_hashtags = list(set(hashtags_from_categories + crypto_entities[:5]))
    hashtags = all_hashtags[:10]  # Limit to top 10

    # Use crypto entities as mentions since RSS doesn't have @mentions
    mentions = crypto_entities  # Already limited to 15 in extract_crypto_entities

    # Build enriched content
    content = {
        # Core fields
        "title": title,
        "summary": summary,
        "link": link,
        "published": published,
        "source": source,
        # Metadata
        "author": author,
        "categories": categories,
        "image_url": image_url,
        # Enhanced extraction
        "word_count": word_count,
        "read_time_minutes": read_time,
        "urls": urls,
        "hashtags": hashtags,
        "mentions": mentions,
        # Quality indicators
        "has_image": bool(image_url),
        "has_author": bool(author),
        "category_count": len(categories),
        "url_count": len(urls),
    }

    # Calculate quality score
    content["quality_score"] = calculate_content_score(content)

    return content


# ========== PRICE SPECIFIC EXTRACTORS ==========


def extract_price_entry_detailed(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract detailed price data from CoinGecko API response.

    Returns enriched content dict with:
    - Price metrics (current, high/low, market cap, volume)
    - Change metrics (1h, 24h, 7d, 30d)
    - Market metrics (market cap rank, fully diluted valuation)
    - Risk indicators (volatility, concentration)
    - Historical context
    """

    # Basic price info
    coin_id = entry.get("id", "").strip()
    symbol = entry.get("symbol", "").upper().strip()
    name = entry.get("name", "").strip()
    current_price = entry.get("current_price")

    # Price range
    ath = entry.get("ath")  # All Time High
    atl = entry.get("atl")  # All Time Low
    high_24h = entry.get("high_24h")
    low_24h = entry.get("low_24h")

    # Calculate price position relative to 24h range
    price_position_24h = None
    if high_24h and low_24h and current_price:
        price_position_24h = (
            (current_price - low_24h) / (high_24h - low_24h)
            if high_24h != low_24h
            else 0.5
        )
        price_position_24h = round(max(0, min(1, price_position_24h)), 3)

    # Price changes over different timeframes
    price_changes = {
        "change_1h_pct": entry.get("price_change_percentage_1h_in_currency"),
        "change_24h_pct": entry.get("price_change_percentage_24h_in_currency"),
        "change_7d_pct": entry.get("price_change_percentage_7d_in_currency"),
        "change_14d_pct": entry.get("price_change_percentage_14d_in_currency"),
        "change_30d_pct": entry.get("price_change_percentage_30d_in_currency"),
        "change_1y_pct": entry.get("price_change_percentage_1y_in_currency"),
        "change_ath_pct": entry.get("ath_change_percentage"),
        "change_atl_pct": entry.get("atl_change_percentage"),
    }

    # Market metrics
    market_cap = entry.get("market_cap")
    market_cap_rank = entry.get("market_cap_rank")
    fully_diluted_valuation = entry.get("fully_diluted_valuation")

    # Market cap dominance (if available)
    market_cap_change_24h = entry.get("market_cap_change_percentage_24h")

    # Volume metrics
    trading_volume_24h = entry.get("total_volume")
    volume_to_market_cap = None
    if trading_volume_24h and market_cap:
        volume_to_market_cap = (
            round(trading_volume_24h / market_cap, 4) if market_cap != 0 else None
        )

    # Circulating supply
    circulating_supply = entry.get("circulating_supply")
    total_supply = entry.get("total_supply")
    max_supply = entry.get("max_supply")

    # Supply metrics
    supply_ratio = None
    if circulating_supply and max_supply:
        supply_ratio = round(circulating_supply / max_supply, 4)

    # Determine volatility category by price change
    price_volatility = None
    change_24h = price_changes.get("change_24h_pct") or 0
    if abs(change_24h) >= 10:
        price_volatility = "high"
    elif abs(change_24h) >= 5:
        price_volatility = "medium"
    else:
        price_volatility = "low"

    # Risk indicators
    risk_score = calculate_crypto_risk_score(entry, price_changes)

    # Build enriched content
    content = {
        # Basic identification
        "id": coin_id,
        "symbol": symbol,
        "name": name,
        # Current price
        "current_price": current_price,
        "price_position_24h": price_position_24h,  # 0-1 scale
        # Price range
        "ath": ath,
        "atl": atl,
        "high_24h": high_24h,
        "low_24h": low_24h,
        # Price changes
        **price_changes,
        "price_volatility_category": price_volatility,
        # Market metrics
        "market_cap": market_cap,
        "market_cap_rank": market_cap_rank,
        "fully_diluted_valuation": fully_diluted_valuation,
        "market_cap_change_24h_pct": market_cap_change_24h,
        # Volume
        "trading_volume_24h": trading_volume_24h,
        "volume_to_market_cap_ratio": volume_to_market_cap,
        # Supply
        "circulating_supply": circulating_supply,
        "total_supply": total_supply,
        "max_supply": max_supply,
        "circulating_to_max_ratio": supply_ratio,
        # Quality/Risk indicators
        "risk_score": risk_score,
        "last_updated": entry.get("last_updated"),
    }

    return content


def calculate_crypto_risk_score(
    entry: Dict[str, Any], price_changes: Dict[str, Any]
) -> float:
    """
    Calculate risk score for a cryptocurrency (0-100, higher = more risky).

    Factors:
    - Price volatility
    - Market cap rank (lower rank = less established)
    - Volume to market cap ratio
    - Supply concentration
    """

    risk = 0.0

    # 1. Volatility risk (0-30 points)
    change_24h = abs(price_changes.get("change_24h_pct") or 0)
    if change_24h > 20:
        risk += 30
    elif change_24h > 10:
        risk += 20
    elif change_24h > 5:
        risk += 10
    else:
        risk += 5

    # 2. Market cap rank risk (0-30 points)
    # Top 10 = lowest risk, Outside top 100 = highest risk
    market_cap_rank = entry.get("market_cap_rank")
    if market_cap_rank:
        if market_cap_rank <= 10:
            risk += 5
        elif market_cap_rank <= 50:
            risk += 15
        elif market_cap_rank <= 100:
            risk += 25
        else:
            risk += 30
    else:
        risk += 30

    # 3. Volume to Market Cap ratio (0-20 points)
    # Higher ratio = more liquid = lower risk
    volume = entry.get("total_volume")
    market_cap = entry.get("market_cap")
    if volume and market_cap and market_cap != 0:
        v_to_mc = volume / market_cap
        if v_to_mc > 1:
            risk += 5
        elif v_to_mc > 0.5:
            risk += 10
        elif v_to_mc > 0.1:
            risk += 15
        else:
            risk += 20
    else:
        risk += 20

    # 4. Supply concentration (0-20 points)
    max_supply = entry.get("max_supply")
    circulating_supply = entry.get("circulating_supply")
    if max_supply and circulating_supply and max_supply != 0:
        supply_ratio = circulating_supply / max_supply
        if supply_ratio > 0.9:
            risk += 5
        elif supply_ratio > 0.7:
            risk += 10
        elif supply_ratio > 0.5:
            risk += 15
        else:
            risk += 20
    else:
        risk += 15

    return min(100.0, risk)


def identify_significant_changes(
    current_entry: Dict[str, Any],
    previous_price: Optional[float] = None,
    significance_threshold_pct: float = 5.0,
) -> Dict[str, Any]:
    """
    Identify significant price movements and market changes.

    Returns dict with:
    - significant_moves: list of identified movements
    - should_alert: bool indicating if changes warrant attention
    - alert_reasons: reasons for alert
    """

    changes = current_entry.get("price_changes", {})
    alerts = []

    change_1h = changes.get("change_1h_pct") or 0
    change_24h = changes.get("change_24h_pct") or 0
    change_7d = changes.get("change_7d_pct") or 0

    # Check for significant 1-hour movement
    if abs(change_1h) >= significance_threshold_pct:
        direction = "↑" if change_1h > 0 else "↓"
        alerts.append(f"1h: {direction} {abs(change_1h):.2f}%")

    # Check for significant 24-hour movement
    if abs(change_24h) >= significance_threshold_pct:
        direction = "↑" if change_24h > 0 else "↓"
        alerts.append(f"24h: {direction} {abs(change_24h):.2f}%")

    # Check for sustained movement (same direction across timeframes)
    if (change_1h > 0 and change_24h > 0) or (change_1h < 0 and change_24h < 0):
        alerts.append("Sustained trend")

    # Check for ATH/ATL proximity
    ath = current_entry.get("ath")
    atl = current_entry.get("atl")
    current_price = current_entry.get("current_price")

    if ath and current_price:
        distance_to_ath = abs(current_price - ath) / ath * 100
        if distance_to_ath < 5:
            alerts.append(f"Near ATH (5% away)")

    if atl and current_price:
        distance_to_atl = abs(current_price - atl) / atl * 100
        if distance_to_atl < 5:
            alerts.append(f"Near ATL (5% away)")

    return {
        "significant_moves": alerts,
        "should_alert": len(alerts) > 0,
        "alert_reasons": " | ".join(alerts) if alerts else None,
    }


# ========== TWITTER/X SPECIFIC EXTRACTORS ==========


def calculate_engagement_rate(
    public_metrics: Dict[str, Any], followers_count: Optional[int]
) -> float:
    """Calculate a bounded engagement rate for social posts."""
    if not public_metrics:
        return 0.0

    followers = max(int(followers_count or 0), 0)
    likes = int(public_metrics.get("like_count", 0) or 0)
    retweets = int(public_metrics.get("retweet_count", 0) or 0)
    replies = int(public_metrics.get("reply_count", 0) or 0)
    quotes = int(public_metrics.get("quote_count", 0) or 0)
    bookmarks = int(public_metrics.get("bookmark_count", 0) or 0)
    impressions = int(public_metrics.get("impression_count", 0) or 0)

    engagements = likes + retweets + replies + quotes + bookmarks
    denominator = followers or impressions
    if denominator <= 0:
        return 0.0

    rate = engagements / denominator
    return round(max(0.0, min(rate, 1.0)), 4)


def extract_twitter_tweet_detailed(
    tweet: Dict[str, Any], author: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract detailed metadata from a Twitter/X recent search result.

    Returns a normalized social payload with author, engagement, URLs,
    hashtags, and quality indicators.
    """
    text = (tweet.get("text") or "").strip()
    tweet_id = str(tweet.get("id") or "").strip()
    created_at = tweet.get("created_at")
    lang = tweet.get("lang")
    author = author or {}
    public_metrics = tweet.get("public_metrics") or {}
    author_metrics = author.get("public_metrics") or {}

    username_raw = author.get("username") or ""
    username = normalize_username(username_raw)
    followers_count = int(author_metrics.get("followers_count", 0) or 0)
    following_count = int(author_metrics.get("following_count", 0) or 0)
    tweet_count = int(author_metrics.get("tweet_count", 0) or 0)
    listed_count = int(author_metrics.get("listed_count", 0) or 0)

    urls = extract_urls(text)
    hashtags = extract_hashtags(text)
    mentions = extract_mentions(text)
    entities = extract_crypto_entities(text)

    tweet_url = ""
    if username_raw and tweet_id:
        tweet_url = f"https://twitter.com/{username_raw}/status/{tweet_id}"

    content = {
        "tweet_id": tweet_id,
        "title": f"{username} on X" if username else "Twitter/X Post",
        "summary": text,
        "text": text,
        "url": tweet_url,
        "link": tweet_url,
        "published": created_at,
        "source": "twitter",
        "source_domain": urlparse(tweet_url).netloc if tweet_url else "twitter.com",
        "lang": lang,
        "conversation_id": tweet.get("conversation_id"),
        "possibly_sensitive": bool(tweet.get("possibly_sensitive", False)),
        "hashtags": hashtags,
        "mentions": list(dict.fromkeys(mentions + entities))[:15],
        "urls": urls,
        "url_count": len(urls),
        "word_count": len(text.split()),
        "author": {
            "id": str(author.get("id") or ""),
            "name": author.get("name"),
            "username": username,
            "verified": bool(author.get("verified", False)),
            "followers_count": followers_count,
            "following_count": following_count,
            "tweet_count": tweet_count,
            "listed_count": listed_count,
        },
        "engagement": {
            "likes": int(public_metrics.get("like_count", 0) or 0),
            "retweets": int(public_metrics.get("retweet_count", 0) or 0),
            "replies": int(public_metrics.get("reply_count", 0) or 0),
            "quotes": int(public_metrics.get("quote_count", 0) or 0),
            "bookmarks": int(public_metrics.get("bookmark_count", 0) or 0),
            "impressions": int(public_metrics.get("impression_count", 0) or 0),
        },
        "followers_count": followers_count,
        "verified": bool(author.get("verified", False)),
        "engagement_rate": calculate_engagement_rate(public_metrics, followers_count),
        "site_name": "Twitter/X",
    }
    content["quality_score"] = calculate_content_score(content)
    return content
