import feedparser
from translator import translate

COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"


def get_latest_news():
    news = []

    feeds = [COINDESK_RSS, COINTELEGRAPH_RSS]

    for url in feeds:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            news.append({
                "title": translate(entry.title),
                "description": translate(
        getattr(entry, "summary", "")),
                "link": entry.link,
})

    return news
    
