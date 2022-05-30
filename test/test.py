import os
import sys
import arcpy
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.admin.schemas import features_from_json, create_ng911_admin_gdb
from ilng911.env import NG_911_DIR
from ilng911.logging import log_context, log

if __name__ == '__main__':
    schemas_dir = os.path.join(NG_911_DIR, 'admin', 'data_structures')
    tables = ['NG911_Tables', 'AgencyInfo', 'CustomFields', 'CustomFields']
    schemaPath = r'L:\Users\caleb.mackey\Documents\GIS_Data\IL_NG911'
    gdbPath = r'L:\Users\caleb.mackey\Documents\GIS_Data\IL_NG911\IL_NG911_Brown_Master_v3.2.5.gdb'

    with log_context() as lc:
        gdb = create_ng911_admin_gdb(gdbPath, schemaPath, 'BROWN')

        # for tab in tables:
        #     json_file = os.path.join(schemas_dir, tab + '.json')
        #     table = os.path.join(gdb, tab)
        #     if tab == 'AgencyInfo':
        #         arcpy.management.Delete(table)

        #     log(f'{json_file}, {os.path.exists(json_file)}')
        #     # log(table)
        #     if os.path.exists(json_file) and not arcpy.Exists(table):
        #         features_from_json(json_file, table)
