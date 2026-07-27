import feedparser
from translator import translate
from cleaner import clean_text
from datetime import datetime, timezone


COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"


def get_latest_news():
    news = []

    feeds = [COINDESK_RSS, COINTELEGRAPH_RSS]

    for url in feeds:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:

            published = getattr(entry, "published_parsed", None)
        
            if published:
                published_time = datetime(
                    *published[:6],
                    tzinfo=timezone.utc
                )
        
                age = datetime.now(
                    timezone.utc
                ) - published_time
        
                if age.total_seconds() > 86400:
                    continue
        
            news.append({
                "title": clean_text(
                    translate(entry.title)
                ),
                "description": clean_text(
                    translate(
                        getattr(entry, "summary", "")
                    )
                ),
                "link": entry.link
            })
    return news
    
