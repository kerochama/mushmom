"""
Used to launch the bot

"""
import os

from mushmom.bot import Mushmom
from dotenv import load_dotenv

load_dotenv()  # use env variables from .env


def run_bot():
    bot = Mushmom()
    bot.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    run_bot()
