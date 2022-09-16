# -*- coding: utf-8 -*-
import os
import sys
import json
import arcpy

# debug mode
os.environ['NG911_DEBUG_MODE'] = 'DEBUG'

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.env import get_ng911_db
from ilng911.geoprocessing import log_params, table_to_params, debug_window
from ilng911.schemas import DataType, DataSchema
from ilng911.support.munch import munchify
from ilng911.core.address import STREET_ATTRIBUTES, ADDRESS_ATTRIBUTES, create_address_point, get_range_and_parity, find_closest_centerlines
from ilng911.core.fields import FIELDS
from ilng911.utils.json_helpers import load_json
from ilng911.logging import log, log_context
thisDir = os.path.abspath(os.path.dirname(__file__))
helpersDir = os.path.join(thisDir, 'helpers')

ng911_db = get_ng911_db()

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
            # TestTool
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
        # featureSet.value = r'L:\Users\caleb.mackey\Documents\gitProjects\IL_NG911_Tools\Toolbox\helpers\AddressPoints.lyrx'
        # featureSet.schema.featureType
        # featureSet.schema.geometryType = 'Point'

        fs = arcpy.FeatureSet()
        points = ng911_db.get_911_table(ng911_db.types.ADDRESS_POINTS)
        desc = arcpy.Describe(points)
        where = f"{desc.oidFieldName} IS NULL"
        renderer = load_json(os.path.join(helpersDir, 'AddressPointRenderer.json'))
        fs.load(points, where)#, None, json.dumps(renderer), True) # getting error renderer arguments??

        featureSet.value = fs

        centerlineOID = arcpy.Parameter(
            name="centerlineOID",
            displayName="Road Centerline",
            direction="Input",
            datatype="GPLong",
            enabled=False
        )
        try:
            with arcpy.da.SearchCursor("RoadCenterline", ['OID@']) as rows:
                roadOID = [r[0] for r in rows][0]
                debug_window(f'oid is? {roadOID}')
                log(f'fetched road oid from selection: {roadOID}')
        except IndexError:
            roadOID = 208
            debug_window(f'using hard coded oid: {roadOID}')
            log('could not fetch road oid, defaulting to 208')
        centerlineOID.value = roadOID
        
        # centerlineOID.enabled = False
        # centerline = DataSchema(DataType.ROAD_CENTERLINE)
        # with arcpy.da.SearchCursor(centerline.table, ['OID@']) as rows:
        #     centerlineOID.filter.list = [r[0] for r in rows]

        params = [featureSet, centerlineOID]

        # check for custom populated fields, add to filters
        custFieldsTab = ng911_db.get_table(ng911_db.schemaTables.CUSTOM_FIELDS)
        overlayFieldsTab = ng911_db.get_table(ng911_db.schemaTables.SPATIAL_JOIN_FIELDS)
        where = f"TargetTable = '{ng911_db.types.ADDRESS_POINTS}'"

        # custom fields
        with arcpy.da.SearchCursor(custFieldsTab, ['TargetTable', 'FieldName'], where_clause=where) as rows:
            custFields = [r[1] for r in rows]

        # overlay attributes
        with arcpy.da.SearchCursor(overlayFieldsTab, ['TargetTable', 'TargetField'], where_clause=where) as rows:
            overlayFields = [r[1] for r in rows]

        filters = STREET_ATTRIBUTES + custFields + overlayFields
        params.extend(table_to_params(DataSchema(DataType.ADDRESS_POINTS), filters=filters))
        # for p in params[2:]:
        #     p.enabled = False
        return params
        

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        # if parameters[0].altered and parameters[0].value and not parameters[1].value: #not parameters[1].altered:# and int(arcpy.GetCount_management(parameters[0].value).getOutput(0)):
            
        #     debug_window(parameters[0].valueAsText)
        #     debug_window(f'count: {int(arcpy.GetCount_management(parameters[0].value).getOutput(0))}')
        #     with arcpy.da.SearchCursor(parameters[0].value, ['SHAPE@', 'OID@']) as rows:
        #         try:
        #             geom = [r[0] for r in rows][0]
        #         except IndexError:
        #             geom = None
        #     if geom:
        #         debug_window('we have geometry')
        #         # get list of closest roads
        #         roads = find_closest_centerlines(geom)
        #         debug_window(json.dumps(roads))
        #         if len(roads) == 1:
        #             rd = roads[0]
        #             parameters[1].value = f'{rd["OID@"]}: {rd.St_Name} {rd.St_PosTyp}'
        #         else:
        #             parameters[1].filter.list = [f'{rd["OID@"]}: {rd.St_Name} {rd.St_PosTyp}' for rd in roads]
        #         parameters[1].enabled = True

        # if parameters[1].value and parameters[0].altered:
        #     for p in parameters[2:]:
        #         p.enabled = True
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        addNum = [p for p in parameters if p.name == FIELDS.ADDRESS.NUMBER][0]
        if addNum.value and parameters[1].value and parameters[0].altered and not addNum.hasBeenValidated:
            # debug_window(f'Calling Address Number Validation NOw? {addNum.value}')
            with arcpy.da.SearchCursor(parameters[0].value, ['SHAPE@']) as rows:
                geom = [r[0] for r in rows][0]
                # debug_window(geom.JSON)
            info = get_range_and_parity(geom, parameters[1].value)
            # debug_window(json.dumps(info))
            messages = []
            if addNum.value < info.from_address or addNum.value > info.to_address:
                msg = f'Address Number is not in range {info.from_address} - {info.to_address}'
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
        with log_context(self.__class__.__name__ + '_') as lc:
            log_params(parameters)
            fs = arcpy.FeatureSet()
            fs.load(parameters[0].value)
            attrs = {p.name: p.valueAsText for p in parameters[2:]}
            roadOID = parameters[1].value
            # roadOID = int(parameters[1].valueAsText.split(':')[0])
            # try:
            #     with arcpy.da.SearchCursor("RoadCenterline", ['OID@']) as rows:
            #         roadOID = [r[0] for r in rows][0]
            #         log(f'fetched road oid from selection: {roadOID}')
            # except IndexError:
            #     roadOID = 208
            #     log('could not fetch road oid, defaulting to 208')
            fsJson = munchify(json.loads(fs.JSON))
            geomJson = fsJson.features[0].get('geometry')
            geomJson["spatialReference"] = {"wkid": 4326 }
            pt = arcpy.AsShape(geomJson, True)
            ft, schema = create_address_point(pt, roadOID or 208, **attrs)
            ft.prettyPrint()
            try: 
                # try to remove feature set layer
                aprx = arcpy.mp.ArcGISProject('current')
                log(f'attempting to remove temporary drawing layer: "{parameters[0].valueAsText}"')
                lyr = aprx.activeMap.listLayers(parameters[0].valueAsText)[0]
                log(f'found temporary drawing layer: {lyr}')
                if lyr:
                    aprx.activeMap.removeLayer(lyr)
                    log(f'removed temporary drawing layer: "{parameters[0].valueAsText}"')
            except Exception as e:
                log(f'failed to remove temporary draw layer: {e}', 'warn')
                pass
            return

if __name__ == '__main__':
    tbx = Toolbox()
    # t = tbx.tools[0]()
    # params = t.getParameterInfo()
    # print(params)
