import os
from dotenv import load_dotenv
from discord_functions import NewsBot

load_dotenv()
TOKEN = os.environ["DISCORD_TOKEN"]

# Which leagues to poll, and the channel ID each one posts to.
# (Developer Mode on -> right-click a channel -> "Copy Channel ID")
# Point several leagues at the same channel to keep them all in one place.
LEAGUE_CHANNELS = {
    "nfl": 1224471014033985606,
    "nba": 1170103092197470318,
    "mlb": 1224470979821043794,
    "nhl": 1224471033051086858,
}

POLL_MINUTES = 1


if __name__ == "__main__":
    NewsBot(LEAGUE_CHANNELS, POLL_MINUTES).run(TOKEN)