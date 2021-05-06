import arcpy
from ..env import ng911_db
from typing import Union
from ..core.common import Feature, FeatureHelper
from ..schemas import DataType
from warnings import warn


STREET_ATTRIBUTES = [
    'St_PreMod', 'St_PreDir', 'St_PreTyp', 'St_PreSep', 'St_Name', 'St_PosTyp', 
    'St_PosDir', 'St_PosMod', 'LSt_PreDir', 'LSt_Name', 'LSt_Type', 'LSt_PosDir'
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
    'Elev', 
    'GC_Address_wZIP', 
    'GC_Address_wMSAGCOMM'
]

DATE_FIELDS = [
    'DateUpdate',
    'Effective',
    'Expire'
]

def merge_street_segment_attributes(address: Feature, centerline: Union[int, Feature]):
    centerlineTab = ng911_db.get_911_table(DataType.ROAD_CENTERLINE)
    centerlineSchema = ng911_db.load_911_schema(DataType.ROAD_CENTERLINE)

    # get matching fields
    fields = arcpy.ListFields(centerlineTab)
    matchFields = STREET_ATTRIBUTES[:]
    for f in fields:
        # also add any matching custom fields?
        if f.name not in (SKIP_NAMES + DATE_FIELDS + STREET_ATTRIBUTES) and f.name in address.fieldNames:
            matchFields.append(f.name)

    # if OBJECTID is provided for centerline, fetch attributes and merge
    if isinstance(centerline, int):
        oidField = [f.name for f in fields if f.type == 'OID'][0]
        where = f'{oidField} = {centerline}'
        
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

    
        



def get_zip_code(pt: arcpy.Point) -> str:
    """gets a zip code from a given point, using authoritative data from the USPS

    see: https://www.arcgis.com/home/item.html?id=8d2012a2016e484dafaac0451f9aea24

    Args:
        pt (arcpy.Point): an arcpy Point geometry

    Returns:
        str: the intersecting zip code used by the USPS
    """
    pass

# def extract_street_info(oid: number)

if __name__ == '__main__':
    # sample point 205 MAIN
    x, y = -10104222.172, 4864013.569


