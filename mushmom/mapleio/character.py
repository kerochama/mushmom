"""
Representation of a maplestory character.  Attributes stored are those needed
in order to read in and recreate API calls

"""
from __future__ import annotations

import json
from urllib import parse
from aenum import Enum, IntEnum, auto, extend_enum
from typing import Union, Optional, Any, Iterable

from .. import config
from . import resources
from .equip import Equip


class Character:
    """
    Representation of a maplestory/maplestory.io character sprite

    Attributes
    ----------
    name: str
        the characters name
    version: str
        the maplestory version
    region: region
        maplestory region
    skin: Skin
        Enum value of skins from skins.json
    ears: Ears
        Enum value of ears from maplestory.io representation
    equips: list[Equip]
        equips worn by character

    """
    def __init__(
            self,
            name: Optional[str] = None,
            version: Optional[str] = None,
            region: Optional[str] = 'GMS'
    ) -> None:
        self.name = name
        self.version = version or config.mapleio.default_version
        self.region = region

        # can only be populated by from_* funcs
        self.skin = None
        self.ears = None
        self.equips = []

    @classmethod
    def from_json(cls, data: Union[str, dict]) -> Character:
        """
        Parse from maples.im/maplestory.studio json

        Parameters
        ----------
        data: Union[str, dict]
            JSON character data (export from maples.im or
            beta.maplestory.studio)

        Returns
        -------
        Character
            parsed character object

        Notes
        -----
        JSON refers to itemids as `id`

        """
        if isinstance(data, (str, bytes)):
            data = json.loads(data)

        char = Character()
        char.name = data.get('name')
        char.skin = Skin.get(data.get('skin', 2005))  # default green
        char.ears = Ears.get(data.get('mercEars', False),
                             data.get('illiumEars', False),
                             data.get('highFloraEars', False))

        # handle selectedItems
        items = data.get('selectedItems', {})

        if (items and isinstance(items, dict)
                and all(isinstance(v, dict) for v in items.values())):
            item0 = list(items.values())[0]
            char.version = item0.get('version', config.mapleio.default_version)
            char.region = item0.get('region', 'GMS')

            char.equips = [
                Equip(item.get('id', 0),
                      item.get('version', char.version),
                      item.get('region', 'GMS'),
                      item.get('name'))
                for type, item in items.items() if type not in ['Body', 'Head']
            ]

        return char

    @classmethod
    def from_url(cls, url: str) -> Character:
        """
        Parse directly from a preexisting API call/url

        Parameters
        ----------
        url: str
            https://maplestory.io/api/character/...

        Returns
        -------
        Character
            parsed character object

        Notes
        -----
        url refers to itemids as `itemId`

        """
        parsed = parse.urlparse(url)
        query = dict(parse.parse_qsl(parsed.query, keep_blank_values=True))

        char = Character()
        char.name = query.get('name')
        char.ears = Ears.get(query.get('showears', 'false') == 'true',
                             query.get('showLefEars', 'false') == 'true',
                             query.get('showHighLefEars', 'false') == 'true')

        # handle items
        generator = (x for x in parsed.path.split('/') if 'itemId' in x)
        item_str = next(generator, None)
        items = {}

        if item_str:
            try:
                items = json.loads('[{}]'.format(parse.unquote(item_str)))
            except json.decoder.JSONDecodeError:
                pass  # already set to {}

        if items and all(isinstance(v, dict) for v in items):
            item0 = items[0]
            char.version = item0.get('version', config.mapleio.default_version)
            char.region = item0.get('region', 'GMS')

            # identify Body item (id is skinid)
            char.skin = next((Skin.get(x['itemId'])
                              for x in items if Skin.get(x['itemId'])),
                             Skin.GREEN)

            char.equips = [
                Equip(item.get('itemId', 0),
                      item.get('version', char.version),
                      item.get('region', 'GMS'))
                for item in items if Equip.valid_equip(item.get('itemId', 0))
            ]

        return char

    def filtered_equips(
            self,
            keep: Optional[Iterable[str]] = None,
            remove: Optional[Iterable[str]] = None,
            replace: Optional[Iterable[Equip]] = None
    ) -> list[Equip]:
        """
        Filtered equips. Keep is prioritized over remove

        Parameters
        ----------
        keep: Optional[Iterable[str]]
            list of equip types to keep
        remove: Optional[Iterable[str]]
            list of equip types to remove
        replace: Optional[Iterable[Equip]]
            list of equip to overwrite char equips by type

        Returns
        -------
        list[Equip]
            list of equips worn by character

        """
        equips = self.equips

        if keep:
            equips = [equip for equip in self.equips if equip.type in keep]
        elif remove:
            equips = [equip for equip in self.equips if equip.type not in remove]

        for equip in replace or []:
            _iter = (i for i, eq in enumerate(equips) if eq.type == equip.type)
            i = next(_iter, None)
            if i is not None:
                equips[i] = equip

        return equips

    def url(
            self,
            pose: str = 'stand1',
            emotion: str = 'default',
            frame: Union[int, str] = 0,
            zoom: float = 1,
            flipx: bool = False,
            bgcolor: tuple[int, int, int, int] = (0, 0, 0, 0),
            render_mode: Optional[str] = None,
            remove: Optional[Iterable[str]] = None,
            replace: Optional[Iterable[Equip]] = None
    ) -> str:
        """
        Build API call to get char sprite data

        Parameters
        ----------
        pose: str
            pose from poses.json
        emotion: str
            emotion from emotions.json
        frame: Union[int, str]
            the animation frame. animated for gif
        zoom: float
            how zoomed in the image should be (1 = 100%)
        flipx: bool
            whether or not to flip sprite horizontally
        bgcolor: tuple[int, int, int, int]
            rgba color tuple
        render_mode: Optional[str]
            the render mode (e.g. centered, NavelCenter, etc.)
        remove: Optional[Iterable[str]]
            list of equip types to remove
        replace: Optional[Iterable[Equip]]
            list of equip to overwrite char equips by type

        Returns
        -------
        str
            API call to get sprite data (url)

        """
        # format equips. emotion placed in face/face accessory dicts
        items = [
            {'type': 'Body', 'itemId': self.skin.value, 'version': self.version},
            {'type': 'Head', 'itemId': 10000+self.skin.value, 'version': self.version}
        ]

        if self.region != 'GMS':
            items = [dict(item, region=self.region) for item in items]

        for equip in self.filtered_equips(remove=remove, replace=replace):
            equip = equip.to_dict()
            _type = equip.pop('type')

            if _type in ['Face', 'Face Accessory']:
                equip['animationName'] = emotion

            items.append(equip)

        items_s = parse.quote(
            json.dumps(items).lstrip('[').rstrip(']').replace(', ', ',').replace(': ', ':')
        )  # remove brackets and excess whitespace

        # format query
        query = self.ears.to_dict()
        query.update({
            'resize': zoom,
            'flipX': flipx,
            'bgColor': '{},{},{},{}'.format(*bgcolor)
        })
        if render_mode:
            query['renderMode'] = render_mode
        qs = parse.urlencode(
            {k: str(v).lower() for k, v in query.items()}, safe=','
        )  # keep commas

        return f'{config.mapleio.api_url}/character/{items_s}/{pose}/{frame}?{qs}'

    def to_dict(self) -> dict[str, Any]:
        """
        Transform self into a dict. Output can be used as input of a
        new Character instance (stripped down version of JSON)

        Returns
        -------
        dict[str, Any]
            key-value pairs of attributes

        Notes
        -----
        JSON refers to itemids as `id`

        """
        char = {
            'name': self.name,
            'version': self.version,
            'region': self.region,
            'skin': self.skin.value,
            'mercEars': self.ears is Ears.MERCEDES,
            'illiumEars': self.ears is Ears.FLORA,
            'highFloraEars': self.ears is Ears.HIGH_FLORA,
            'selectedItems': {
                eq.type: eq.to_dict(map={'itemId': 'id'}, exclude=['type'])
                for eq in self.equips
            }
        }

        return char

    def __repr__(self):
        return f"Character(name={self.name})"


class Skin(IntEnum):
    """
    Set skin tones. Will be populated after reading in json

    LIGHT = 2000
    ASHEN = 2004
    PALE_PINK = 2010
    ...
    BLUSHING_LAVENDER = 2019

    """
    @property
    def label(self) -> str:
        """
        Human readable version of skin name

        Returns
        -------
        str
            skin label

        """
        return self.name.title().replace('_', ' ')

    @classmethod
    def get(cls, skinid: int) -> Skin:
        """
        Get the Skin enum from id

        Parameters
        ----------
        skinid: int
            the skin id

        Returns
        -------
        Skin
            the associated skin enum

        """
        try:
            skin = cls(skinid)
        except ValueError:
            skin = None

        return skin


# populate Skin enum
for k, v in resources.SKINS.items():
    key = k.upper().replace(' ', '_')  # Pale Pink -> PALE_PINK
    extend_enum(Skin, key, v)


class Ears(Enum):
    """
    maplestory.io ear representation. Can be converted to bools for
    API calls

    """
    REGULAR = auto()
    MERCEDES = auto()  # mercedes
    FLORA = auto()  # illium
    HIGH_FLORA = auto()  # ark, adele

    def to_dict(self) -> dict[str, bool]:
        """
        Convert an enum to a dict

        Returns
        -------
        dict[str, bool]
            maplestory.io dict representation

        """
        """
        Format dict for query string/maplestory.io API call

        :return:
        """
        return {
            'showears': self is Ears.MERCEDES,
            'showLefEars': self is Ears.FLORA,
            'showHighLefEars': self is Ears.HIGH_FLORA
        }

    @classmethod
    def get(cls, showears: bool, showLefEars: bool, showHighLefEars: bool) -> Ears:
        """
        From 3 bools, get the specified Ears enum

        Parameters
        ----------
        showears: bool
            has mercedes ears
        showLefEars: bool
            has flora ears
        showHighLefEars: bool
            has high flora ears

        Returns
        -------
        Ears
            the matching ears enum

        """
        ears = Ears.REGULAR

        if showears:
            ears = Ears.MERCEDES
        elif showLefEars:
            ears = Ears.FLORA
        elif showHighLefEars:
            ears = Ears.HIGH_FLORA

        return ears
