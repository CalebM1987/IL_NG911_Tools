import os
import sys
import arcpy
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.core.address import create_address_point, get_range_and_parity, find_closest_centerlines
from ilng911.schemas import DataSchema, DataType
from ilng911.admin.schemas import features_from_json, create_ng911_admin_gdb
from ilng911.env import NG_911_DIR, get_ng911_db
from ilng911.logging import log_context, log

if __name__ == '__main__':
    schemas_dir = os.path.join(NG_911_DIR, 'admin', 'data_structures')
    tables = ['NG911_Tables', 'AgencyInfo', 'CustomFields', 'CustomFields']
    schemaPath = r'L:\Users\caleb.mackey\Documents\GIS_Data\IL_NG911'
    gdbPath = r'L:\Users\caleb.mackey\Documents\GIS_Data\IL_NG911\IL_NG911_Brown_Master_v3.2.5.gdb'

    testStr = 'this is a test with house number {Add_Number}, and street name {St_Name}'

    with log_context() as lc:
        # gdb = create_ng911_admin_gdb(gdbPath, schemaPath, 'BROWN')
        # ng911_db = get_ng911_db()
        # log(f'setup is complete? {ng911_db.setupComplete}')
        # if not ng911_db.setupComplete:
        #     gdb = create_ng911_admin_gdb(gdbPath, schemaPath, 'BROWN')
        #     ng911_db.setup()
        #     log(f'created admin gdb, is setup complete? {ng911_db.setupComplete}')

        # points = ng911_db.get_911_table(ng911_db.types.ADDRESS_POINTS)
        # print('points is: ', points)
        # print(arcpy.Describe(points).oidFieldName)
        # for tab in tables:
        #     json_file = os.path.join(schemas_dir, tab + '.json')
        #     table = os.path.join(gdb, tab)
        #     if tab == 'AgencyInfo':
        #         arcpy.management.Delete(table)

        #     log(f'{json_file}, {os.path.exists(json_file)}')
        #     # log(table)
        #     if os.path.exists(json_file) and not arcpy.Exists(table):
        #         features_from_json(json_file, table)

        # centerlineSchema = DataSchema(DataType.ROAD_CENTERLINE)

        # feature = centerlineSchema.find_feature_from_oid(238)
        # feature.prettyPrint()
        
        # sample: 142 main
        pg = arcpy.AsShape({
            "x": -90.76689954799997,
            "y": 39.98611309700004,
            "spatialReference": {
            "wkid": 4326,
            "latestWkid": 4326
            }
        }, True)

        # info = get_range_and_parity(pg, feature)
        # log('range and parity', info)
        
        null = None
        kwargs = {
            "centerlineOID": 238,
            "Effective": null,
            "Expire": null,
            "AddCode": null,
            "AddDataURI": null,
            "Nbrhd_Comm": null,
            "AddNum_Pre": null,
            "Add_Number": 142,
            "AddNum_Suf": null,
            "ESN": null,
            "Building": null,
            "Floor": null,
            "Unit": null,
            "Room": null,
            "Seat": null,
            "Addtl_Loc": null,
            "LandmkName": null,
            "Mile_Post": null,
            "Place_Type": null,
            "Placement": null
        }

        ft, schema = create_address_point(pg, **kwargs)
        # schema = DataSchema(DataType.ADDRESS_POINTS)
        # ft = schema.create_feature(pg, **kwargs)
        # schema.calculate_custom_fields(ft)
        # ft.calculate_custom_field('DemoField', testStr)
        # print('demo field: ', ft.get('DemoField'))
        ft.prettyPrint()

        # roads = find_closest_centerlines(pg)
        # print(json.dumps(roads, indent=2))
        log('done??')

        
