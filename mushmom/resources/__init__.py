"""
Resources used in cogs/commands

"""
import yaml

from importlib import resources
from collections import namedtuple

# simple models
Emoji = namedtuple('Emoji', 'id')
Attachment = namedtuple('Attachment', 'channel_id id filename url')
Background = namedtuple('Background', 'attachment y_ground')


def _fmt_attm(channel_id, attachment_id, filename):
    path = 'https://cdn.discordapp.com/attachments'
    url = f'{path}/{channel_id}/{attachment_id}/{filename}'
    return Attachment(channel_id, attachment_id, filename, url)


with resources.open_binary(__package__, 'discord.yaml') as fp:
    _discord = yaml.safe_load(fp)

# constant dicts to of resources
EMOJIS = {k: Emoji(v) for k, v in _discord['emojis'].items()}
ATTACHMENTS = {k: _fmt_attm(*v) for k, v in _discord['attachments'].items()}
BACKGROUNDS = {
    k: Background(_fmt_attm(*v['attm']), v['y_ground'])
    for k, v in _discord['backgrounds'].items()
}
