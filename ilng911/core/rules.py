import os
import arcpy
from ilng911.utils.helpers import find_nena_guid_field, get_next_nena_id
from ilng911.logging import log

NENA_ID_CALC = """var id = NextSequenceValue("AddressPointsSequence");
return `SITE${id}@casscomm.com`;"""

def add_attribute_rules(path, nena_prefix='SITE'):
    desc = arcpy.Describe(path)
    if not desc.hasGlobalID:
        log('no global IDs detected, attempting to add now')
        try:
            arcpy.management.AddGlobalIDs(path)
        except Exception as e:
            log(f'failed to add global IDs: {e}')
        raise RuntimeError('the table does not have a GlobalID field, please add GlobalIDs before running this tool')

    field_names = [f.name for f in desc.fields]
    guid_field = find_nena_guid_field(path)

    # add nena identfier attribute rule
    basename = os.path.basename(desc.catalogPath)
    if '.' in basename:
        if basename.endswith('.shp'):
            basename = os.path.splitext(basename)[0]
        else:
            # is sde feature class?
            basename = basename.split('.')[-1]

    if guid_field:
        nena_exp = '\n'.join([
            f'var id = NextSequenceValue("{basename}Sequence");'
            'return `%s${id}@casscomm.com`;' %nena_prefix
        ])
        arcpy.management.AddAttributeRule(
            path,
            f"{basename}NENAID", 
            "CALCULATION", 
            nena_exp, 
            "EDITABLE", 
            triggering_events='INSERT', 
            field=guid_field, 
            exclude_from_client_evaluation='EXCLUDE'
        )
        log(f'added NENA identifier attribute rule')

    # add DateUpdate
    if 'DateUpdate' in field_names:
        arcpy.management.AddAttributeRule(
        path,
            f"{basename}DateUpdate", 
            "CALCULATION", 
            'Date()', 
            "EDITABLE", 
            triggering_events='INSERT;UPDATE', 
            field=guid_field, 
            exclude_from_client_evaluation='EXCLUDE'
        )
        log(f'added DateUpdate attribute rule')