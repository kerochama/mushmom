import json
import importlib.resources
from urllib import parse
from aenum import Enum, IntEnum, auto, extend_enum

from mushmom import config
from mushmom.mapleio.equip import Equip, equip_type, valid_equip
from mushmom.mapleio import resources


class Character:
    def __init__(self, name="", version=""):
        """
        Keep track of equips and sprite settings

        """

        self.name = name

        # can only be populated by from_* funcs
        self.version = version or config.MAPLEIO_DEFAULT_VERSION
        self.skin = None
        self.ears = None
        self.equips = []

    @classmethod
    def from_json(cls, data):
        """
        Parse from maples.im/maplestory.studio json

        :param data: json string or dict
        :return:
        """
        if isinstance(data, (str, bytes)):
            data = json.loads(data)

        char = Character()
        char.name = data['name']
        char.version = list(data['selectedItems'].values())[0]['version']  # use first
        char.skin = Skin.get(data['skin'])
        char.ears = Ears.get(data['mercEars'], data['illiumEars'], data['highFloraEars'])
        char.equips = [
            Equip(item['id'], item['version'], item['name'])
            for type, item in data['selectedItems'].items()
            if type not in ['Body', 'Head']
        ]

        return char

    @classmethod
    def from_url(cls, url):
        """
        Parse directly from a preexisting API call

        :param url:
        :return:
        """
        parsed = parse.urlparse(url)
        item_str = next(x for x in parsed.path.split('/') if 'itemId' in x)
        items = json.loads('[{}]'.format(parse.unquote(item_str)))
        query = dict(parse.parse_qsl(parsed.query, keep_blank_values=True))

        char = Character()
        char.name = query['name']
        char.version = items[0]['version']
        char.ears = Ears.get(query['showears'] == 'true', query['showLefEars'] == 'true',
                             query['showHighLefEars'] == 'true')

        # identify Body item (id is skinid)
        item = next((x for x in items if Skin.get(x['itemId'])), Skin.GREEN)

        char.equips = [
            Equip(item['itemId'], item['version'])
            for item in items if valid_equip(item['itemId'])
        ]

        return char

    def filter(self, keep=None, remove=None):
        """
        Keep is prioritized over remove

        :param keep:
        :param remove:
        :return:
        """
        if keep:
            return [equip for equip in self.equips if equip.type in keep]
        elif remove:
            return [equip for equip in self.equips if equip.type not in remove]

        return self.equips

    def item_dicts(self, keep=None, remove=None):
        """
        Equipment dicts formatted for API call

        :return:
        """
        # build Body and Head
        equips = [
            {'type': 'Body', 'itemId': self.skin.value, 'version': self.version},
            {'type': 'Head', 'itemId': 10000+self.skin.value, 'version': self.version}
        ]

        for equip in self.filter(keep, remove):
            equips.append(equip.to_dict())

        return equips

    def url(self, pose='stand1', emotion='default',
            zoom=1, flipx=False, bgcolor=(0, 0, 0, 0), remove=None):
        """
        Build API call to get char sprite data

        :param pose:
        :param emotion:
        :param zoom:
        :param flipx:
        :param bgcolor:
        :param remove:
        :return:
        """
        # format equips. emotion placed in face/face accessory dicts
        items = []

        for item in self.item_dicts(remove=remove):
            i = item.copy()

            if i['type'] in ['Face', 'Face Accessory']:
                i['animationName'] = emotion

            i.pop('type')
            items.append(i)

        items_s = parse.quote(
            json.dumps(items).lstrip('[').rstrip(']').replace(', ', ',').replace(': ', ':')
        )  # remove brackets and excess whitespace

        # format query
        query = self.ears.to_dict()
        query.update({
            'resize': zoom, 'flipX': flipx, 'bgColor': '{},{},{},{}'.format(*bgcolor)
        })
        qs = parse.urlencode(
            {k: str(v).lower() for k, v in query.items()}, safe=','
        )  # keep commas

        return f'{config.MAPLEIO_API}/character/{items_s}/{pose}/0?{qs}'

    def to_dict(self):
        """

        :return:
        """
        char = {
            'name': self.name,
            'version': self.version,
            'skin': self.skin.value,
            'mercEars': self.ears is Ears.MERCEDES,
            'illiumEars': self.ears is Ears.FLORA,
            'highFloraEars': self.ears is Ears.HIGH_FLORA,
            'selectedItems': {}
        }
        
        for equip in self.equips:
            subcat = equip_type(equip.itemid)
            char['selectedItems'][subcat] = {
                "id": equip.itemid,
                "version": equip.version,
                "name": equip._name  # no need to make API call
            }

        return char

    def __repr__(self):
        return f"Character(name={self.name})"


class Skin(IntEnum):
    """
    Set skin tones. Will be populated after reading in json

    e.g.

    LIGHT = 2000
    ASHEN = 2004
    PALE_PINK = 2010
    ...
    BLUSHING_LAVENDER = 2019

    """
    @property
    def label(self):
        return self.name.title().replace('_', ' ')

    @classmethod
    def get(cls, skinid):
        try:
            skin = cls(skinid)
        except ValueError:
            skin = None

        return skin


# populate Skin enum
_skins_json = importlib.resources.read_text(resources, 'skins.json')
_skins_dict = {k.upper().replace(' ', '_'): v  # Pale Pink -> PALE_PINK
               for k, v in json.loads(_skins_json).items()}

for k, v in _skins_dict.items():
    extend_enum(Skin, k, v)


class Ears(Enum):
    REGULAR = auto()
    MERCEDES = auto()  # mercedes
    FLORA = auto()  # illium
    HIGH_FLORA = auto()  # ark, adele

    def to_dict(self):
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
    def get(cls, showears, showLefEars, showHighLefEars):
        """
        From 3 flags return the correct enum

        :param showears:
        :param showLefEars:
        :param showHighLefEars:
        :return:
        """
        ears = Ears.REGULAR

        if showears:
            ears = Ears.MERCEDES
        elif showLefEars:
            ears = Ears.FLORA
        elif showHighLefEars:
            ears = Ears.HIGH_FLORA

        return ears
