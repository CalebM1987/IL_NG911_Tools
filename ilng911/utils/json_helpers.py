from ..support.munch import munchify
from ..utils import message
import json
import os

def load_json(json_file):
    """loads a json file into a Munch (dict)

    Args:
        json_file (str): the input json file

    Returns:
        Munch: the munchified dict of JSON data
    """
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            return munchify(json.load(f))
    raise IOError(f'JSON file "{json_file}" does not exist.')

def write_json_file(obj, out_file, **kwargs):
    """writes a json file

    Args:
        obj (dict): a python dict or Munch object that will be written to a .json file
        out_file (str): the full path to an output .json file
    """
    if 'indent' not in kwargs:
        kwargs['indent'] = 2
    
    validated_filename = os.path.splitext(out_file)[0] + '.json'
    with open(validated_filename, 'w') as f:
        json.dump(obj, f, **kwargs)
    message(f'Created json file: "{out_file}"')
    return validated_filename