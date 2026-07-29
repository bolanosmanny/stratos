import requests
import re
from fastapi import HTTPException

def is_directly_relevant(
    article: dict,
    ticker: str,
    company_name: str
) -> bool:
    ticker_match = any(
        ticker_data.get("ticker") == ticker
        for ticker_data in article.get("ticker_sentiment", [])
    )

    title = article.get("title", "").lower()

    company_words = [
        word
        for word in re.findall(r"[a-z]+", company_name.lower())
        if word 
        not in { 
            "inc",
            "corp",
            "corporation",
            "co",
            "company",
            "ltd",
            "limited",
            "plc",
            "class",
        }
        and len(word) >= 3
    ]

    title_match = ( 
        ticker.lower() in title
        or any(word in title for word in company_words)
    )

    return ticker_match and title_match

def get_company_news(
        ticker: str,
        api_key: str,
        company_name: str,
        limit: int = 6,
) -> list[dict]:
    try:
        response = requests.get(
            "https://www.alphavantage.co/query",
            params={ 
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "sort": "LATEST",
                "limit": 50,
                "apikey": api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as error:
        raise HTTPException(
            status_code = 502,
            detail=f"News provider request failed: {error}",
        )

    if "Information" in data or "Note" in data:
        raise HTTPException(
            status_code = 429,
            detail="News API rate limit reached. Please try again later.",
        )

    if "Error Message" in data:
        raise HTTPException(
            status_code = 502,
            detail="The news provider could not retrieve this ticker.",
        )

    feed = data.get("feed")

    if not isinstance(feed, list):
        raise HTTPException(
            status_code = 502,
            detail="The news provider returned an unexpected response.",
        )

    articles = []
    seen_titles = set()

    for article in feed:
        if not is_directly_relevant(article, ticker, company_name):
            continue

        title = article.get("title", "Untitled Article")
        title_key = re.sub(r"\s+", " ", title.lower()).strip()

        if title_key in seen_titles:
            continue

        seen_titles.add(title_key)

        articles.append(
            {
                "title": title,
                "summary": article.get("summary", ""),
                "source": article.get("source", "Unknown Source"),
                "url": article.get("url", ""),
                "published_at": article.get("time_published", ""),
                "sentiment": article.get(
                    "overall_sentiment_label",
                    "Neutral"
                ),
            }
        )

        if len(articles) >= limit:
            break

    return articles

