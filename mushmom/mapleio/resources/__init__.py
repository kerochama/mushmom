"""
Various json resources from maplestory.io

"""
import json

from importlib import resources


# load all json resources
with resources.open_binary(__package__, 'emotions.json') as fp:
    _emotions = json.load(fp)

EMOTIONS = list(_emotions.keys())
ANIMATED = [k for k, v in _emotions.items() if v == 'animated']

with resources.open_binary(__package__, 'equip_ranges.json') as fp:
    EQUIP_RANGES = json.load(fp)

with resources.open_binary(__package__, 'poses.json') as fp:
    POSES = json.load(fp)

with resources.open_binary(__package__, 'skins.json') as fp:
    SKINS = json.load(fp)

with resources.open_binary(__package__, 'jobs.json') as fp:
    JOBS = json.load(fp)
