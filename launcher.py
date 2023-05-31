"""
Used to launch the bot

"""
import os
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from mushmom.bot import Mushmom
from dotenv import load_dotenv

load_dotenv()  # use env variables from .env


def run_bot():
    # database
    db_client = AsyncIOMotorClient(os.getenv('MONGO_CONN_STR'))
    db_client.get_io_loop = asyncio.get_running_loop

    # start bot
    bot = Mushmom(db_client)
    bot.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    run_bot()
