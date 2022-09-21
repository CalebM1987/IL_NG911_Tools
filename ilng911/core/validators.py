import math
from enum import Enum
from ilng911.support.munch import munchify, Munch
from ilng911.core.common import Feature

class VALIDATION_FLAGS(Enum):
    DUPLICATE_ADDRESS = 1
    ADDRESS_OUTSIDE_RANGE = 2
    INVALID_PARITY = 3
    DUPLICATE_NENA_IDENTIFIER = 4
    MISSING_NENA_IDENTIFIER = 5
    INVALID_STREET_NAME = 6
    INVALID_MSAG = 7
    INVALID_INCORPORATED_MUNICIPALITY = 8
    INVALID_UNINCORPORATED_MUNICIPALITY = 9
    INVALID_COUNTY = 10
    INVALID_ESN = 11
    MISSING_STREET_NAME = 12




# Address Validation workflow psuedo code:
# prerequisites:
#   create validatedAddress table (store already processed addresses)
#   create AddressFlags table (for actual flagged addresses)

# Actual Validation
#   take one address at a time
#   query street according to 

def get_validation_template() -> Munch:
    return munchify(dict(
        DUPLICATE_ADDRESS = 0,
        ADDRESS_OUTSIDE_RANGE = 0,
        INVALID_PARITY = 0,
        DUPLICATE_NENA_IDENTIFIER = 0,
        MISSING_NENA_IDENTIFIER = 0,
        INVALID_STREET_NAME = 0,
        INVALID_MSAG = 0,
        INVALID_INCORPORATED_MUNICIPALITY = 0,
        INVALID_UNINCORPORATED_MUNICIPALITY = 0,
        INVALID_COUNTY = 0,
        INVALID_ESN = 0,
        MISSING_STREET_NAME = 0,
    ))

def validate_address(pt: Feature):
    validators = get_validation_template()
    par_attr_bases = [
        'MSAGComm_',
        'IncMuni_',
        'UnincCom_',
        'PostCode_'
    ]
    par_attrs = [f'{b}{p}' for p in ['L', 'R'] for b in par_attr_bases]
    st_attrs = [
        'St_PreMod', 
        'St_PreDir', 
        'St_PreTyp', 
        'St_PreSep', 
        'St_Name', 
        'St_PosTyp', 
        'St_PosDir', 
        'St_PosMod', 
    ]
    range_bases = ['ToAddr_', 'FromAddr_']
    range_attrs = [f'{b}{p}' for p in ['L', 'R'] for b in range_bases]

    # get block range for given point
    addNum = pt.get('Add_Number', 0)

    blockFloor = math.floor(addNum / 100.0) * 100
    blockCeil = math.ceil(addNum / 100.0) * 100
    atts = []
    for a in st_attrs:
        v = pt.get(a)
        if v:
            atts.append(f"{a} = '{v}'")

    # make sure to only query this block
    for a in range_attrs:
        if a.startswith('To'):
            atts.append(f'{a} >= blockFloor')
        else:
            atts.append(f'{a} < blockCeil')

    where_clause = ' AND '.join(atts)