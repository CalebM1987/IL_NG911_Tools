import arcpy
from ..env import get_ng911_db
from ..support.munch import munchify


def create_fields_table():
    for tab in ng911_db.requiredTables:
        schema = ng911_db.load_911_schema(tab.type)
        