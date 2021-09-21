import json
import importlib.resources

from collections import namedtuple

from mushmom.mapleio import resources, api


class Equip:
    def __init__(self, itemid, version, name="", type=None):
        self.itemid = itemid
        self.type = type or equip_type(itemid)
        self.version = version

        # only make requests if needed
        self._name = name

    @property
    async def name(self):
        if not self._name:
            data = await api.get_item(self.itemid, version=self.version)
            self._name = data['description']['name']

        return self._name

    def to_dict(self, verbose=False):
        d = {'type': self.type, 'itemId': self.itemid, 'version': self.version}

        if verbose:
            d['name'] = self.name

        return d

    def __repr__(self):
        args = {k.strip('_'): v if isinstance(v, int) else '"{}"'.format(v.replace('"', '\\"'))
                for k, v in self.__dict__.items() if v}
        return 'Equip({})'.format(', '.join(['{}={}'.format(k, v)
                                             for k, v in args.items()]))


EquipType = namedtuple('EquipType', 'name category subcategory low high')  # pseudo class

# parse equip_ranges
_equip_ranges_json = importlib.resources.read_text(resources, 'equip_ranges.json')

EQUIP_RANGES = list()

for cat, subcats in json.loads(_equip_ranges_json).items():
    for subcat_dict in subcats:
        subcat, low, high = subcat_dict.values()
        EQUIP_RANGES.append(
            EquipType('Weapon' if 'Weapon' in cat else subcat,
                      cat, subcat, low, high)
        )


def equip_type(itemid):
    """
    Gets the EquipType if any

    :param itemid:
    :return:
    """
    iterator = (x for x in EQUIP_RANGES if x.low <= itemid <= x.high)
    itemtype = next(iterator, None)

    if itemtype:
        return itemtype.name


def valid_equip(itemid):
    """
    Checks if id is in one of the valid equip ranges

    :param itemid:
    :return:
    """
    return equip_type(itemid) is not None
