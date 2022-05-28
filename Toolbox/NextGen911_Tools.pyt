# -*- coding: utf-8 -*-
import os
import sys
import json
import arcpy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.env import ng911_db
from ilng911.geoprocessing import table_to_params, debug_window
from ilng911.schemas import DataType, DataSchema
from ilng911.support.munch import munchify
from ilng911.core.address import STREET_ATTRIBUTES, ADDRESS_ATTRIBUTES, create_address_point, get_range_and_parity
from ilng911.core.fields import FIELDS
from ilng911.logging import log


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
        log(f'path is: "{parameters[0].valueAsText}"')

        with open(r"C:\Users\calebma\Documents\Temp\roadCenterline911.json", 'w') as f:
            json.dump(parameters[1].valueAsText, indent=2)
        return

class CreateRoadCenterline(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Road Centerline"
        self.description = ""
        self.canRunInBackground = False
        self.paramLookup = {}

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = table_to_params(DataSchema(DataType.ROAD_CENTERLINE))
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
        featureSet = arcpy.Parameter(
            name="featureSet",
            displayName="Draw Point",
            direction="Input",
            datatype="GPFeatureRecordSetLayer"
        )
        featureSet.value = r"C:\Users\calebma\Documents\IL_911\IL_NG911_Tools\test_env\test\AddressPoints.lyrx"

        centerlineOID = arcpy.Parameter(
            name="centerlineOID",
            displayName="Centerline OBJECTID",
            direction="Input",
            datatype="GPLong"
        )
        centerline = DataSchema(DataType.ROAD_CENTERLINE)
        with arcpy.da.SearchCursor(centerline.table, ['OID@']) as rows:
            centerlineOID.filter.list = [r[0] for r in rows]

        params = [featureSet, centerlineOID]

        params.extend(table_to_params(DataSchema(DataType.ADDRESS_POINTS), filters=STREET_ATTRIBUTES))
        for p in params[2:]:
            p.enabled = False
        return params
        

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[1].value and parameters[0].altered:
            for p in parameters[2:]:
                p.enabled = True
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        import json
        addNum = [p for p in parameters if p.name ==FIELDS.ADDRESS.NUMBER][0]
        if addNum.value and parameters[1].value and parameters[0].altered and not addNum.hasBeenValidated:
            # debug_window(f'Calling Address Number Validation NOw? {addNum.value}')
            with arcpy.da.SearchCursor(parameters[0].value, ['SHAPE@']) as rows:
                geom = [r[0] for r in rows][0]
                # debug_window(geom.JSON)
            info = get_range_and_parity(geom, parameters[1].value)
            # debug_window(json.dumps(info))
            messages = []
            if addNum.value < info.from_address or addNum.value > info.to_address:
                msg = f'Address Number is not in range {info.to_address} - {info.from_address}'
                # debug_window(msg)
                messages.append(msg)
                
            if info.parity == 'O' and not addNum.value % 2:
                messages.append('Address Number should be Odd')
                # debug_window('Address Number should be Odd')
            elif info.parity == 'E' and addNum.value % 2:
                messages.append('Address Number should be Even')
                # debug_window('Address Number should be Even')
            if messages:
                addNum.setWarningMessage('\n'.join(messages))
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # fs = arcpy.FeatureSet(parameters[0])
        fs = arcpy.FeatureSet()
        fs.load(parameters[0].value)
        attrs = {p.name: p.valueAsText for p in parameters[2:]}
        fsJson = munchify(json.loads(fs.JSON))
        geomJson = fsJson.features[0].get('geometry')
        geomJson["spatialReference"] = {"wkid": 4326 }
        pt = arcpy.AsShape(geomJson, True)
        ft, schema = create_address_point(pt, parameters[1].value, **attrs)
        ft.prettyPrint()
        try: 
            aprx = arcpy.mp.ArcGISProject('current')
            lyr = aprx.activeMap.listLayers(parameters[0].valueAsText)[0]
            if lyr:
                aprx.removeLayer(lyr)
        except:
            pass
        return

if __name__ == '__main__':
    tbx = Toolbox()
    # t = tbx.tools[0]()
    # params = t.getParameterInfo()
    # print(params)
