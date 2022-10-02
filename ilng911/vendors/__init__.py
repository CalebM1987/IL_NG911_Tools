import os
from ilng911.utils.json_helpers import load_json
from ilng911.env import NG_911_DIR

vendors_dir = os.path.join(NG_911_DIR, 'vendors')

def load_vendor_config_file():
    schemas_file = os.path.join(vendors_dir, 'schemas.json')
    if not os.path.exists(schemas_file):
        raise RuntimeError('CAD Vendors Schema Fiel does not exist')

    return load_json(schemas_file)


def load_vendor_config(name='TRITECH'):
    vendor_conf = load_vendor_config_file()
    try:
        return [v for v in vendor_conf if v.get('vendor') == name.upper()][0]
    except IndexError:
        raise RuntimeError(f'Invalid Vendor Name Supplied: "{name}"')

