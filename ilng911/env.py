import os
import sys

NG_911_DIR = os.path.abspath(os.path.dirname(__file__))
from ilng911.core.database import NG911Data
from ilng911.utils import is_arc

def get_ng911_db(config_file='config.json') -> NG911Data:
    """gets the NG911Data helper instance

    Args:
        config_file (str, optional): the config file name. Defaults to 'config.json'.

    Returns:
        NG911Data: the NG911Data helper instance
    """
    return NG911Data(config_file)
