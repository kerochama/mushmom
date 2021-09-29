"""
Parse config and make it accessible

"""
import munch

from importlib import resources


with resources.open_binary(__package__, 'config.yaml') as fp:
    config = munch.Munch.fromYAML(fp)
