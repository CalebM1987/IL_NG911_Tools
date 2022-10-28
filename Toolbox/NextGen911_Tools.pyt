# -*- coding: utf-8 -*-
import os
import sys
import json
import arcpy

# debug mode
os.environ['NG911_DEBUG_MODE'] = 'DEBUG'

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.env import get_ng911_db
from ilng911.geoprocessing import get_drawing_featureset, log_params, table_to_params, debug_window
from ilng911.schemas import DataType, DataSchema
from ilng911.support.munch import munchify
from ilng911.core.database import NG911LayerTypes
from ilng911.core.address import STREET_ATTRIBUTES, ADDRESS_ATTRIBUTES, create_address_point, get_range_and_parity, find_closest_centerlines
from ilng911.core.fields import FIELDS, POINT_SIDE_MAPPING
from ilng911.core.validators import run_address_validation
from ilng911.utils.json_helpers import load_json
from ilng911.logging import log, log_context
thisDir = os.path.abspath(os.path.dirname(__file__))
helpersDir = os.path.join(thisDir, 'helpers')

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "NextGen 911 Tools"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [
            Create911Feature,
            CreateRoadCenterline,
            CreateAddressPoint,
            RunAddressValidation
            # TestTool
        ]

class Create911Feature:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create 911 Feature"
        self.description = ""
        self.canRunInBackground = False
        self.category = 'Create Features'
        self.paramLookup = {}

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    
    def getParameterInfo(self):
        featureType = arcpy.Parameter(
            name="featureType",
            displayName="Feature Type",
            direction="Input",
            datatype="GPString"
        )

        # create road feature set
        featureSet = arcpy.Parameter(
            name="featureSet",
            displayName="Draw Point",
            direction="Input",
            datatype="GPFeatureRecordSetLayer",
            enabled=False
        )

        ng911_db = get_ng911_db()
        schemas = ng911_db.get_table()
        with arcpy.da.SearchCursor(schemas, ['FeatureType']) as rows:
            featureType.filter.list = [r[0] for r in rows if r[0] not in ('ADDRESS_POINTS', 'ROAD_CENTERLINE')] + ['Test']
        
        return [ featureType, featureSet ]
        

    def updateParameters(self, parameters):

        if parameters[0].altered:
            featureSet = parameters[1]
            featureSet.enabled = True
            
            featureSet.value = get_drawing_featureset(parameters[0].valueAsText)

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        with log_context(self.__class__.__name__ + '_') as lc:
            log_params(parameters)
            fs = arcpy.FeatureSet()
            fs.load(parameters[0].value)
            log(f'type of param0: {type(parameters[0].value)}')
            attrs = {p.name: p.valueAsText for p in parameters[1:]}
            fsJson = munchify(json.loads(fs.JSON))
            geomJson = fsJson.features[0].get('geometry')
            geomJson["spatialReference"] = {"wkid": 4326 }
            ln = arcpy.AsShape(geomJson, True)
            schema = DataSchema(parameters[0].valueAsText)
            ft = schema.create_feature(ln)
            ft.update(**attrs)
            schema.calculate_custom_fields(ft)
            schema.calculate_vendor_fields(ft)
            schema.commit_features()

class CreateRoadCenterline(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Road Centerline"
        self.description = ""
        self.canRunInBackground = False
        self.category = 'Create Features'
        self.paramLookup = {}

    def getParameterInfo(self):
        """Define parameter definitions"""
        # check for custom populated fields, add to filters
        ng911_db = get_ng911_db()
        custFieldsTab = ng911_db.get_table(ng911_db.schemaTables.CUSTOM_FIELDS)
        overlayFieldsTab = ng911_db.get_table(ng911_db.schemaTables.SPATIAL_JOIN_FIELDS)
        vendorFieldsTab = ng911_db.get_table(ng911_db.schemaTables.CAD_VENDOR_FIELDS)
        where = f"TargetTable = '{ng911_db.types.ROAD_CENTERLINE}'"

        # custom fields
        with arcpy.da.SearchCursor(custFieldsTab, ['TargetTable', 'FieldName'], where_clause=where) as rows:
            custFields = [r[1] for r in rows]

        # overlay attributes
        with arcpy.da.SearchCursor(overlayFieldsTab, ['TargetTable', 'TargetField'], where_clause=where) as rows:
            overlayFields = [r[1] for r in rows]

        # overlay attributes
        where = f"FeatureType = '{ng911_db.types.ROAD_CENTERLINE}'"
        with arcpy.da.SearchCursor(vendorFieldsTab, ['FeatureType', 'FieldName'], where_clause=where) as rows:
            vendorFields = [r[1] for r in rows]

        filters = custFields + overlayFields + vendorFields
        params = table_to_params(DataSchema(DataType.ROAD_CENTERLINE), filters=filters)

        # create road feature set
        featureSet = arcpy.Parameter(
            name="featureSet",
            displayName="Draw Point",
            direction="Input",
            datatype="GPFeatureRecordSetLayer"
        )
        featureSet.value = get_drawing_featureset(ng911_db.types.ROAD_CENTERLINE)

        # centerlineOID = arcpy.Parameter(
        #     name="centerlineOID",
        #     displayName="Road Centerline",
        #     direction="Input",
        #     datatype="GPLong",
        #     enabled=False,
        #     parameterType='Required'
        # )

        params.insert(0, featureSet)
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
        with log_context(self.__class__.__name__ + '_') as lc:
            log_params(parameters)
            fs = arcpy.FeatureSet()
            fs.load(parameters[0].value)
            log(f'type of param0: {type(parameters[0].value)}')
            attrs = {p.name: p.valueAsText for p in parameters[1:]}
            fsJson = munchify(json.loads(fs.JSON))
            geomJson = fsJson.features[0].get('geometry')
            geomJson["spatialReference"] = {"wkid": 4326 }
            ln = arcpy.AsShape(geomJson, True)
            roadSchema = DataSchema(DataType.ROAD_CENTERLINE)
            ft = roadSchema.create_feature(ln)
            ft.update(**attrs)
            roadSchema.calculate_custom_fields(ft)
            roadSchema.calculate_vendor_fields(ft)
            roadSchema.commit_features()
            
            # ft.prettyPrint()
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

class CreateAddressPoint(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Address Point"
        self.description = ""
        self.canRunInBackground = False
        self.category = 'Create Features'

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

        ng911_db = get_ng911_db()
        fs = arcpy.FeatureSet()
        # # get ng911_db helper
        # points = ng911_db.get_911_table(ng911_db.types.ADDRESS_POINTS)
        # desc = arcpy.Describe(points)
        # where = f"{desc.oidFieldName} IS NULL"
        ptJson = load_json(os.path.join(helpersDir, 'DrawingFeatureSet.json'), True)
        # renderer = load_json(os.path.join(helpersDir, 'AddressPointRenderer.json'), True)
        # # fs.load(points, where)#, None, json.dumps(renderer), True) # getting error renderer arguments??
        # # fs = arcpy.FeatureSet(ptJson)#, renderer=renderer)
        fs.load(ptJson)#, None, None, renderer, True)
        # fs = get_drawing_featureset(ng911_db.types.ADDRESS_POINTS)

        featureSet.value = fs

        roadsLyr = arcpy.Parameter(
            name='roadsLyr',
            displayName="Roads Layer",
            direction="Input",
            datatype="GPFeatureLayer",
            parameterType="Required"
        )

        centerlineOID = arcpy.Parameter(
            name="centerlineOID",
            displayName="Road Centerline",
            direction="Input",
            datatype="GPLong",
            enabled=False,
            parameterType='Required'
        )

        # check for custom populated fields, add to filters
        custFieldsTab = ng911_db.get_table(ng911_db.schemaTables.CUSTOM_FIELDS)
        overlayFieldsTab = ng911_db.get_table(ng911_db.schemaTables.SPATIAL_JOIN_FIELDS)
        vendorFieldsTab = ng911_db.get_table(ng911_db.schemaTables.CAD_VENDOR_FIELDS)
        where = f"TargetTable = '{ng911_db.types.ADDRESS_POINTS}'"

        # custom fields
        with arcpy.da.SearchCursor(custFieldsTab, ['TargetTable', 'FieldName'], where_clause=where) as rows:
            custFields = [r[1] for r in rows]

        # overlay attributes
        with arcpy.da.SearchCursor(overlayFieldsTab, ['TargetTable', 'TargetField'], where_clause=where) as rows:
            overlayFields = [r[1] for r in rows]

        # overlay attributes
        where = f"FeatureType = '{ng911_db.types.ADDRESS_POINTS}'"
        with arcpy.da.SearchCursor(vendorFieldsTab, ['FeatureType', 'FieldName'], where_clause=where) as rows:
            vendorFields = [r[1] for r in rows]

        parityFields = [p.get('pt') for p in POINT_SIDE_MAPPING]

        filters = STREET_ATTRIBUTES + custFields + overlayFields + vendorFields + parityFields
        params = [
            featureSet, 
            roadsLyr, 
            centerlineOID
        ]
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
    
        roadsLyr = [p for p in parameters if p.name == 'roadsLyr'][0]
        centerlineOID = [p for p in parameters if p.name == 'centerlineOID'][0]
        # debug_window(f'update params {roadsLyr.altered}, {bool(roadsLyr.value)}', 'udpate params')

        if roadsLyr.value:
       
            roadOID = None
            try:
                # roadsLyr = ng911_db.get_911_layer(ng911_db.types.ROAD_CENTERLINE, check_map=True)
                with arcpy.da.SearchCursor(roadsLyr.value, ['OID@']) as rows:
                    roadOID = [r[0] for r in rows][0]
                    # debug_window(f'oid is? {roadOID}')
                    log(f'fetched road oid from selection: {roadOID}')
            except IndexError:
                # debug_window(f'using hard coded oid: {roadOID}')
                log('could not fetch road oid')
            
            if roadOID:
                centerlineOID.value = roadOID
            else:
                centerlineOID.enabled = True

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        addNum = [p for p in parameters if p.name == FIELDS.ADDRESS.NUMBER][0]
        roadsLyr = [p for p in parameters if p.name == 'roadsLyr'][0]
        centerlineOID = [p for p in parameters if p.name == 'centerlineOID'][0]
        if roadsLyr.value:
            count = int(arcpy.management.GetCount(roadsLyr.value).getOutput(0))
            if count != 1:
                roadsLyr.setWarningMessage(f'please make sure only ONE feature is selected!')

        if addNum.value and centerlineOID.value and parameters[0].altered and not addNum.hasBeenValidated:
            # debug_window(f'Calling Address Number Validation NOw? {addNum.value}')
            with arcpy.da.SearchCursor(parameters[0].value, ['SHAPE@']) as rows:
                geom = [r[0] for r in rows][0]
                # debug_window(geom.JSON)
            info = get_range_and_parity(geom, centerlineOID.value)
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
            log(f'type of param0: {type(parameters[0].value)}')
            attrs = {p.name: p.valueAsText for p in parameters[3:]}
            roadOID = parameters[2].value
            fsJson = munchify(json.loads(fs.JSON))
            geomJson = fsJson.features[0].get('geometry')
            geomJson["spatialReference"] = {"wkid": 4326 }
            pt = arcpy.AsShape(geomJson, True)
            ft, schema = create_address_point(pt, roadOID, **attrs)
            # ft.prettyPrint()
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

class RunAddressValidation(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Run Address Validation"
        self.description = "Will run Address Validation Checks and flag any address with issues"
        self.canRunInBackground = False
        self.category = 'Validation'

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = None
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
        with log_context(self.__class__.__name__ + '_') as lc:
            run_address_validation()
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are outputs are processed and
        added to the display."""
        return

if __name__ == '__main__':
    tbx = Toolbox()
    # t = tbx.tools[0]()
    # params = t.getParameterInfo()
    # print(params)
