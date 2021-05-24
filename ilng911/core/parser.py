import re
from .fields import FIELDS
from ..support.munch import munchify

class STREET_DIRECTIONS_ABBR:
    NORTH='N'
    NORTHEAST='NE'
    NORTHWEST='NW'
    SOUTH='S'
    SOUTHEAST='SE'
    SOUTHWEST='SW'
    EAST='E'
    WEST='W'

class CUSTOM_TOKENS:
    PreDirectionAbbr = 'PreDirectionAbbr'
    PostDirectionAbbr = 'PostDirectionAbbr'
    StreetTypeAbbr = 'StreetTypeAbbr'

def get_string_tokens(s: str):
    return re.findall(r"(\{.*?\})", s)



    

