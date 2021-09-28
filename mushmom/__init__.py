"""
Parse config and make it accessible

"""
import sys
import munch

from importlib import resources


with resources.open_binary(sys.modules[__name__], 'config.yaml') as fp:
    config = munch.Munch.fromYAML(fp)
