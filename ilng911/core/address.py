import os
import arcpy
from ..env import get_ng911_db
from ..support.munch import munchify, Munch
from typing import Union, Dict, List
from ..core.common import Feature
from ..core.geometry import get_angle
from ..schemas import DataType, DataSchema
from warnings import warn
from itertools import zip_longest
from .fields import FIELDS
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
        oidField = [f.name for f in fields if f.type == 'OID'][0]
        where = f'{oidField} = {centerline}'
        log(f'matchFields: {matchFields}')
        with arcpy.da.SearchCursor(centerlineTab, matchFields, where) as rows:
            try:
                row = [r for r in rows][0]
                address.update(**dict(zip(matchFields, row)))
            except IndexError:
                warn(f'WARNING: Road Centerline with {oidField} {centerline} does not exist, failed to merge street attributes.')
                
    # merge from Feature
    elif isinstance(centerline, Feature):
        attrs = {f: centerline.get(f) for f in matchFields}
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

def get_range_and_parity(pt: Union[arcpy.PointGeometry, Feature], centerline: Union[int, Feature]) -> Munch:
    """finds address range and parity from a given street centerline Feature or OID

    Args:
        pt (Union[arcpy.PointGeometry, Feature]): a point geometry or address Feature
        centerline (Union[int, Feature]): an OBJECTID of the street centerline or centerline Feature

    Returns:
        Munch: a d
    """
    attrs = dict(
        parity = None,
        to_address=None,
        from_address=None,
        address_prefix=None,
        side=None
    )
    if isinstance(pt, Feature):
        pt = pt.geometry

    if isinstance(centerline, int):
        schema = DataSchema(DataType.ROAD_CENTERLINE)
        flds = FIELDS.STREET
        where = f'{schema.oidField} = {centerline}'
        fields = schema.fieldNames + ['SHAPE@']
        with arcpy.da.SearchCursor(schema.table, fields, where) as rows:
            for r in rows:
                centerline = schema.fromRow(fields, r)
        
        # make sure we have a valid feature
        if isinstance(centerline, Feature):
            # angle = get_angle(centerline.geometry)
            line = centerline.geometry
            pq = line.queryPointAndDistance(pt)
            side = 'R' if pq[-1] else 'L'
            parity = centerline.get(f'Parity_{side}')
            attrs['parity'] = parity
            attrs['side'] = side
            attrs['address_prefix'] = centerline.get(flds.ADDRESS_PREFIX_RIGHT if side == 'R' else flds.ADDRESS_PREFIX_LEFT)
            attrs['to_address'] = centerline.get(flds.TO_ADDRESS_RIGHT if side == 'R' else flds.TO_ADDRESS_LEFT)
            attrs['from_address'] = centerline.get(flds.FROM_ADDRESS_RIGHT if side == 'R' else flds.FROM_ADDRESS_LEFT)
    
    return munchify(attrs)


def create_address_point(pg: arcpy.PointGeometry, centerlineOID: int, **kwargs):
    """creates an address point

    Args:
        pg (arcpy.PointGeometry): [description]
        centerlineOID (int): [description]
    """
    schema = DataSchema(DataType.ADDRESS_POINTS)
    kwargs.update(**get_zip_code(pg))
    kwargs.update(**get_city_limits(pg))
    ft = schema.create_feature(pg, **kwargs)
    merge_street_segment_attributes(ft, centerlineOID)
    schema.calculate_custom_fields(ft)
    schema.commit_features()
    return ft, schema

if __name__ == '__main__':
    # sample point 205 MAIN
    x, y = -10104222.172, 4864013.569


