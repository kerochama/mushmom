"""
Poses and emotions

"""

import json
import importlib.resources

from mushmom.mapleio import resources


POSES = json.loads(
    importlib.resources.read_text(resources, 'poses.json')
)
EMOTIONS = json.loads(
    importlib.resources.read_text(resources, 'emotions.json')
)