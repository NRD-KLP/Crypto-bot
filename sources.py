import feedparser

COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"


def get_latest_news():
    news = []

    feeds = [COINDESK_RSS, COINTELEGRAPH_RSS]

    for url in feeds:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            news.append({
                "title": entry.title,
                "link": entry.link,
            })

    return news
