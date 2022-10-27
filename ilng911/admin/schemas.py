import enum
import json
from operator import ge
import os
import re
import time
import arcpy
import glob
import datetime
from typing import List

from attr import field

esb_pattern = re.compile('(esb?_*)')

from ilng911.vendors import load_vendor_config
from ..env import NG_911_DIR, get_ng911_db
from ..logging import log, timeit
from ..utils.cursors import find_ws, UpdateCursor, InsertCursor
from ..utils.json_helpers import load_json
from ..utils.helpers import field_types, find_nena_guid_field
from ..support.munch import munchify
from ..config import write_config
from ..core.database import NG911LayerTypes, NG911SchemaTables
from ..schemas import DATA_TYPES, DATA_TYPES_LOOKUP, DEFAULT_NENA_PREFIXES

def features_from_json(json_file: str, out_path: str, registerAsVersioned: bool=False):
    """create features from a json file, will also add
    necessary domains.

    Args:
        json_file (str): the input json file
        out_path (str): the output feature class
        registerAsVersioend (bool): option to register data as versioned, only applicable for SDE data
    """
    # first check for domains in fields
    fs = load_json(json_file)
    domains = munchify([dict(field=f, **f.domain) for f in fs.fields if f.get('domain')])
    addedDomains = []
    ws, ws_type = find_ws(out_path, return_type=True)
    if domains and ws_type in ('LocalDatabase', 'RemoteDatabase'):
        doms = {d.name: d for d in arcpy.da.ListDomains(ws)}
        for dom in domains:
            if dom.name not in doms and dom.name not in addedDomains:
                # new domain detected, try adding it
                dom_type = 'CODED' if dom.type == 'codedValue' else 'RANGE'
                try:
                    arcpy.management.CreateDomain(
                        ws, 
                        dom.name, 
                        dom.name, 
                        field_type=field_types.get(dom.field.type, 'TEXT'), 
                        domain_type=dom_type
                    )
                    addedDomains.append(dom.name)

                    log(f'created domain "{dom.name}" in workspace: "{ws}"')

                    # add coded values
                    if dom_type == 'CODED':
                        for cv in dom.codedValues:
                            arcpy.management.AddCodedValueToDomain(ws, dom.name, cv.code, cv.name)
                        log(f'added {len(dom.codedValues)} coded values to domain: "{dom.name}"')
                    else:
                        # set range values
                        arcpy.management.SetValueForRangeDomain(ws, dom.name, *dom.get('range', []))
                        log(f'set range {len(dom.codedValues)} coded values for domain: "{dom.name}"')

                except Exception as e:
                    log(f'Failed to create domain: "{dom.name}": {e}', 'warn')

    # convert from json
    if ws_type == 'RemoteDatabase':
        log('detected SDE database, will convert features to in_memory fc first and then append')
        # temp = os.path.join(arcpy.env.scratchGDB, os.path.basename(json_file).replace('.json', ''))
        base = os.path.basename(json_file).replace('.json', '')
        temp = os.path.join('in_memory', base)
        temp = arcpy.conversion.JSONToFeatures(json_file, temp).getOutput(0)
        log(f'created temporary features: "{temp}"')
        if base in ['AddressFlags', 'ValidatedAddresses']:
            arcpy.conversion.FeatureClassToFeatureClass(temp, *os.path.split(out_path))
        else:
            arcpy.conversion.TableToTable(temp, *os.path.split(out_path))
        arcpy.management.Delete(temp)
    else:
        arcpy.conversion.JSONToFeatures(json_file, out_path)
    log(f'Converted json file to features: "{out_path}"')

    # now assign domains
    for dom in domains:
        try:
            arcpy.management.AssignDomainToField(out_path, dom.field.name, dom.name)
            log(f'Assigned "{dom.name}" domain to "{dom.field.name}" field.')
        except Exception as e:
            log(f'Failed to assign "{dom.name}" domain to "{dom.field.name}" field: {e}', level='warn')

    # attempt to register as versioned if sde
    if registerAsVersioned and ws_type == 'RemoteDatabase':
        try:
            arcpy.management.RegisterAsVersioned(out_path)
            log(f'registered data as versioned')
        except Exception as e:
            log(f'failed to register data as versioned')
    return out_path
    

@timeit
def create_ng911_admin_gdb(ng911_gdb: str, schemas_gdb_path: str, agency: str, config_file='config.json', registerAsVersioned: bool=False) -> str:
    """creates the NG911_SchemaTables.gdb

    Args:
        ng911_gdb (str): the ng911 geodatabase path
        schemas_gdb_path (str): the geodatabase folder path
        agency (str): the agency name
        config_file (str, optional): _description_. Defaults to 'config.json'.
        registerAsVersioend (bool): option to register data as versioned, only applicable for SDE data

    Returns:
        str: _description_
    """
    ws = arcpy.Describe(schemas_gdb_path)
    if ws.workspaceType == 'FileSystem':
        out_gdb = os.path.join(schemas_gdb_path, 'NG911_Schemas.gdb')

        if not arcpy.Exists(out_gdb):
            arcpy.management.CreateFileGDB(*os.path.split(out_gdb))
            log(f'Created NG911 Schema Geodatabase: "{out_gdb}"')
    
    elif ws.workspaceType in ['LocalDatabase', 'RemoteDatabase']:
        log(f'using existing geodatabse for schema tables: "{schemas_gdb_path}" ({ws.workspaceType})')
        out_gdb = schemas_gdb_path

    # create all tables
    schemas_dir = os.path.join(NG_911_DIR, 'admin', 'data_structures')
    for fl in glob.glob(os.path.join(schemas_dir, '*.json')):
        basename = os.path.basename(fl)
        table = os.path.join(out_gdb, basename.split('.')[0])

        # create if missing
        if not arcpy.Exists(table):
            log(f'creating table form JSON definition: "{basename}"')
            features_from_json(fl, table, registerAsVersioned)

    # load agency infos
    agency_file = os.path.join(NG_911_DIR, 'admin', 'agencyInfos')
    agencyInfos = load_json(agency_file)
    agencyInfo = [a for a in agencyInfos if agency == a.AgencyName][0]
    agencyId = agencyInfo.AgencyID

    # write config file
    # agencyId = f'{county.lower()}coil.org'
    conf = {
        'ng911GDBPath': ng911_gdb,
        'ng911GDBSchemasPath': out_gdb,
        'createdBy': os.getenv('username'),
        'created': datetime.datetime.utcnow().isoformat(),
        'agencyName': agency,
        'agencyId': agencyId
    }

    if not config_file.endswith('.json'):
        config_file += '.json'

    write_config(conf, config_file)

    # check for relationship class for vendors to fields
    hasSpatialRel = False
    spatialRel = 'SpatailJoinFeaturesRel'
    for dirpath, dirnames, rels in arcpy.da.Walk(out_gdb, datatype='RelationshipClass'):
        for rel in rels:
            log(f'relationship class: "{rel}"')
                
            if rel == spatialRel:
                hasSpatialRel = True
                log('found existing spatial join features relationship')

    if not hasSpatialRel:
        # create relationship class
        spatialFeatures = os.path.join(out_gdb, NG911SchemaTables.SPATIAL_JOIN_FEATURES)
        spatialFields = os.path.join(out_gdb, NG911SchemaTables.SPATIAL_JOIN_FIELDS)
        arcpy.management.CreateRelationshipClass(
            spatialFeatures, 
            spatialFields, 
            os.path.join(out_gdb, spatialRel), 
            'COMPOSITE', 
            NG911SchemaTables.SPATIAL_JOIN_FIELDS, 
            NG911SchemaTables.SPATIAL_JOIN_FEATURES, 
            'BOTH', 
            'ONE_TO_MANY', 
            'ATTRIBUTED', 
            'TableName',
            'TableName',
        )
        log(f'created "{spatialRel}" relationship')

    # set agency info
    table = os.path.join(out_gdb, NG911SchemaTables.AGENCY_INFO)

    agencyFields = ['AgencyName', 'AgencyID', 'County', 'County2', 'County3', 'Region']
    with UpdateCursor(table, agencyFields) as rows:
        for r in rows:
            if r[1] != agencyInfo.get('AgencyID'):
                rows.updateRow([agencyInfo.get(f) for f in agencyFields])

    log(f'set agency ID: "{agencyId}"')

    # check for core feature classes
    schemaTable = os.path.join(out_gdb, NG911SchemaTables.NG911_TABLES)
    with arcpy.da.SearchCursor(schemaTable, ['FeatureType', 'Path']) as rows:
        existing = [r[0] for r in rows if r[1] and arcpy.Exists(r[1])]

    # try to find required feature classes
    toAdd = [p for p in DATA_TYPES if p not in existing]

    # create nena identifiers table
    nenaTab = os.path.join(out_gdb, 'NENA_IDs')
    if not arcpy.Exists(nenaTab):
        nenaTab = arcpy.management.CreateTable(*os.path.split(nenaTab)).getOutput(0)
        log(f'Created "NENA_Identifiers" table"')

    nena_id_fields = [f.name for f in arcpy.ListFields(nenaTab)]
    nena_ids = {}

    # walk through gdb
    with InsertCursor(schemaTable, ['Basename', 'Path', 'FeatureType', 'NENA_Prefix', 'GUID_Field']) as rows:
        for root, fds, tables in arcpy.da.Walk(ng911_gdb, datatype=['FeatureDataset', 'FeatureClass']):
            for tab in tables:
                tab_base = tab.split('.')[-1]
                if esb_pattern.match(tab_base):
                    tab_base = tab_base.upper()
                
                target = DATA_TYPES_LOOKUP.get(tab_base)

                full_path = os.path.join(root, tab)
                guid_field = find_nena_guid_field(full_path)
                if target and target in toAdd:
                    rows.insertRow((tab, full_path, target, DEFAULT_NENA_PREFIXES.get(target), guid_field))
                    log(f'Found Schema for "{target}" -> "{tab}"')

                    if target not in nena_id_fields:
                        nena_ids[target] = {'guid_field': guid_field, 'path': full_path, 'uid': 1 }

    # populate nena identifiers table
    for target, ni in nena_ids.items():
        guid_field = ni.get('guid_field')
        path = ni.get('path')
        uid = ni.get('uid')
        # add field
        arcpy.management.AddField(nenaTab, target, 'LONG')
        log(f'added NENA Identifier field "{target}')
       
        # find max id
        # where = f'{guid_field} is not null'
        desc = arcpy.Describe(path)
        oidField = desc.oidFieldName
        if guid_field:
            sql_clause = (None, f'ORDER BY {oidField} DESC')
<<<<<<< HEAD
            with arcpy.da.SearchCursor(path, [guid_field], sql_clause=sql_clause) as rows:
=======
            with arcpy.da.SearchCursor(path, [guid_field, 'OID@'], sql_clause=sql_clause) as rows:
>>>>>>> dev-tb
                for r in rows:
                    try:
                        guid = int(''.join([t for t in r[0].split('@')[0] if t.isdigit()]))
                    except:
                        guid = None
                        log(f'failed to parse nena identifier: "{r[0]}"')

                    if guid and guid > uid:
                        uid = guid
                        nena_ids[target]['uid'] = guid
                        log(f'found MAX NENA Identifier for "{target}": {uid}')
                        break

    # populate guids
    fields = list(nena_ids.keys())
    if fields:
        count = int(arcpy.management.GetCount(nenaTab).getOutput(0))
        row = [nena_ids.get(f, {}).get('uid') for f in fields]
        if not count:
            with InsertCursor(nenaTab, fields) as irows:
                irows.insertRow(row)
                log(f'added MAX NENA Identifier row')
        else:
            # record already exists, just update it
            with UpdateCursor(nenaTab, fields) as rows:
                for i, r in enumerate(rows):
                    if i == 0:
                        rows.updateRow(row)
                        log('updated NENA IDs table')
                    else:
                        rows.deleteRow()
                        log(f'removed NENA IDs row at index: {i}')

        
    log('completed NextGen911 Admin database setup')

def register_spatial_join_fields(target_table: str, target_field: str, join_table: str, fields: List[str]):
    """registers spatial join fields

    Args:
        target_table (str): _description_
        target_field (str): _description_
        join_table (str): _description_
        fields (List[str]): _description_
    """
    ng_911_db = get_ng911_db()

    spatialFeatures = ng_911_db.get_table(NG911SchemaTables.SPATIAL_JOIN_FEATURES)
    spatialFields = ng_911_db.get_table(NG911SchemaTables.SPATIAL_JOIN_FIELDS)
    features_name = os.path.basename(spatialFeatures)
    existing_where = f"Path = '{target_table}' AND TableName = '{features_name}'"

    tab = arcpy.management.MakeTableView(spatialFeatures, 'spatial_features', existing_where)

    if not int(arcpy.management.GetCount(tab).getOutput(0)):
        # does not exist, insert row
        with InsertCursor(spatialFeatures, ['Path', 'TableName']) as rows:
            rows.insertRow([spatialFeatures, features_name])
            log(f'Registered new Spatial Join Feature: "{spatialFeatures}"')

    spa_fields = ['TargetTable', 'TargetField', 'TableName', 'JoinField']
    with arcpy.da.SearchCursor(spatialFields, spa_fields) as rows:
        existing = [list(r) for r in rows]

    with InsertCursor(spatialFields, spa_fields) as rows:
        for fld in fields:
            vals = [target_table, target_field, features_name, fld]
            if vals not in existing:
                rows.insertRow(vals)
                log(f'Added new Spatial Join Field "{fld}" from "{features_name}" to be inserted into "{target_table}" in "{target_field}" field.')


def add_cad_vendor_fields(featureType: str, vendor: str, cad_fields: List[List[str]]):
    """adds CAD Vendor fields

    Args:
        featureType (str): the 911 Feature Type
        vendor (str): the Vendor Name
        cad_fields (List[List[str]]): the CAD Fields and their mapped field expression [['CadFieldName', '{Expression}'] ]
    """
    ng911_db = get_ng911_db()

    vendorFields = ng911_db.get_table(ng911_db.schemaTables.CAD_VENDOR_FIELDS)

    # populate fields
    existing = [f.name for f in vendorFields]
    field_expressions = {f[0]: f[1] for f in cad_fields if f[0] in existing}

    # first check for updates
    where = f"FeatureType = '{featureType}'"
    with UpdateCursor(vendorFields, ['FieldName', 'Expression', 'FeatureType'], where) as rows:
        for r in rows:
            if r[0] in field_expressions:
                if r[1] != field_expressions[r[0]]:
                    r[1] = field_expressions[r[0]]
                    rows.updateRow(r)
                    log(f'updated Custom CAD Field for "{featureType}": {r[0]} -> {r[1]}')
                    
                del field_expressions[r[0]]

    # now insert new fields
    with InsertCursor(vendorFields, ['FieldName', 'Expression', 'FeatureType', 'CADVendor']) as irows:
        for fld, exp in sorted(field_expressions.items()):
            irows.insertRow([fld, exp, featureType, vendor])
            log(f'inserted new Custom CAD Field for "{featureType}": {fld} -> {exp}')


def add_preconfigured_cad_vendor_fields(featureType= 'ADDRESS_POINTS', vendor='TRITECH'):
    """adds preconfigured CAD vendor fields

    Args:
        featureType (str, optional): _description_. Defaults to 'ADDRESS_POINTS'.
        vendor (str, optional): _description_. Defaults to 'TRITECH'.

    Raises:
        RuntimeError: Invalid Feature Type provided
    """
    
    allowed_vendors = ['TRITECH', 'TYLER', 'WTH']
    if vendor.upper() not in allowed_vendors:
        raise RuntimeError(f'Invalid Vendor Name Supplied: "{vendor}"')

    config = load_vendor_config(vendor)

    try:
        schema = [s for s in config.schemas if s.get('featureType').upper() == featureType][0]

    except IndexError:
        raise RuntimeError(f'Invalid Feature Type provided: "{featureType}"')

    # check to make sure fields exist in table
    ng911_db = get_ng911_db()
    table = ng911_db.get_911_table(featureType)
    existing = [f.name for f in arcpy.ListFields(table)]
    for fmap in schema.fieldMap:
        if fmap.name not in existing:
            try:
                arcpy.AddField_management(table, fmap.name, fmap.type, field_length=fmap.get('length'))
                log(f'Added CAD Vendor field "{fmap.name}" to "{featureType}"')
            except Exception as e:
                log(f'Failed to CAD Vendor field "{fmap.name}" to "{featureType}": {e}', level='warn')
    
    # find cad fields from config
    cad_fields = [[f.name, f.expression] for f in schema.fieldMap]
    add_cad_vendor_fields(schema.featureType, vendor, cad_fields)

  