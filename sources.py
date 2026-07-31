import feedparser


NEWS_SOURCES = [

    "https://www.coindesk.com/arc/outboundfeeds/rss/",

    "https://cointelegraph.com/rss"

]



def get_latest_news():

    news_list = []


    for source in NEWS_SOURCES:

        try:

            feed = feedparser.parse(
                source
            )


            for item in feed.entries[:5]:

                news_list.append(

                    {

                        "title":
                            item.get(
                                "title",
                                "Без заголовка"
                            ),


                        "description":
                            item.get(
                                "description",
                                ""
                            ),


                        "link":
                            item.get(
                                "link",
                                ""
                            )

                    }

                )


        except Exception as e:

            print(
                f"RSS error {source}: {e}"
            )



    return news_list
