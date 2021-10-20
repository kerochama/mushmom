"""
Resources used in cogs/commands

"""
import yaml

from importlib import resources


with resources.open_binary(__package__, 'discord.yaml') as fp:
    _discord = yaml.safe_load(fp)

EMOJIS = _discord['emojis']
ATTACHMENTS = _discord['attachments']
