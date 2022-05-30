import os
import glob
from ..utils.json_helpers import load_json, write_json_file
from ..support.munch import munchify, Munch
from typing import Dict, Union

thisDir = os.path.abspath(os.path.dirname(__file__))


def load_config(file_name='config.json') -> Munch:
    """loads the config file

    Args:
        file_name (str, optional): the config file name. Defaults to 'config.json'.

    Returns:
        Munch: the config
    """
    config_file = os.path.join(thisDir, file_name)
    if not os.path.exists(config_file):
        try:
            config_file = glob.glob(os.path.join(thisDir, '*.json'))[0]
        except IndexError:
            return None

    if os.path.exists(config_file):
        return load_json(config_file)

    return None

def write_config(config: Union[Dict, Munch], file_name='config.json'):
    """_summary_

    Args:
        config (Union[Dict, Munch]): _description_
        file_name (str, optional): _description_. Defaults to 'config.json'.
    """
    config_file = os.path.join(thisDir, file_name)

    write_json_file(config, config_file)





