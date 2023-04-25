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
    JOB_INFO = json.load(fp)

with resources.open_binary(__package__, 'servers.json') as fp:
    SERVER_INFO = json.load(fp)


# extract into list for easy access
JOBS = [info['job'] for info in JOB_INFO]
GAMES = list(SERVER_INFO.keys())

_SERVERS = []
for game, game_info in SERVER_INFO.items():
    for region, region_info in game_info.items():
        for server in region_info['servers'] or []:  # skip no server info
            code = region_info.get('abbrev') or region_info.get('code')
            _SERVERS.append(f'{server} ({code})')

SERVERS = list(set(_SERVERS))
