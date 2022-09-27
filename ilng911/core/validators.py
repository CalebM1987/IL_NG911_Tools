import math
import arcpy
from ilng911.support.munch import munchify, Munch
from ilng911.schemas import DataSchema, DataType
from ilng911.core.common import Feature
from ilng911.env import get_ng911_db
from ilng911.logging import log
from ilng911.core.fields import FIELDS, STREET_FIELDS, ADDRESS_FIELDS
from ilng911.utils import PropIterator, cursors
from typing import Union, List

class VALIDATION_FLAGS(PropIterator):
    __props__ = [
        "ADDRESS_OUTSIDE_RANGE",
        "DUPLICATE_ADDRESS",
        "DUPLICATE_NENA_IDENTIFIER",
        "INVALID_COUNTY",
        'INVALID_STATE',
        "INVALID_ESN",
        "INVALID_INCORPORATED_MUNICIPALITY",
        "INVALID_MSAG",
        "INVALID_PARITY",
        "INVALID_STREET_NAME",
        "INVALID_UNINCORPORATED_MUNICIPALITY",
        "MISSING_NENA_IDENTIFIER",
        "MISSING_STREET_NAME",
        "MISSING_ADDRESS_NUMBER",
        'INVALID_POSTAL_CODE',
        'INVALID_NEIGHBORHOOD',
        'INVALID_ADDITIONAL_CODE'
    ]

    ADDRESS_OUTSIDE_RANGE = 'ADDRESS_OUTSIDE_RANGE'
    DUPLICATE_ADDRESS = 'DUPLICATE_ADDRESS'
    DUPLICATE_NENA_IDENTIFIER = 'DUPLICATE_NENA_IDENTIFIER'
    INVALID_COUNTY = 'INVALID_COUNTY'
    INVALID_STATE='INVALID_STATE'
    INVALID_ESN = 'INVALID_ESN'
    INVALID_INCORPORATED_MUNICIPALITY = 'INVALID_INCORPORATED_MUNICIPALITY'
    INVALID_MSAG = 'INVALID_MSAG'
    INVALID_PARITY = 'INVALID_PARITY'
    INVALID_STREET_NAME = 'INVALID_STREET_NAME'
    INVALID_UNINCORPORATED_MUNICIPALITY = 'INVALID_UNINCORPORATED_MUNICIPALITY'
    MISSING_NENA_IDENTIFIER = 'MISSING_NENA_IDENTIFIER'
    MISSING_STREET_NAME = 'MISSING_STREET_NAME'
    MISSING_ADDRESS_NUMBER = "MISSING_ADDRESS_NUMBER"
    INVALID_POSTAL_CODE = 'INVALID_POSTAL_CODE'
    INVALID_NEIGHBORHOOD='INVALID_NEIGHBORHOOD'
    INVALID_ADDITIONAL_CODE='INVALID_ADDITIONAL_CODE'


# Address Validation workflow psuedo code:
# prerequisites:
#   create validatedAddress table (store already processed addresses)
#   create AddressFlags table (for actual flagged addresses)

# Actual Validation
#   take one address at a time
#   query street according to 

def get_validation_template() -> Munch:
    return munchify(dict(
        zip(
            VALIDATION_FLAGS.__props__, 
            [0] * len(VALIDATION_FLAGS.__props__)
        )  
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

def validate_address(pt: Feature, road: Union[Feature, int]=None):
    validators = get_validation_template()

    ng911_db = get_ng911_db()

    # 1. check for duplicate address
    addressAttrs = [
        ADDRESS_FIELDS.NUMBER_PREFIX,
        ADDRESS_FIELDS.NUMBER,
        ADDRESS_FIELDS.NUMBER_SUFFIX,
        ADDRESS_FIELDS.PRE_MOD,
        ADDRESS_FIELDS.PRE_DIRECTION,
        ADDRESS_FIELDS.PRE_TYPE,
        ADDRESS_FIELDS.PRE_TYPE_SEPERATOR,
        ADDRESS_FIELDS.NAME,
        ADDRESS_FIELDS.POST_TYPE,
        ADDRESS_FIELDS.POST_DIRECTION,
        ADDRESS_FIELDS.POST_MODIFIER,
        ADDRESS_FIELDS.BUILDING,
        ADDRESS_FIELDS.FLOOR,
        ADDRESS_FIELDS.UNIT,
        ADDRESS_FIELDS.SEAT,

    ]
    addSearchAttrs = []

    # set up address layer
    addLyr = arcpy.management.MakeFeatureLayer(ng911_db.addressPoints, 'AddressPoints')
    
    for attr in addressAttrs:
        v = pt.get(attr)
        if v:
            if isinstance(v, str):
                addSearchAttrs.append(f"{attr} = '{v}'")
            else:
                addSearchAttrs.append(f"{attr} = {v}")

    if not addSearchAttrs:
        validators[VALIDATION_FLAGS.MISSING_STREET_NAME] = 1
        validators[VALIDATION_FLAGS.MISSING_ADDRESS_NUMBER]

    else:
        # check for duplicate
        dup_where = ' AND '.join(addSearchAttrs)
        arcpy.management.SelectLayerByAttribute(addLyr, 'NEW_SELECTION', dup_where)
        if int(arcpy.management.GetCount(addLyr).getOutput(0)) > 1:
            validators[VALIDATION_FLAGS.DUPLICATE_ADDRESS] = 1

    # check for missing nena identifier
    nena_id = pt.get(ADDRESS_FIELDS.GUID)
    if not nena_id:
        validators[VALIDATION_FLAGS.MISSING_NENA_IDENTIFIER]
    else:
        # check for duplicate nena identifier
        nena_where = f"{ADDRESS_FIELDS.GUID} = '{nena_id}'"
        arcpy.management.SelectLayerByAttribute(addLyr, 'NEW_SELECTION', nena_where)
        if int(arcpy.management.GetCount(addLyr).getOutput(0)) > 1:
            validators[VALIDATION_FLAGS.DUPLICATE_NENA_IDENTIFIER] = 1
    
    st_attrs = [
        STREET_FIELDS.PRE_TYPE,
        STREET_FIELDS.PRE_TYPE_SEPERATOR,
        STREET_FIELDS.NAME,
        STREET_FIELDS.POST_TYPE,
        STREET_FIELDS.POST_MODIFIER
    ]

    # get block range for given point
    addNum = pt.get('Add_Number', 0)

    # create where clause
    atts = []
    for a in st_attrs:
        v = pt.get(a)
        if v:
            atts.append(f"{a} = '{v}'")

    where_clause = ' AND '.join(atts)
    print('where clause: ', where_clause)

    if not road:

        # get roads layer
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
            arcpy.management.SelectLayerByLocation(roads, 'WITHIN_A_DISTANCE', pt.geometry, '600 FEET', 'SUBSET_SELECTION')
            print('selected by location')
        
        count = int(arcpy.management.GetCount(roads).getOutput(0))
        print(f'count of roads after location search: {count}')
        
        desc = arcpy.Describe(roads)
        fields = [desc.oidFieldName, 'SHAPE@'] + [f.name for f in desc.fields]
        distances = {}
        with arcpy.da.SearchCursor(roads, fields) as rows:
            for r in rows:
                distances[pt.geometry.distanceTo(r[1])] = r

        if not distances:
            raise RuntimeError('No roads found within search radius')

        shortest = min(distances.keys())  
        road = DataSchema(ng911_db.types.ROAD_CENTERLINE).fromRow(fields, distances.get(shortest))
        road.prettyPrint()
                

    else:
        if isinstance(road, int):
            road = DataSchema(DataType.ROAD_CENTERLINE).find_feature_from_oid(road)
        if not isinstance(road, Feature):
            raise RuntimeError(f'Invalid Type for Road Centerline input: "{type(road)}"')
    
    print(road.get('St_Name'), road.get('MSAGComm_R'))

    # get parity and range info
    info = get_range_and_parity(pt.geometry, road)

    if addNum < info.get('from_address') or addNum > info.get('to_address'):
        log(f'address is outside of range: {addNum} ({info.get("from_address")}-{info.get("to_address")})')
        validators.ADDRESS_OUTSIDE_RANGE = 1

    # check parity
    isEven = pt.get('Add_Number', 0) % 2 == 0
    if (info.get('parity') == 'Odd' and isEven) or (info.get('parity') == 'Even' and not isEven):
        validators.INVALID_PARITY = 1

    # check parity based attributes
    parity_checks = [
        [getattr(STREET_FIELDS, f'ESN_{info.side}'), ADDRESS_FIELDS.ESN, 'INVALID_ESN'],
        [getattr(STREET_FIELDS, f'INC_MUNI_{info.side}'), ADDRESS_FIELDS.INC_MUNI, 'INVALID_INCORPORATED_MUNICIPALITY'],
        [getattr(STREET_FIELDS, f'UNINC_MUNI_{info.side}'), ADDRESS_FIELDS.UNINC_MUNI, 'INVALID_UNINCORPORATED_MUNICIPALITY'],
        [getattr(STREET_FIELDS, f'POST_CODE_{info.side}'), ADDRESS_FIELDS.POST_CODE, 'INVALID_POSTAL_CODE'],
        [getattr(STREET_FIELDS, f'MSAG_COM_{info.side}'), ADDRESS_FIELDS.MSAG_COM, 'INVALID_MSAG'],
        [getattr(STREET_FIELDS, f'NEIGHBORHOOD_COM_{info.side}'), ADDRESS_FIELDS.NEIGHBORHOOD_COM, 'INVALID_NEIGHBORHOOD'],
        [getattr(STREET_FIELDS, f'ADD_CODE_{info.side}'), ADDRESS_FIELDS.CODE, 'INVALID_ADDITIONAL_CODE'],
        [getattr(STREET_FIELDS, f'COUNTY_{info.side}'), ADDRESS_FIELDS.COUNTY, 'INVALID_COUNTY'],
        [getattr(STREET_FIELDS, f'STATE_{info.side}'), ADDRESS_FIELDS.STATE, 'INVALID_STATE'],
    ]

    for (roadAttr, addAttr, vf) in parity_checks:
        rv = road.get(roadAttr)
        av = pt.get(addAttr)
        log(f'log address parity check for {addAttr} based on side "{info.side}": {rv} -> {av}')
        if rv != av:
            validators[vf] = 1
            log(f'\tset validation flag warning: "{vf}" to 1')

    # calculate flag count and score
    flagCount = sum(validators.values())
    flagCheckCount = len(VALIDATION_FLAGS.__props__)
    validators['FLAG_COUNT'] = flagCount
    validators['VALIDATION_SCORE'] = (flagCount / flagCheckCount) * 100

    # update validation tables
    base_fields = ['NENA_GUID', 'POINT_OID', 'SHAPE@']
    if flagCount > 0:
        # found some flags, update flags table
        keys = list(validators.keys())
        flag_fields = base_fields + keys  
        with cursors.InsertCursor(ng911_db.addressFlags, flag_fields) as irows:
            r = [nena_id, pt.get(pt.oidField), pt.geometry] + [validators.get(f) for f in keys]
            irows.insertRow(r)
            log(f'added record to addresses flags: {pt.get(pt.oidField)} with flag count of {flagCount}')

    with cursors.InsertCursor(ng911_db.validatedAddresses, base_fields) as irows:
        irows.insertRow([nena_id, pt.get(pt.oidField), pt.geometry])
        log(f'added record to validated addresses: {pt.get(pt.oidField)}')
    print(validators)
    return validators



    
    
    