import feedparser
from translator import translate
from cleaner import clean_text


COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"


def get_latest_news():
    news = []

    feeds = [COINDESK_RSS, COINTELEGRAPH_RSS]

    for url in feeds:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            news.append({
                "title": clean_text(translate(entry.title)),

                "description": clean_text(translate(getattr(entry, "summary", ""))),
})

    return news
    
