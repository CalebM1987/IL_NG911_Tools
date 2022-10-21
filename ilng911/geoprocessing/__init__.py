import arcpy
import os
import re
import json
from ..schemas import DataSchema
from ..env import get_ng911_db
from ..utils.cursors import find_ws, UpdateCursor
from ..support.munch import munchify
from ..core.address import SKIP_NAMES, STREET_ATTRIBUTES, ADDRESS_ATTRIBUTES
from ..logging import log
from typing import List
import ctypes
try:
    MessageBox = ctypes.windll.user32.MessageBoxW
except:
    MessageBox = arcpy.AddMessage

def debug_window(msg='This is a message', title="Info"):
    MessageBox(None, msg, title, 0)

field_types = dict(
    Date='GPDate',
    String='GPString',
    Integer="GPLong",
    SmallInteger="GPLong", # no matching parameter type for this
    Single="GPDouble", # no gp type for this
    Double="GPDouble"
)

SKIP_TYPES = ('OID', 'Geometry', 'Blob', 'GUID', 'Raster')

SHAPE_FIELD_REGEX = re.compile('^(shape)[.|_]', re.IGNORECASE)


def table_to_params(schema: DataSchema, category: str=None, filters: List[str]=[]):
    """creates tool parameters for fields from a given table

    Args:
        table (str): the source table
        schema (DataSchema): the data schema info

    Returns:
        list[arcpy.Parameter]: the arcpy parameters
    """
    table = schema.table
    shapeType = arcpy.Describe(table).shapeType
    if shapeType == 'Polyline':
        shapeType = 'Line'
    log(f'SHAPETYPE IS: {shapeType}')
    ws = find_ws(table)

    params = [
        # arcpy.Parameter(
        #     name=f'{shapeType}_Geometry',
        #     displayName=f'{shapeType} Geometry',
        #     datatype=f'GP{shapeType}',
        #     direction='Input',
        #     parameterType='Required'
        # )
    ]
    # get ng911_db helper
    ng911_db = get_ng911_db()
    
    fields = [f for f in arcpy.ListFields(table) if f.type not in SKIP_TYPES and f.name not in SKIP_NAMES]
    # filters.extend(f.name for f in schema.customFields)
    for field in fields:
        if not SHAPE_FIELD_REGEX.match(field.name) and field.name not in filters:
            log(f'Creating parameter "{field.name}", required: {field.name in schema.requiredFields}')
            param = arcpy.Parameter(
                name=field.name,
                displayName=field.aliasName,
                datatype=field_types.get(field.type, 'GPString'),
                direction='Input',
                category='Street Info' if field.name in STREET_ATTRIBUTES else category,
                parameterType='Required' if field.name in schema.requiredFields else 'Optional'
            )

            # add filter if necessary
            if field.domain:
                domain = ng911_db.get_domain(field.domain, ws)
                log(f'found domain for param: {field.name}, {field.domain}, {type(domain)}')
                if isinstance(domain, dict):
                    param.filter.list = sorted(list(domain.keys()))
                    # log(f'set filter list: {param.filter.list}')

            if field.defaultValue:
                param.value = field.defaultValue

            params.append(
                param
                # dict(
                #     field=field.name,
                #     fieldType=field.type,
                #     fieldLength=field.length,
                #     defaultValue=field.defaultValue,
                #     domain=field.domain,
                #     param=arcpy.Parameter(
                #         name=field.name,
                #         displayName=field.aliasName,
                #         datatype=field_types.get(field.type, 'GPString'),
                #         direction='Input'
                #     )
                # )
            )
    
    # create output for feature set
    # basename = ng911_db.get_basename(table)
    # featureSet = arcpy.Parameter(
    #     name=f'{basename}_Feature',
    #     displayName=f'{basename} Feature',
    #     datatype='GPFeatureRecordSetLayer',
    #     direction='Output',
    #     parameterType='Derived'
    # )

    # featureSet.value = table
    # params.append(featureSet)

    # testing only for address
    # if shapeType == 'Point':
    #     params[0].value = '-10104222.172, 4864013.569'

    return params #munchify(params)

def log_params(parameters: List[arcpy.Parameter]):
    params = {}
    for p in parameters:
        if p.datatype in ('GPFeatureRecordSetLayer', 'Feature Set', 'GPRecordSet', 'Record Set'):
            try:
                params[p.name] = json.loads(p.value.JSON)
            except Exception as e:
                log(f'failed to get feature set value: ', e)
                params[p.name] = p.valueAsText
        else:
            params[p.name] = p.valueAsText

    try:
        params['user'] = os.getenv('username')
    except:
        pass
    log(f'Input Parameters:\n{json.dumps(params, indent=2)}\n')


def check_for_scratch_gdb(clearRecords=False) -> str:
    """will check for existance of scratch geodatabase, will create if does not already exist.  Note: 
    we cannot 

    Returns:
        str: _description_
    """
    folder = arcpy.env.scratchFolder
    if not os.path.exists(folder):
        os.makedirs(folder)
        log(f'no scratch folder found, created at: "{folder}"')

    # edits_gdb_name = re.sub('[^A-Za-z0-9]+', '-', os.getenv('username') or 'anonymous').replace('__', '-') + '.gdb'
    # edits_gdb = os.path.join(folder, edits_gdb_name)

    # if not arcpy.Exists(edits_gdb):
    #     arcpy.management.CreateFileGDB(folder, edits_gdb_name)
    #     log(f'no scratch folder found, created at: "{folder}"')
    edits_gdb = arcpy.env.scratchGDB
    log(f'scratch geodatabse is: "{edits_gdb}"')

    sketch_points = os.path.join(edits_gdb, 'sketch_points')
    if not arcpy.Exists(sketch_points):
        arcpy.management.CreateFeatureclass(edits_gdb, 'sketch_points', 'POINT')
        arcpy.management.AddField(sketch_points, 'CENTERLINE', 'LONG')
        log('created "sketch_points" feature class')
        
    elif clearRecords:
        # empty rows
        with UpdateCursor(sketch_points, ['OID@']) as rows:
            for r in rows:
                rows.deleteRow()
        log('removed all records from "sketch_points"')

    return edits_gdb