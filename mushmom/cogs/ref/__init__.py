"""
Some reference data for cogs

"""
import yaml

from importlib import resources


with resources.open_binary(__package__, 'errors.yaml') as fp:
    ERRORS = yaml.safe_load(fp)

with resources.open_binary(__package__, 'help.yaml') as fp:
    HELP = yaml.safe_load(fp)

