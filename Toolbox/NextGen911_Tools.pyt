# -*- coding: utf-8 -*-
import os
import sys
import arcpy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.env import ng911_db
from ilng911.geoprocessing import table_to_params
from ilng911.schemas import DataType


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "NextGen 911 Tools"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [
            CreateRoadCenterline,
            CreateAddressPoint,
            TestTool
        ]

class TestTool(object):
    def __init__(self):
        self.label = "Test Tool"
        self.description = ""
        self.canRunInBackground = False
    
    def getParameterInfo(self):
        path = arcpy.Parameter(
            name="Path", 
            displayName="Path",
            datatype="DEFeatureClass"
        )

        fs = arcpy.Parameter(
            name="Feature_Set",
            displayName="Feature Set",
            datatype='DEFeatureClass',#"GPFeatureRecordSetLayer"
        )
        return [ path, fs ]

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
        arcpy.AddMessage(f'path is: "{parameters[0].valueAsText}"')

        with open(r"C:\Users\calebma\Documents\Temp\roadCenterline911.json", 'w') as f:
            json.dump(parameters[1].valueAsText, indent=2)
        return

class CreateRoadCenterline(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Road Centerline"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = table_to_params(ng911_db.roadCenterlines, ng911_db.load_911_schema(DataType.ROAD_CENTERLINE))
        return params
        

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
        return

class CreateAddressPoint(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Address Point"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = table_to_params(ng911_db.addressPoints, ng911_db.load_911_schema(DataType.ADDRESS_POINTS))
        return params
        

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
        return

if __name__ == '__main__':
    tbx = Toolbox()
    t = tbx.tools[0]()
    params = t.getParameterInfo()
    print(params)
