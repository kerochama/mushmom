"""
Parse config and make it accessible

"""
import munch
import os

from importlib import resources
from dotenv import load_dotenv

load_dotenv()  # use env variables from .env

file = os.getenv('CONFIG_FILE') or 'config.yaml'

with resources.open_binary(__package__, file) as fp:
    config = munch.Munch.fromYAML(fp)
    config.urls.add_bot = ''.join(config.urls.add_bot.split())
