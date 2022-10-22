import os
import sys
import arcpy
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.config import load_config
from ilng911.core.address import create_address_point, get_range_and_parity, find_closest_centerlines
from ilng911.schemas import DataSchema, DataType
from ilng911.admin.schemas import add_preconfigured_cad_vendor_fields, features_from_json, create_ng911_admin_gdb, add_preconfigured_cad_vendor_fields
from ilng911.env import NG_911_DIR, get_ng911_db
from ilng911.logging import log_context, log
from ilng911.core.validators import validate_address, run_address_validation
from ilng911.vendors import load_vendor_config

if __name__ == '__main__':
    schemas_dir = os.path.join(NG_911_DIR, 'admin', 'data_structures')
    tables = ['NG911_Tables', 'AgencyInfo', 'CustomFields', 'CustomFields']
    # schemaPath = r'C:\Users\caleb.mackey\Documents\Testing\addressing\data'
    schemaPath = r'C:\Users\caleb.mackey\Documents\GIS_Data\NextGen911_Schemas.sde'
    # gdbPath = os.path.join(schemaPath, 'IL_NG911_Brown_Master_v3.2.5.gdb')
    gdbPath = r'C:\Users\caleb.mackey\Documents\GIS_Data\NextGen911_Test.sde'

    testStr = 'this is a test with house number {Add_Number}, and street name {St_Name}'

    arcpy.env.workspace = schemaPath
    for tab in arcpy.ListTables():
        arcpy.management.Delete(tab)
        print('removed table: ', tab)

    for fc in arcpy.ListFeatureClasses():
        arcpy.management.Delete(fc)
        print('removed fc: ', fc)

    # use config file to create gdb
    # config = load_config()
    # print(json.dumps(config, indent=2))
    # gdbPath = config.ng911GDBPath
    # schemaPath = os.path.dirname(config.ng911GDBSchemasPath)
    # gdb = os.path.join(schemaPath, 'NG911_Schemas.gdb')

    # if arcpy.Exists(gdb) and not gdb.endswith('.sde'):
    #     arcpy.management.Delete(gdb)
    #     print('deleted gdb')

    with log_context() as lc:
        gdb = create_ng911_admin_gdb(gdbPath, schemaPath, 'Brown')
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
        
        # # sample: 142 main
        # pg = arcpy.AsShape({
        #     "x": -90.76689954799997,
        #     "y": 39.98611309700004,
        #     "spatialReference": {
        #     "wkid": 4326,
        #     "latestWkid": 4326
        #     }
        # }, True)

        # # info = get_range_and_parity(pg, feature)
        # # log('range and parity', info)
        
        # null = None
        # kwargs = {
        #     "centerlineOID": 238,
        #     "Effective": null,
        #     "Expire": null,
        #     "AddCode": null,
        #     "AddDataURI": null,
        #     "Nbrhd_Comm": null,
        #     "AddNum_Pre": null,
        #     "Add_Number": 142,
        #     "AddNum_Suf": null,
        #     "ESN": null,
        #     "Building": null,
        #     "Floor": null,
        #     "Unit": null,
        #     "Room": null,
        #     "Seat": null,
        #     "Addtl_Loc": null,
        #     "LandmkName": null,
        #     "Mile_Post": null,
        #     "Place_Type": null,
        #     "Placement": null
        # }

        # ft, schema = create_address_point(pg, **kwargs)
        # # schema = DataSchema(DataType.ADDRESS_POINTS)
        # # ft = schema.create_feature(pg, **kwargs)
        # # schema.calculate_custom_fields(ft)
        # # ft.calculate_custom_field('DemoField', testStr)
        # # print('demo field: ', ft.get('DemoField'))
        # ft.prettyPrint()

        # ft = schema.find_feature_from_oid(3029)
       
        # schema.calculate_vendor_fields(ft)
        # validate_address(ft)

        # run_address_validation()

        # tritech = r'L:\Users\caleb.mackey\Documents\GIS_Data\IL_NG911\Tritech_Test.gdb'
        # tyler = r'L:\Users\caleb.mackey\Documents\GIS_Data\IL_NG911\Tyler_Test.gdb'

        # create testing vendor features
        # for vendor in ['Tyler']:
        #     print('vendor: ', vendor)
        #     config = load_vendor_config(vendor)

        #     # add fields
        #     for schema in config.schemas:
        #         print('checking schema type: ', schema.featureType)
        #         # table = ng911_db.get_table(schema.featureType)
        #         # existing = [f.name for f in arcpy.ListFields(table)]
        #         # for fmap in schema.fieldMap:
        #         #     if fmap.name not in existing:
        #         #         arcpy.AddField_management(table, fmap.name, fmap.type, field_length=fmap.get('length'))

        #         # add pre-configured CAD Vendor Fields
        #         add_preconfigured_cad_vendor_fields(schema.featureType,  vendor)

        # roads = find_closest_centerlines(pg)
        # print(json.dumps(roads, indent=2))
        log('done??')

        
