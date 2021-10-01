"""
Various json resources from maplestory.io

"""
import os
import json

from importlib import resources


# Defined only to resolve references (pycharm inspection)
EMOTIONS = None
EQUIP_RANGES = None
POSES = None
SKINS = None

# load all json files
for f in resources.contents(__package__):
    name, ext = os.path.splitext(f)

    if ext == '.json':
        with resources.open_binary(__package__, f) as fp:
            globals()[name.upper()] = json.load(fp)

