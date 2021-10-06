"""
Representation of a maplestory equip.  Attributes stored are those needed
in order to read in and recreate API calls

"""
from __future__ import annotations

from collections import namedtuple
from typing import Optional, Union, Any

from . import resources, api


EquipType = namedtuple('EquipType', 'name category subcategory low high')  # pseudo class

EQUIP_TYPES = [
    EquipType('Weapon' if 'Weapon' in cat else d['subCategory'], cat, *d.values())
    for cat, data in resources.EQUIP_RANGES.items()
    for d in data
]


class Equip:
    """
    Representation of a maplestory/maplestory.io equip

    Attributes
    ----------
    itemid: Union[int, str]
        the maplestory/maplestory.io item id
    version: str
        maplestory version
    region: str
        maplestory region
    type: Optional[str]
        for most equipment, this will be the maplestory.io subcategory
        one-handed and two-handed weapons will just be referred to as
        'Weapon'

    """
    def __init__(
            self,
            itemid: Union[int, str],
            version: str,
            region: str = 'GMS',
            name: Optional[str] = None,
            type: Optional[str] = None
    ) -> None:
        self.itemid = itemid
        self.type = type or Equip.get_equip_type(itemid)
        self.region = region
        self.version = version

        # cache api return
        self._name = name

    async def get_name(self) -> str:
        """
        Make API call if name has not been cached

        Returns
        -------
        str
            the item name based on region/version

        """
        if not self._name:
            data = await api.get_item(self.itemid, version=self.version)
            self._name = data['description']['name']

        return self._name

    def to_dict(
            self,
            map: dict[str, str] = None,
            exclude: Optional[list[str, ...]] = None
    ) -> dict[str, Any]:
        """

        Parameters
        ----------
        map: dict[str, str]
            mapping of key to new key
        exclude: Optional[list[str, ...]]
            list of keys to exclude

        Returns
        -------
        dict
            dict representation of equip

        """
        d = {'type': self.type, 'itemId': self.itemid, 'version': self.version}

        if self.region != 'GMS':
            d['region'] = self.region

        if self._name:
            d['name'] = self._name

        # pop any excluded keys
        for k in exclude or []:
            d.pop(k, None)

        map = map or {}
        return {map[k] if k in map else k: v for k, v in d.items()}

    @classmethod
    def get_equip_type(cls, itemid: Union[int, str]) -> str:
        """
        Gets the EquipType if any

        Parameters
        ----------
        itemid: Union[int, str]
           the maplestory/maplestory.io item id

        Returns
        -------

        """
        iterator = (x for x in EQUIP_TYPES if x.low <= itemid <= x.high)
        itemtype = next(iterator, None)

        if itemtype:
            return itemtype.name

    @classmethod
    def valid_equip(cls, itemid: Union[int, str]) -> bool:
        """
        Checks if itemid falls into any valid equip type range

        Parameters
        ----------
        itemid: Union[int, str]
           the maplestory/maplestory.io item id

        Returns
        -------
        bool
            whether or not the item is in a valid equip itemid range

        """
        return cls.get_equip_type(itemid) is not None

    def __repr__(self):
        args = {k.strip('_'): v if isinstance(v, int) else '"{}"'.format(v.replace('"', '\\"'))
                for k, v in self.__dict__.items() if v}
        return 'Equip({})'.format(', '.join(['{}={}'.format(k, v)
                                             for k, v in args.items()]))
