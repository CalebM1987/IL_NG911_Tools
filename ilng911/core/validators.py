import math
import arcpy
from enum import Enum
from ilng911.support.munch import munchify, Munch
from ilng911.schemas import DataSchema
from ilng911.core.common import Feature
from ilng911.env import get_ng911_db
from ilng911.logging import log

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

def get_range_and_parity(pt: Union[arcpy.PointGeometry, Feature], centerline: Union[int, Feature]) -> Munch:
    """finds address range and parity from a given street centerline Feature or OID

    Args:
        pt (Union[arcpy.PointGeometry, Feature]): a point geometry or address Feature
        centerline (Union[int, Feature]): an OBJECTID of the street centerline or centerline Feature

    Returns:
        Munch: a d
    """
    log('parity and range args: ', pt, centerline)
    attrs = dict(
        parity = None,
        to_address=None,
        from_address=None,
        address_prefix=None,
        side=None
    )
    flds = FIELDS.STREET
    
    if isinstance(pt, Feature):
        pt = pt.geometry
        log(f'parity and range, point geometry is: {pt}')

    if isinstance(centerline, int):
        schema = DataSchema(DataType.ROAD_CENTERLINE)
        centerline = schema.find_feature_from_oid(centerline)
        
    # make sure we have a valid feature
    if isinstance(centerline, Feature):
        log('range and parity, centerline is a Feature')
        # angle = get_angle(centerline.geometry)
        line = centerline.geometry
        log(f'parity and range, centerline geometry is: {pt}')
        pq = line.queryPointAndDistance(pt)
        side = 'R' if pq[-1] else 'L'
        parity = centerline.get(f'Parity_{side}')
        attrs['parity'] = parity
        attrs['side'] = side
        attrs['address_prefix'] = centerline.get(flds.ADDRESS_PREFIX_RIGHT if side == 'R' else flds.ADDRESS_PREFIX_LEFT)
        attrs['to_address'] = centerline.get(flds.TO_ADDRESS_RIGHT if side == 'R' else flds.TO_ADDRESS_LEFT)
        attrs['from_address'] = centerline.get(flds.FROM_ADDRESS_RIGHT if side == 'R' else flds.FROM_ADDRESS_LEFT)
    
    return munchify(attrs)

def validate_address(pt: Feature):
    validators = get_validation_template()
    
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
            atts.append(f'{a} >= {blockFloor}')
        else:
            atts.append(f'{a} < {blockCeil}')

    where_clause = ' AND '.join(atts)
    print('where clause: ', where_clause)

    # get roads layer
    ng911_db = get_ng911_db()
    print('got gdb')
    roads = arcpy.management.MakeFeatureLayer(ng911_db.roadCenterlines, 'RoadCenterlines', where_clause)
    # arcpy.management.SelectLayerByAttribute(roads, 'NEW_SELECTION', where_clause)
    print('got layer')

    count = int(arcpy.management.GetCount(roads).getOutput(0))
    print(f'count of roads matching search criteria: {count}')
    if not count:
        # no matching roads?
        return # for now...

    if count > 1:
        # first select by location
        arcpy.management.SelectLayerByLocation(roads, 'WITHIN_A_DISTANCE', pt.geometry, '700 FEET', 'SUBSET_SELECTION')
        print('selected by location')
    
    desc = arcpy.Describe(roads)
    fields = [desc.oidFieldName, 'SHAPE@'] + [f.name for f in desc.fields]
    with arcpy.da.SearchCursor(roads, fields) as rows:
        for r in rows:
            road = DataSchema(ng911_db.types.ROAD_CENTERLINE).fromRow(fields, r)
            road.prettyPrint()
            break

    print(road.get('St_Name'), road.get('MSAGComm_R'))
    
    # DUPLICATE_ADDRESS = 1
    # ADDRESS_OUTSIDE_RANGE = 2
    # INVALID_PARITY = 3
    # DUPLICATE_NENA_IDENTIFIER = 4
    # MISSING_NENA_IDENTIFIER = 5
    # INVALID_STREET_NAME = 6
    # INVALID_MSAG = 7
    # INVALID_INCORPORATED_MUNICIPALITY = 8
    # INVALID_UNINCORPORATED_MUNICIPALITY = 9
    # INVALID_COUNTY = 10
    # INVALID_ESN = 11
    # MISSING_STREET_NAME = 12

    info = get_range_and_parity(pt.geometry, road)

    # check parity
    isEven = pt.get('Add_Number', 0) % 2 == 0
    if (info.get('parity') == 'Odd' and isEven) or (info.get('parity') == 'Even' and not isEven):
        validators.INVALID_PARITY = 1

    # check parity based attributes
    par_attr_bases = [
        'MSAGComm_',
        'IncMuni_',
        'UnincCom_',
        'PostCode_'
    ]
    par_attrs = [f'{p}{info.get("side")}' for p in par_attr_bases]
    
    