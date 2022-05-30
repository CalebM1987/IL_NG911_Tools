import os
import sys

is_arc = os.path.basename(sys.executable).startswith('Arc')

NG_911_DIR = os.path.abspath(os.path.dirname(__file__))
from ilng911.core.database import NG911Data
from ilng911.config import load_config

def get_ng911_db(config_file='config.json') -> NG911Data:
    """gets the NG911Data helper instance

    Args:
        config_file (str, optional): the config file name. Defaults to 'config.json'.

    Returns:
        NG911Data: the NG911Data helper instance
    """
    config = load_config(config_file)
    if config:
        return NG911Data(config.get('ng911GDBSchemasPath'))
