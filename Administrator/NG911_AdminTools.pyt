# -*- coding: utf-8 -*-
import os
import sys
import json
import arcpy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.config import load_config
from ilng911.env import NG_911_DIR, get_ng911_db
from ilng911.admin.schemas import create_ng911_admin_gdb
from ilng911.core.fields import FIELDS
from ilng911.utils.json_helpers import load_json
from ilng911.logging import log, log_context
from ilng911.schemas import DATA_TYPES, DATA_TYPES_LOOKUP, DEFAULT_NENA_PREFIXES
from ilng911.env import get_ng911_db

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "NextGen 911 Administrator Tools"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [
            CreateNG911SchemaGeoDatabase,
            CreateNG911SchemaTables,
        ]

class CreateNG911SchemaGeoDatabase(object):
    def __init__(self):
        self.label = "1. Create NG911 Schema Geodatabase"
        self.description = "creates the NG911 Schema geodatabase"
        self.canRunInBackground = False
    
    def getParameterInfo(self):
        ng911_gdb = arcpy.Parameter(
            name="ng911_gdb", 
            displayName="NG911 Geodatabse",
            datatype="DEWorkspace"
        )

        schemas_gdb_path = arcpy.Parameter(
            name='schemas_gdb_path', 
            displayName='Schemas GDB Path',
            datatype='DEWorkspace'
        )

        county = arcpy.Parameter(
            name="county",
            displayName="County",
            datatype='GPString',
        )

        config_file = arcpy.Parameter(
            name="config_file",
            displayName='Config File Name',
        )

        # set defaults and filters
        config_file.value = 'config.json'

        # set workspace filters
        ng911_gdb.filter.list = ['LocalDatabase', 'RemoteDatabase']
        schemas_gdb_path.filter.list = ['FileSystem']

        # get list of counties
        agency_file = os.path.join(NG_911_DIR, 'admin', 'data_structures', 'AgencyInfo.json')
        agencyInfo = load_json(agency_file)
        county_field = [f for f in agencyInfo.fields if f.name == 'County'][0]
        county.filter.list = [cv.name for cv in county_field.domain.codedValues]
        
        # check for existing config
        config = load_config(config_file.value)
        if config:
            ng911_gdb.value = config.get("ng911GDBPath")
            schemas_gdb_path.value = config.get("ng911GDBSchemasPath")
            county.value = config.get('county')

        return [ ng911_gdb, schemas_gdb_path, county, config_file ]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        with log_context(self.__class__.__name__ + '_') as lc:
            create_ng911_admin_gdb(*[p.value for p in parameters])
        return

class CreateNG911SchemaTables(object):
    def __init__(self):
        self.label = "2. Create NG911 Schema Tables"
        self.description = "creates the NG911 Schema Tables database"
        self.canRunInBackground = False
    
    def getParameterInfo(self):
        required_features = arcpy.Parameter(
            name='required_features',
            displayName='Required Features',
            datatype='GPValueTable',
            category='Required Features',
            parameterType='Required'
        )
        
        custom_fields = arcpy.Parameter(
            name='custom_fields',
            displayName='Custom Fields',
            datatype='GPValueTable',
            category='Required Features',
            parameterType='Optional'
        )
        
        cad_vendor_features = arcpy.Parameter(
            name='cad_feature_vendors',
            displayName='CAD Vendor Features',
            datatype='GPValueTable',
            category='CAD Features',
            parameterType='Optional'
        )

        cad_vendor_fields = arcpy.Parameter(
            name='cad_vendor_fields',
            displayName='CAD Vendor Fields',
            datatype='GPValueTable',
            category='CAD Features',
            parameterType='Optional'
        )

        # required fields vt
        required_features.columns = [['GPString', 'Feature Type'], ['GPFeatureLayer', '911 Feature Type'], ['GPString', 'NENA Prefix']]
        # look for existing features
        ng911_db = get_ng911_db()
        ng911_db.setup()
        if ng911_db.setupComplete:
            table = ng911_db.get_table(ng911_db.schemaTables.NG911_TABLES)
            if table:
                with arcpy.da.SearchCursor(table, ['FeatureType', 'Path', 'NENA_Prefix']) as rows:
                    required_features.values = [list(r) for r in rows]
        
        # custom fields
        custom_fields.columns = [['GPString', '911 Feature Type'], ['GPString', 'Field'], ['GPString', 'Expression']]

        # cad vendor features
        cad_vendor_features.columns = [['GPString', 'CAD Vendor'], ['GPFeatureLayer', 'CAD Table']]    

        # cad vendor fields
        cad_vendor_fields.columns = [['GPString', 'CAD Table'], ['GPString', 'Field'], ['GPString', 'Expression']]

        return [ required_features, custom_fields, cad_vendor_features, cad_vendor_fields ]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        with log_context(self.__class__.__name__ + '_') as lc:
            pass
        return

if __name__ == '__main__':
    tbx = Toolbox()
    # t = tbx.tools[0]()
    # params = t.getParameterInfo()
    # print(params)
