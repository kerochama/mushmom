"""
Global settings

"""

####################
# CORE             #
####################

# Used to control whether or not original message is deleted
DEBUG = False

BOT_NAME = 'Mushmom'
HOOK_NAME = BOT_NAME

# for embed
EMBED_COLOR = 0xf49c00

# If greater than 9 select reactions will break
MAX_CHARS = 5

# default time to wait for messages that will be deleted
DEFAULT_DELAY = 10


####################
# EMOJIS           #
####################

# Stored on a server. Reference by ID
EMOJI_IDS = {
    'mushshock': 890392463867527228,
    'mushheart': 890978701158809671,
    'mushdab': 890978611803324487,
    'mushping': 890978760780832818,
    'mushparty': 890987908633362503
}

EMOJIS = {
    k: f'https://cdn.discordapp.com/emojis/{v}.png?v=1'
    for k, v in EMOJI_IDS.items()
}

####################
# MONGODB          #
####################

DATABASE = 'mushmom'


####################
# MAPLESTORY.IO    #
####################

MAPLEIO_API = "https://maplestory.io/api"

# this is arbitrary based on time of writing
MAPLEIO_DEFAULT_VERSION = "225"

# see scripts/get_sprite_sizes
MAPLEIO_BODY_HEIGHT = 33
