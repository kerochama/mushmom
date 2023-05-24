"""
Used to launch the bot

"""
import os
import asyncio
import argparse

from motor.motor_asyncio import AsyncIOMotorClient
from mushmom.bot import Mushmom
from dotenv import load_dotenv

load_dotenv()  # use env variables from .env


def run_bot():
    # flags for sync
    parser = argparse.ArgumentParser(description='Launch the bot')
    parser.add_argument('-s', '--sync', action='store_true',
                        help='Sync slash commands')
    parser.add_argument('-g', '--guild', default=0, help='Guild ID')
    args = parser.parse_args()

    # database
    db_client = AsyncIOMotorClient(os.getenv('MONGO_CONN_STR'))
    db_client.get_io_loop = asyncio.get_running_loop

    # start bot
    sync = int(args.guild) or True if args.sync else None
    bot = Mushmom(db_client, sync=sync)
    bot.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    run_bot()
