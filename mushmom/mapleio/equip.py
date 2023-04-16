"""
Representation of a maplestory equip.  Attributes stored are those needed
in order to read in and recreate API calls

"""
from __future__ import annotations

from collections import namedtuple
from typing import Optional, Union, Any

from . import api, EQUIP_RANGES


EquipType = namedtuple('EquipType', 'name category subcategory low high')  # pseudo class

EQUIP_TYPES = [
    EquipType('Weapon' if 'Weapon' in cat else d['subCategory'], cat, *d.values())
    for cat, data in EQUIP_RANGES.items()
    for d in data
]

DEFAULT_HSV = namedtuple('hsv', 'h s v')(0, 1, 1)


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
            key_map: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        dict representation of equip

        Parameters
        ----------
        key_map: Optional[dict[str, Optional[str]]]
            mapping of attribute to dict key. Passing None as value removes key

        Returns
        -------
        dict
            dict representation of equip

        """
        _key_map = {
            'type': 'type',
            'itemid': 'itemId',
            'version': 'version',
            'region': 'region',
            '_name': 'name'
        }
        _key_map.update(key_map or {})
        _key_map = {k: v for k, v in _key_map.items() if v is not None}

        d = {v: getattr(self, k) for k, v in _key_map.items()
             if getattr(self, k) is not None}

        if self.region == 'GMS':
            d.pop('region')

        return d

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
        args = {k.strip('_'): v
                if isinstance(v, (int, float))
                else '"{}"'.format(v.replace('"', '\\"'))
                for k, v in self.__dict__.items() if v is not None}
        return '{}({})'.format(type(self).__name__,
                               ', '.join(['{}={}'.format(k, v)
                                          for k, v in args.items()]))


class BeautyItem(Equip):
    """
    Representation of a maplestory/maplestory.io hair or face. Adds HSV
    color attributes to simulate mix coupons

    Attributes
    ----------
    hsv: tuple[Union[int, str, None], ...]
        the hsv value

    """
    def __init__(
            self,
            itemid: Union[int, str],
            version: str,
            region: str = 'GMS',
            name: Optional[str] = None,
            type: Optional[str] = None,
            hsv: tuple[Union[int, str, None], ...] = DEFAULT_HSV
    ):
        super().__init__(itemid, version, region, name, type)
        self.hue = hsv[0]
        self.saturation = hsv[1]
        self.value = hsv[2]

    @classmethod
    def from_equip(
            cls,
            equip: Equip,
            hsv: tuple[Union[int, str, None], ...] = DEFAULT_HSV
    ) -> BeautyItem:
        """
        Create from an existing Equip item

        Parameters
        ----------
        equip: Equip
            the equip item to copy
        hsv: tuple[Union[int, str, None], ...]
            the h, s, v (brightness) values

        Returns
        -------
        BeautyItem
            the new BeautyItem instance

        """
        item = BeautyItem(
            equip.itemid,
            equip.version,
            equip.region,
            equip._name,
            equip.type
        )

        item.hue = hsv[0]
        item.saturation = hsv[1]
        item.value = hsv[2]

        return item

    @property
    def hsv(self):
        return self.hue, self.saturation, self.value

    @hsv.setter
    def hsv(self, val):
        self.hue, self.saturation, self.value = val

    @property
    def brightness(self):
        return self.value

    @brightness.setter
    def brightness(self, val):
        self.value = val

    def to_dict(
            self,
            key_map: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """See Equip. add hue, saturation, value"""
        _key_map = {
            'hue': 'hue',
            'saturation': 'saturation',
            'brightness': 'brightness'
        }
        _key_map.update(key_map or {})
        d = super().to_dict(_key_map)

        # remove if default value
        attrs = ('hue', 'saturation', 'brightness')
        for attr, k in zip(attrs, DEFAULT_HSV._fields):
            if getattr(self, attr) == getattr(DEFAULT_HSV, k):
                d.pop(attr)

        return d
