import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import discord
from discord.ext import tasks

from pull_rss_content import get_news

MAX_SEEN = 2000  # how many past articles to remember (oldest are dropped)


def make_embed(article, league):
    link = article["link"]
    embed = discord.Embed(
        title=article["title"][:256],
        description=article["summary"][:1000],
        url=link if link.startswith("http") else None,
        color=discord.Color.red(),
    )
    embed.set_footer(text=f"ESPN {league.upper()}")
    return embed


def article_key(article):
    """A stable ID for an article, so the same story is recognised everywhere.

    Strips query strings / fragments (tracking params) from the link.
    Falls back to the title if there's no usable link.
    """
    link = article["link"]
    if not link.startswith("http"):
        return article["title"].strip().lower()
    parts = urlsplit(link)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


class NewsBot(discord.Client):
    def __init__(self, league_channels: dict[str, int], poll_minutes: int = 10,
                 seen_file: str = "seen_articles.json"):
        super().__init__(intents=discord.Intents.default())
        self.league_channels = league_channels
        self.poll_minutes = poll_minutes
        self.seen_file = Path(seen_file)
        self.seen, self.primed = self._load_seen()

    # --- Persistence ---------------------------------------------------------

    def _load_seen(self):
        """Returns (seen article keys in order, leagues already primed)."""
        if not self.seen_file.exists():
            return {}, set()
        data = json.loads(self.seen_file.read_text())
        return dict.fromkeys(data.get("articles", [])), set(data.get("leagues", []))

    def _save_seen(self):
        articles = list(self.seen)[-MAX_SEEN:]
        self.seen = dict.fromkeys(articles)
        tmp = self.seen_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"leagues": sorted(self.primed), "articles": articles}))
        tmp.replace(self.seen_file)  # atomic, so a crash can't corrupt the file

    # --- Bot -----------------------------------------------------------------

    async def setup_hook(self):
        self.poll_feeds.change_interval(minutes=self.poll_minutes)
        self.poll_feeds.start()

    async def on_ready(self):
        print(f"Logged in as {self.user} - polling every {self.poll_minutes} min")

    async def _get_channel(self, channel_id):
        return self.get_channel(channel_id) or await self.fetch_channel(channel_id)

    @tasks.loop(minutes=10)
    async def poll_feeds(self):
        for league, channel_id in self.league_channels.items():
            try:
                articles = await get_news(league)
            except Exception as e:
                print(f"[{league}] fetch failed: {e}")
                continue

            # First time ever seeing this league: remember what's already
            # in the feed without posting, so the channel isn't flooded.
            if league not in self.primed:
                self.seen.update(dict.fromkeys(article_key(a) for a in articles))
                self.primed.add(league)
                continue

            for article in reversed(articles):  # oldest first
                key = article_key(article)
                if key in self.seen:
                    continue
                try:
                    channel = await self._get_channel(channel_id)
                    await channel.send(embed=make_embed(article, league))
                except Exception as e:
                    # Not marked as seen, so it'll be retried next poll
                    print(f"[{league}] failed to post '{article['title']}': {e}")
                    continue
                self.seen[key] = None

        self._save_seen()

    @poll_feeds.before_loop
    async def before_poll(self):
        await self.wait_until_ready()