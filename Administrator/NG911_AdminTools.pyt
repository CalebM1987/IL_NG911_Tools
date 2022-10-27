# -*- coding: utf-8 -*-
import os
import sys
import json
import arcpy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.config import load_config
from ilng911.env import NG_911_DIR, get_ng911_db
from ilng911.admin.schemas import create_ng911_admin_gdb, register_spatial_join_fields, add_cad_vendor_fields, add_preconfigured_cad_vendor_fields
from ilng911.core.fields import FIELDS
from ilng911.utils.json_helpers import load_json
from ilng911.utils.helpers import parameter_from_json, params_to_kwargs, parse_value_table, find_nena_guid_field
from ilng911.logging import log, log_context
from ilng911.utils.cursors import UpdateCursor, InsertCursor
from ilng911.schemas import DATA_TYPES, DATA_TYPES_LOOKUP, DEFAULT_NENA_PREFIXES
from ilng911.env import get_ng911_db

helpers_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'helper')
helpers_json = load_json(os.path.join(helpers_dir, 'tools.json'))

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
            # AddOverlayAttributes,
            AddCustomFields,
            AddCADVendorFields,
            AddPreConfiguredCADVendorFields
        ]

class CreateNG911SchemaGeoDatabase(object):
    def __init__(self):
        self.label = "1. Create NG911 Schema Geodatabase"
        self.description = "creates the NG911 Schema geodatabase"
        self.canRunInBackground = False
        self.category = 'Setup'
    
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

        agency = arcpy.Parameter(
            name="agency",
            displayName="Agency",
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
        schemas_gdb_path.filter.list = ['FileSystem', 'RemoteDatabase']

        # get list of counties
        agency_file = os.path.join(NG_911_DIR, 'admin', 'agencyInfos')
        agencyInfos = load_json(agency_file)
        agency.filter.list = [r.get('AgencyName') for r in agencyInfos]
        # agency_field = [f for f in agencyInfo.fields if f.name == 'AgencyName'][0]
        # agency.filter.list = [cv.name for cv in agency_field.domain.codedValues]
        
        # check for existing config
        config = load_config(config_file.value)
        if config:
            ng911_gdb.value = config.get("ng911GDBPath")
            schemasPathConf = config.get("ng911GDBSchemasPath")
            schemas_gdb_path.value = os.path.dirname(schemasPathConf) if schemasPathConf else None
            agency.value = config.get('agencyName')

        return [ ng911_gdb, schemas_gdb_path, agency, config_file ]

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
            create_ng911_admin_gdb(*[p.valueAsText for p in parameters])
        return

class CreateNG911SchemaTables(object):
    def __init__(self):
        self.label = "2. Create NG911 Schema Tables (Optional)"
        self.description = "creates the NG911 Schema Tables database"
        self.canRunInBackground = False
        self.category = 'Setup'
    
    def getParameterInfo(self):
        required_features = arcpy.Parameter(
            name='required_features',
            displayName='Required Features',
            datatype='GPValueTable',
            # category='Required Features',
            parameterType='Required'
        )
        
        # custom_fields = arcpy.Parameter(
        #     name='custom_fields',
        #     displayName='Custom Fields',
        #     datatype='GPValueTable',
        #     category='Required Features',
        #     parameterType='Optional'
        # )
        
        # cad_vendor_features = arcpy.Parameter(
        #     name='cad_feature_vendors',
        #     displayName='CAD Vendor Features',
        #     datatype='GPValueTable',
        #     category='CAD Features',
        #     parameterType='Optional'
        # )

        # cad_vendor_fields = arcpy.Parameter(
        #     name='cad_vendor_fields',
        #     displayName='CAD Vendor Fields',
        #     datatype='GPValueTable',
        #     category='CAD Features',
        #     parameterType='Optional'
        # )

        # required fields vt
        required_features.columns = [['GPString', '911 Feature Type'], ['GPFeatureLayer', '911 Layer'], ['GPString', 'NENA Prefix']]
        # look for existing features
        ng911_db = get_ng911_db()
        ng911_db.setup()
        if ng911_db.setupComplete:
            table = ng911_db.get_table(ng911_db.schemaTables.NG911_TABLES)
            if table:
                with arcpy.da.SearchCursor(table, ['FeatureType', 'Path', 'NENA_Prefix']) as rows:
                    required_features.values = [list(r) for r in rows]

        # # set dropdowns for feature type
        # featureTypes = list(iter(DATA_TYPES))
        # required_features.filters[0].type = 'ValueList'
        # required_features.filters[0].list = featureTypes
        
        # # custom fields
        # custom_fields.columns = [['GPString', '911 Feature Type'], ['GPString', 'Field'], ['GPString', 'Expression']]
        # custom_fields.filters[0].type = 'ValueList'
        # custom_fields.filters[0].list = featureTypes

        # # create dropdowns from address + centerline fields
        # if ng911_db.addressPoints and arcpy.Exists(ng911_db.addressPoints):
        #     flds = [f.name for f in arcpy.ListFields(ng911_db.addressPoints) if f.type == 'String']
        #     custom_fields.filters[1].type = 'ValueList'
        #     custom_fields.filters[1].list = flds

        # # cad vendor features
        # cad_vendor_features.columns = [['GPString', 'CAD Vendor'], ['GPFeatureLayer', 'CAD Table']]    

        # # cad vendor fields
        # cad_vendor_fields.columns = [['GPString', 'CAD Table'], ['GPString', 'Field'], ['GPString', 'Expression']]

        return [ required_features] #, custom_fields, cad_vendor_features, cad_vendor_fields ]

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
            ng911_db = get_ng911_db()
            if ng911_db.setupComplete:
                # check for core feature classes
                param_lookup = {p.name: p for p in parameters}
                required_features = param_lookup.get('required_features')
                schemaTable = ng911_db.get_table(ng911_db.schemaTables.NG911_TABLES)
                with arcpy.da.SearchCursor(schemaTable, ['FeatureType', 'Path']) as rows:
                    existing = {r[0]: r for r in rows if r[1] and arcpy.Exists(r[1])}

                # try to find required feature classes
                toAdd = {p[0]: p for p in required_features.values if p[0] in existing and existing.get(p[0])[1] != p[1] }

                # add missing features
                if toAdd:
                    with arcpy.da.InsertCursor(schemaTable, ['Basename', 'Path', 'FeatureType', 'NENA_Prefix', 'GUID_Field']) as rows:
                        for target, row in toAdd.items():
                            log(f'checking for required type: "{target}": {row[1:]}')
                            full_path = row[1]
                            basename = os.path.basename(full_path)
                            guid_field = find_nena_guid_field(full_path)
                            rows.insertRow((basename, full_path, target, row[2] or DEFAULT_NENA_PREFIXES.get(target), guid_field))
                            log(f'Found Schema for "{target}" -> "{basename}"')

            # register nena identifiers
            try:
                ng911_db.register_nena_ids()
            except Exception as e:
                log(f'failed to register NENA identifiers')
            
        return

class AddOverlayAttributes(object):
    def __init__(self):
        self.label = "Add Overlay Attributes"
        self.description = "add attributes that will be populated based on a spatial relationship"
        self.canRunInBackground = False
        self.category = 'Custom Fields'
    
    def getParameterInfo(self):
        try:
            tool = [t for t in helpers_json.tools if t.name == self.__class__.__name__][0]
            return [parameter_from_json(p) for p in tool.params]
        except IndexError:
            return []

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
            target = parameters[0].valueAsText
            target_field = parameters[1].valueAsText
            source = arcpy.Describe(parameters[2].value).catalogPath
            fields = [f.name for f in parameters[3].value]
            register_spatial_join_fields(target, target_field, source, fields)
        return

class AddCustomFields(object):
    def __init__(self):
        self.label = "Add Custom Fields"
        self.description = "add attributes that will be populated based on an expression"
        self.canRunInBackground = False
        self.category = 'Custom Fields'
    
    def getParameterInfo(self):
        
        try:
            log('Attempting to get parameters from json')
            tool = [t for t in helpers_json.tools if t.name == self.__class__.__name__][0]
            return [parameter_from_json(p) for p in tool.params]
        except IndexError:
            return []

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
            target = arcpy.Describe(parameters[0].value).catalogPath
            log(f'vt as text: {parameters[1].valueAsText}')
            vt = parse_value_table(parameters[1].valueAsText)
            log(f'Custom Fields ValueTable:\n{vt}')
            il911_db = get_ng911_db()
            tableType = il911_db.get_table_type(target)
            if not tableType:
                log('Unsupported Table Path provided', 'error')
                arcpy.AddError('Unsupported Table Path provided')
                return

            log(f'Preparing to add Custom Fields for "{tableType}"')

            # get custom fields table
            fieldsTable = il911_db.get_table(il911_db.schemaTables.CUSTOM_FIELDS)
            
            # check for updates first
            skipIndices = []
            with UpdateCursor(fieldsTable, ['TargetTable', 'FieldName', 'Expression']) as rows:
                for r in rows:
                    for i, (field, exp) in enumerate(vt):
                        if tableType == r[0] and field == r[1]:
                            rows.updateRow([r[0], r[1], exp])
                            skipIndices.append(i)
                            log(f'updated existing expression for field "{field}" with expression "{exp}"')

            # now insert any new table/field combos
            with InsertCursor(fieldsTable, ['TargetTable', 'FieldName', 'Expression']) as irows:
                for i, (field, exp) in enumerate(vt):
                    if i not in skipIndices:
                        irows.insertRow([tableType, field, exp])
                        log(f'added new expression for field "{field}": "{exp}"')

class AddPreConfiguredCADVendorFields(object):
    def __init__(self):
        self.label = "Add Pre-Configured CAD Vendors"
        self.description = "add pre-configured CAD Vendors"
        self.canRunInBackground = False
        self.category = 'CAD Vendors'
    
    def getParameterInfo(self):
        
        try:
            log('Attempting to get parameters from json')
            tool = [t for t in helpers_json.tools if t.name == self.__class__.__name__][0]
            return [parameter_from_json(p) for p in tool.params]
        except IndexError:
            return []

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
            params = params_to_kwargs(parameters)
            add_preconfigured_cad_vendor_fields(**params)

class AddCADVendorFields(object):
    def __init__(self):
        self.label = "Add CAD Vendor Fields"
        self.description = "add CAD Vendor Fields"
        self.canRunInBackground = False
        self.category = 'CAD Vendors'
    
    def getParameterInfo(self):
        
        try:
            log('Attempting to get parameters from json')
            tool = [t for t in helpers_json.tools if t.name == self.__class__.__name__][0]
            return [parameter_from_json(p) for p in tool.params]
        except IndexError:
            return []

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
            cad_path = parameters[0].value
            featureType = parameters[1].valueAsText
            vendor = parameters[1].valueAsText
            vt = parse_value_table(parameters[3].valueAsText)
            add_cad_vendor_fields(cad_path, featureType, vendor, vt)

if __name__ == '__main__':
    tbx = Toolbox()
    # t = tbx.tools[0]()
    # params = t.getParameterInfo()
    # print(params)
