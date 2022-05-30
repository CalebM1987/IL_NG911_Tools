# -*- coding: utf-8 -*-
import os
import sys
import json
import arcpy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.env import NG_911_DIR, get_ng911_db
from ilng911.admin.schemas import create_ng911_admin_gdb
from ilng911.core.fields import FIELDS
from ilng911.utils.json_helpers import load_json
from ilng911.logging import log


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
        gdb_path = arcpy.Parameter(
            name="gdb_path", 
            displayName="Geodatabase Path",
            datatype="DEWorkspace"
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

        # get list of counties
        agency_file = os.path.join(NG_911_DIR, 'admin', 'data_structures', 'AgencyInfo.json')
        agencyInfo = load_json(agency_file)
        county_field = [f for f in agencyInfo.fields if f.name == 'County'][0]
        county.filter.list = [cv.name for cv in county_field.domain.codedValues]
        

        return [ gdb_path, county, config_file ]

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
        import json
        log(f'path is: "{parameters[0].valueAsText}"')

        with open(r"C:\Users\calebma\Documents\Temp\roadCenterline911.json", 'w') as f:
            json.dump(parameters[1].valueAsText, indent=2)
        return

class CreateNG911SchemaTables(object):
    def __init__(self):
        self.label = "2. Create NG911 Schema Tables"
        self.description = "creates the NG911 Schema Tables database"
        self.canRunInBackground = False
    
    def getParameterInfo(self):
        required_features

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
        import json
        log(f'path is: "{parameters[0].valueAsText}"')

        with open(r"C:\Users\calebma\Documents\Temp\roadCenterline911.json", 'w') as f:
            json.dump(parameters[1].valueAsText, indent=2)
        return

if __name__ == '__main__':
    tbx = Toolbox()
    # t = tbx.tools[0]()
    # params = t.getParameterInfo()
    # print(params)
