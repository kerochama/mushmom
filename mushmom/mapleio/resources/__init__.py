"""
Various json resources from maplestory.io

"""
import json

from importlib import resources


# load all json resources
with resources.open_binary(__package__, 'expressions.json') as fp:
    _expressions = json.load(fp)

EXPRESSIONS = list(_expressions.keys())
ANIMATED = [k for k, v in _expressions.items() if v == 'animated']

with resources.open_binary(__package__, 'equip_ranges.json') as fp:
    EQUIP_RANGES = json.load(fp)

with resources.open_binary(__package__, 'poses.json') as fp:
    POSES = json.load(fp)

with resources.open_binary(__package__, 'skins.json') as fp:
    SKINS = json.load(fp)

with resources.open_binary(__package__, 'jobs.json') as fp:
    JOBS = json.load(fp)
