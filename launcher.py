"""
Used to launch the bot

"""
import os

from motor.motor_asyncio import AsyncIOMotorClient
from mushmom.bot import Mushmom
from dotenv import load_dotenv

load_dotenv()  # use env variables from .env


def run_bot():
    db_client = AsyncIOMotorClient(os.getenv('MONGO_CONN_STR'))

    # start bot
    bot = Mushmom(db_client)
    bot.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    run_bot()
