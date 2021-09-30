import json
import importlib.resources

from collections import namedtuple

from mushmom.mapleio import resources, api


EquipType = namedtuple('EquipType', 'name category subcategory low high')  # pseudo class

EQUIP_TYPES = [
    EquipType('Weapon' if 'Weapon' in cat else d['subCategory'], cat, *d.values())
    for cat, data in resources.EQUIP_RANGES.items()
    for d in data
]


class Equip:
    def __init__(self, itemid, version, name="", type=None):
        self.itemid = itemid
        self.type = type or Equip.get_equip_type(itemid)
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

    @classmethod
    def get_equip_type(cls, itemid):
        """
        Gets the EquipType if any

        :param itemid:
        :return:
        """
        iterator = (x for x in EQUIP_TYPES if x.low <= itemid <= x.high)
        itemtype = next(iterator, None)

        if itemtype:
            return itemtype.name

    @classmethod
    def valid_equip(cls, itemid):
        """
        Checks if id is in one of the valid equip ranges

        :param itemid:
        :return:
        """
        return cls.get_equip_type(itemid) is not None

    def __repr__(self):
        args = {k.strip('_'): v if isinstance(v, int) else '"{}"'.format(v.replace('"', '\\"'))
                for k, v in self.__dict__.items() if v}
        return 'Equip({})'.format(', '.join(['{}={}'.format(k, v)
                                             for k, v in args.items()]))
