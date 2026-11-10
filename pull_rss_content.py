import feedparser
import asyncio

def _clean_feed(feed):

    entries_cleand = []

    for entry in feed:

        entries_cleand.append(
            {'title': entry.get('title', 'No Title Found'),
             'summary': entry.get('summary', 'No Summary Found'),
             'link': entry.get('link', "No Link Found")})

    return entries_cleand

def _parse_feed(league: str):

    rss_url = f"https://www.espn.com/espn/rss/{league.lower()}/news"

    feed = feedparser.parse(rss_url)

    return feed['entries']

async def get_news(league: str):

    feed = await asyncio.to_thread(_parse_feed, league)
    return _clean_feed(feed)

if __name__ == "__main__":

    print(asyncio.run(get_news("nfl")))


    