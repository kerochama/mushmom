"""
Resources used in cogs/commands

"""
import yaml

from importlib import resources
from collections import namedtuple

# simple models
Emoji = namedtuple('Emoji', 'id')
Attachment = namedtuple('Attachment', 'channel_id id filename')
Background = namedtuple('Background', 'attachment y_ground')

with resources.open_binary(__package__, 'discord.yaml') as fp:
    _discord = yaml.safe_load(fp)

# constant dicts to of resources
EMOJIS = {k: Emoji(v) for k, v in _discord['emojis'].items()}
ATTACHMENTS = {k: Attachment(*v) for k, v in _discord['attachments'].items()}
BACKGROUNDS = {
    k: Background(Attachment(*v['attm']), v['y_ground'])
    for k, v in _discord['backgrounds']
}
