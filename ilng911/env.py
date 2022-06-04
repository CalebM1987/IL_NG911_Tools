import os
import sys
import arcpy

NG_911_DIR = os.path.abspath(os.path.dirname(__file__))
from ilng911.core.database import NG911Data
from ilng911.utils import is_arc

# can set mode to 'DEBUG' to save temporary outputs to disk
MODE = os.getenv('NG911_DEBUG_MODE', 'INFO')

DEBUG_WS = os.path.join(os.path.expanduser('~'), 'Documents', 'ng911_temp.gdb')
SCRATCH_WS = DEBUG_WS if MODE == 'DEBUG' else 'in_memory'

if MODE == 'DEBUG' and SCRATCH_WS != 'in_memory' and not arcpy.Exists(DEBUG_WS):
    arcpy.management.CreateFileGDB(*os.path.split(SCRATCH_WS))

def get_ng911_db(config_file='config.json') -> NG911Data:
    """gets the NG911Data helper instance

    Args:
        config_file (str, optional): the config file name. Defaults to 'config.json'.

    Returns:
        NG911Data: the NG911Data helper instance
    """
    return NG911Data(config_file)
