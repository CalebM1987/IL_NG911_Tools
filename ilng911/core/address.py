import os
import arcpy
import json
import math
from ..env import get_ng911_db
from ..support.munch import munchify, Munch
from typing import Union, Dict, List
from ..core.common import Feature
from ..core.geometry import get_angle
from ..schemas import DataType, DataSchema
from .validators import get_range_and_parity, validate_address
from warnings import warn
from itertools import zip_longest
from .fields import FIELDS, POINT_SIDE_MAPPING
from ..logging import log

thisDir = os.path.abspath(os.path.dirname(__file__))

FALLBACK_ZIP_CODES = os.path.join(os.path.dirname(thisDir), 'data', 'il_zip_codes.shp')

STREET_ATTRIBUTES = [
    'St_PreMod', 
    'St_PreDir', 
    'St_PreTyp', 
    'St_PreSep', 
    'St_Name', 
    'St_PosTyp', 
    'St_PosDir', 
    'St_PosMod', 
    'LSt_PreDir', 
    'LSt_Name', 
    'LSt_Type', 
    'LSt_PosDir'
]

ADDRESS_ATTRIBUTES = [
    'AddCode', 
    'AddDataURI', 
    'Nbrhd_Comm', 
    'AddNum_Pre', 
    'Add_Number', 
    'AddNum_Suf', 
    'ESN', 
    'Building',
    'Floor', 
    'Unit', 
    'Room', 
    'Seat', 
    'Addtl_Loc', 
    'LandmkName', 
    'Mile_Post', 
    'Place_Type', 
    'Placement'
]

SKIP_NAMES = [
    'DateUpdate',
    "DiscrpAgID",
    "RCL_NGUID",
    "Site_NGUID",
    'Uninc_Comm',   
    # COMMUNITY NAMES
    'Inc_Muni', 
    'MSAGComm', 
    'Post_Comm', 
    'Post_Code', 
    'Post_Code4',
    "Country",
    "State",
    "County",
    'Long', 
    'Lat', 
    'Elev'
]

DATE_FIELDS = [
    'DateUpdate',
    'Effective',
    'Expire'
]




def merge_street_segment_attributes(address: Feature, centerline: Union[int, Feature]):
    """merge street segment attributes into address point feature

    Args:
        address (Feature): an address Feature
        centerline (Union[int, Feature]): a centerline OBJECTID or Feature

    Returns:
        Feature: the address Feature
    """
    centerlineSchema = DataSchema(DataType.ROAD_CENTERLINE)
    centerlineTab = centerlineSchema.table

    # get matching fields
    fields = arcpy.ListFields(centerlineTab)
    matchFields = STREET_ATTRIBUTES[:]
    for f in fields:
        # also add any matching custom fields?
        if f.name not in (SKIP_NAMES + DATE_FIELDS + STREET_ATTRIBUTES) and f.name in address.fieldNames and f.editable:
            matchFields.append(f.name)

    # if OBJECTID is provided for centerline, fetch attributes and merge
    if isinstance(centerline, int):
        centerline = centerlineSchema.find_feature_from_oid(centerline)

    # merge from Feature
    if isinstance(centerline, Feature):
        log('centerline is a Feature, extracting point attributes now')
        attrs = {f: centerline.get(f) for f in matchFields}

        # set MSAG, IncMuni and UnincorpMuni from side
        info = get_range_and_parity(address.geometry, centerline)
        log(f'extracted parity and range info:\n{json.dumps(info, indent=4)}')
        if info.side: 
            for mapping in POINT_SIDE_MAPPING:
                ptAttr = mapping['pt']
                lnAttr = f"{mapping['ln']}_{info.side}"
                attrs[ptAttr] = centerline.get(lnAttr)
                log(f'Extracted value from "{lnAttr}" to "{ptAttr}": "{attrs[ptAttr]}" based on side "{info.side}"')
            

        # check for Inc_Muni, if not use location to get
        if not attrs.get('Inc_Muni'):
            log('did not find incorporated city limits from centerline, attempting to extract from location.')
            attrs.update(**get_city_limits(address.geometry))
        
        address.update(**attrs)

    return address

def get_zip_code(pt: arcpy.PointGeometry) -> Dict[str, str]:
    """gets a zip code from a given point, using authoritative data from the USPS

    see: https://www.arcgis.com/home/item.html?id=8d2012a2016e484dafaac0451f9aea24

    Args:
        pt (arcpy.PointGeometry): an arcpy Point geometry

    Returns:
        str: the intersecting zip code used by the USPS
    """
    # get ng911_db helper
    ng911_db = get_ng911_db()
    zipLyr = ng911_db.get_911_layer(DataType.ZIP_CODES)
    arcpy.management.SelectLayerByLocation(zipLyr, 'INTERSECT', pt)
    count = arcpy.management.GetCount(zipLyr).getOutput(0)
    if count:
        # get zip code and zip code 4
        with arcpy.da.SearchCursor(zipLyr, ['ZipCode', 'ZipCode4']) as rows:
            for row in rows:
                return dict(zip(['Post_Code', 'Post_Code4'], row))

    # use fallback
    fallback = arcpy.management.MakeFeatureLayer(FALLBACK_ZIP_CODES).getOutput(0)
    log(f'using fallback zip codes {fallback} -> {fallback.dataSource}')
    
    arcpy.management.SelectLayerByLocation(fallback, 'INTERSECT', pt)
    with arcpy.da.SearchCursor(fallback, ['ZIP_CODE']) as rows:
        for row in rows:
            return dict(zip(['Post_Code', 'Post_Code4'], row + (None,)))

    return { 'Post_Code': None, 'Post_Code4': None }

def get_city_limits(pt: arcpy.PointGeometry) -> Dict[str, str]:
    """gets the city limits for a given point

    Args:
        pt (arcpy.PointGeometry): [description]

    Returns:
        Dict[str, str]: [description]
    """
    # get ng911_db helper
    ng911_db = get_ng911_db()
    incLyr = ng911_db.get_911_layer(DataType.INCORPORATED_MUNICIPAL)
    uniLyr = ng911_db.get_911_layer(DataType.UNINCORPORATED_MUNICIPAL)
    attrs = dict(
        Inc_Muni='UNINCORPORATED',
        Uninc_Comm=None
    )

    types = [(incLyr, 'Inc_Muni'), (uniLyr, 'Uninc_Comm')]
    for lyr, field in types:
        arcpy.management.SelectLayerByLocation(lyr, 'INTERSECT', pt)
        with arcpy.da.SearchCursor(lyr, [ field ]) as rows:
            for r in rows:
                attrs[field] = r[0]
                break # in case there are more than one?
    return attrs


def create_address_point(pg: arcpy.PointGeometry, centerlineOID: int, **kwargs):
    """creates an address point

    Args:
        pg (arcpy.PointGeometry): [description]
        centerlineOID (int): [description]
    """
    schema = DataSchema(DataType.ADDRESS_POINTS)
    kwargs.update(**get_zip_code(pg))
    # kwargs.update(**get_city_limits(pg))
    ft = schema.create_feature(pg, **kwargs)
    merge_street_segment_attributes(ft, centerlineOID)
    schema.calculate_custom_fields(ft)
    schema.calculate_vendor_fields(ft)
    schema.commit_features()
    return ft, schema

def find_closest_centerlines(pg: Union[arcpy.Geometry, Feature]) -> Dict:
    """finds the closest road centerlines from a given point

    Args:
        pg (Union[arcpy.Geometry, Feature]): _description_

    Returns:
        Dict: _description_
    """
    if isinstance(pg, Feature):
        pg = pg.geometry

    # get ng911_db helper
    ng911_db = get_ng911_db()
    roads_lyr = ng911_db.get_911_layer(DataType.ROAD_CENTERLINE)
    distances = [200, 500, 1000, 3000]
    for dist in distances:
        arcpy.management.SelectLayerByLocation(roads_lyr, 'WITHIN_A_DISTANCE', pg, search_distance=f'{dist} FEET')
        count = int(arcpy.management.GetCount(roads_lyr).getOutput(0))
        log(f'selected {count} roads within a distance of {dist} ft to the new address point')
        if count:
            break

    fields = ['SHAPE@', 'OID@', 'St_Name', 'St_PosTyp', 'FromAddr_L', 'ToAddr_L',  'FromAddr_R', 'ToAddr_R']
    # f'{min(r[4:])} - {max(r[4:])}' #range
    roads = []
    with arcpy.da.SearchCursor(roads_lyr, fields) as rows:
        for r in rows:
            attrs = dict(zip(fields[1:], r[1:]))
            # get distance (will be in DD)
            attrs['distance'] = pg.distanceTo(r[0])
            attrs['block'] =  round(list(filter(None, r[4:]) or [0])[0], -2)
            attrs['range'] = f'{min(r[4:])} - {max(r[4:])}'
            roads.append(munchify(attrs))
    
    if len(roads) == 1:
        return roads

    closest = []
    # find unique roads
    unique = {}
    for r in roads:
        st = f'{r.St_Name} {r.St_PosTyp}'
        if st in unique:
            unique[st].append(r) 
        else:
            unique[st] = [r]
    
    for rd in unique.keys():
        rds = unique[rd]
        min_dist = min(r.distance for r in rds)
        log(f'distance to closest segment of "{rd}" is {min_dist}')
        closest.append([r for r in rds if r.distance == min_dist][0])

    return sorted(closest, key=lambda d: d['distance'])

    
if __name__ == '__main__':
    # sample point 205 MAIN
    x, y = -10104222.172, 4864013.569



