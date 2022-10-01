import enum
from operator import ge
import os
import re
import arcpy
import glob
import datetime
from typing import List

from attr import field
from ..env import NG_911_DIR, get_ng911_db
from ..logging import log
from ..utils.cursors import find_ws, UpdateCursor, InsertCursor
from ..utils.json_helpers import load_json
from ..utils.helpers import field_types, find_nena_guid_field
from ..support.munch import munchify
from ..config import write_config
from ..core.database import NG911SchemaTables
from ..schemas import DATA_TYPES, DATA_TYPES_LOOKUP, DEFAULT_NENA_PREFIXES
from ..core.validators import VALIDATION_FLAGS

def features_from_json(json_file: str, out_path: str):
    """create features from a json file, will also add
    necessary domains.

    Args:
        json_file (str): the input json file
        out_path (str): the output feature class
    """
    # first check for domains in fields
    fs = load_json(json_file)
    domains = munchify([dict(field=f, **f.domain) for f in fs.fields if f.get('domain')])

    ws, ws_type = find_ws(out_path, return_type=True)
    if domains and ws_type in ('LocalDatabase', 'RemoteDatabase'):
        doms = {d.name: d for d in arcpy.da.ListDomains(ws)}
        for dom in domains:
            if dom.name not in doms:
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
    arcpy.conversion.JSONToFeatures(json_file, out_path)
    log(f'Converted json file to features: "{out_path}"')

    # now assign domains
    for dom in domains:
        arcpy.management.AssignDomainToField(out_path, dom.field.name, dom.name)
        log(f'Assigned "{dom.name}" domain to "{dom.field.name}" field.')
    return out_path
    

def create_ng911_admin_gdb(ng911_gdb: str, schemas_gdb_path: str, county: str, config_file='config.json') -> str:
    """creates the NG911_SchemaTables.gdb

    Args:
        ng911_gdb (str): the ng911 geodatabase path
        schemas_gdb_path (str): the geodatabase folder path
        county (str): the county for 
        config_file (str, optional): _description_. Defaults to 'config.json'.

    Returns:
        str: _description_
    """
    out_gdb = os.path.join(schemas_gdb_path, 'NG911_Schemas.gdb')

    if not arcpy.Exists(out_gdb):
        arcpy.management.CreateFileGDB(*os.path.split(out_gdb))
        log(f'Created NG911 Schema Geodatabase: "{out_gdb}"')

    # create all tables
    schemas_dir = os.path.join(NG_911_DIR, 'admin', 'data_structures')
    for fl in glob.glob(os.path.join(schemas_dir, '*.json')):
        basename = os.path.basename(fl)
        table = os.path.join(out_gdb, basename.split('.')[0])

        # create if missing
        if not arcpy.Exists(table):
            features_from_json(fl, table)

    # write config file
    agencyId = f'@{county.lower()}coil.org'
    conf = {
        'ng911GDBPath': ng911_gdb,
        'ng911GDBSchemasPath': out_gdb,
        'createdBy': os.getenv('username'),
        'created': datetime.datetime.utcnow().isoformat(),
        'county': county,
        'agencyId': agencyId
    }

    if not config_file.endswith('.json'):
        config_file += '.json'

    write_config(conf, config_file)

    # check for relationship class for vendors to fields
    hasVendorRel, hasSpatialRel = False, False
    vendorRel = 'CADVendorsRel'
    spatialRel = 'SpatailJoinFeaturesRel'
    for dirpath, dirnames, rels in arcpy.da.Walk(out_gdb, datatype='RelationshipClass'):
        for rel in rels:
            log(f'relationship class: "{rel}"')
            if rel == vendorRel:
                hasVendorRel = True
                log('found existing CAD Vendors relationship')
                
            if rel == spatialRel:
                hasSpatialRel = True
                log('found existing spatial join features relationship')

    if not hasVendorRel:
        # create relationship class
        cadVendors = os.path.join(out_gdb, NG911SchemaTables.CAD_VENDOR_FEATURES)
        cadFields = os.path.join(out_gdb, NG911SchemaTables.CAD_VENDOR_FIELDS)
        arcpy.management.CreateRelationshipClass(
            cadVendors, 
            cadFields, 
            os.path.join(out_gdb, vendorRel), 
            'COMPOSITE', 
            'VendorFields', 
            'CADVendor', 
            'BOTH', 
            'ONE_TO_MANY', 
            'ATTRIBUTED', 
            'TableName',
            'TableName',
        )
        log(f'created "{vendorRel}" relationship')

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

    with UpdateCursor(table, ['County', 'AgencyID']) as rows:
        for r in rows:
            rows.updateRow([county, agencyId])

    log(f'set agency ID: "{agencyId}"')

    # check for core feature classes
    schemaTable = os.path.join(out_gdb, NG911SchemaTables.NG911_TABLES)
    with arcpy.da.SearchCursor(schemaTable, ['FeatureType', 'Path']) as rows:
        existing = [r[0] for r in rows if r[1] and arcpy.Exists(r[1])]

    # try to find required feature classes
    toAdd = [p for p in DATA_TYPES if p not in existing]

    # walk through gdb
    with InsertCursor(schemaTable, ['Basename', 'Path', 'FeatureType', 'NENA_Prefix', 'GUID_Field']) as rows:
        for root, fds, tables in arcpy.da.Walk(ng911_gdb):
            for tab in tables:
                target = DATA_TYPES_LOOKUP.get(tab)
                full_path = os.path.join(root, tab)
                guid_field = find_nena_guid_field(full_path)
                if target and target in toAdd:
                    rows.insertRow((tab, full_path, target, DEFAULT_NENA_PREFIXES.get(target), guid_field))
                    log(f'Found Schema for "{target}" -> "{tab}"')


    # populate nena ids
    register_nena_identifiers()


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


def register_nena_identifiers():
    ng_911_db = get_ng911_db()
    if not ng_911_db.setupComplete:
        raise RuntimeError('Setup has not been completed for NG911 Database!')
    
    log('preparing to register NENA Identifiers')

    # validate nena identifier table
    ng_911_db.valiate_nena_id_fields()
    nenaTab = os.path.join(ng_911_db.gdb_path, 'NENA_IDs')
    if not arcpy.Exists(nenaTab):
        arcpy.CreateTable_management(*os.path.split(nenaTab))
        log(f'Created "NENA_Identifiers" table"')

    fields = [f.name for f in arcpy.ListFields(nenaTab)]
    for ftype in ng_911_db.types:
        log(f'checking NENA Idenfiers in "{ftype}"')
        
        ngTab = ng_911_db.get_911_table(ftype)
        
        # check for guid field
        guid_field = find_nena_guid_field(ngTab)

        # default uid to 1
        uid = 1
        if guid_field:
            if ftype not in fields:

                # add field
                arcpy.management.AddField(nenaTab, ftype, 'LONG')
                log(f'added NENA Identifier field "{ftype}')
                
            # find max id
            where = f'{guid_field} is not null'
            with arcpy.da.SearchCursor(ngTab, [guid_field], where_clause=where) as rows:
                for r in rows:
                    try:
                        guid = int(''.join([t for t in r[0].split('@')[0] if t.isdigit()]))
                    except:
                        guid = 0
                        log(f'failed to parse nena identifier: "{r[0]}"')

                    if guid and guid > uid:
                        uid = guid

            count = int(arcpy.management.GetCount(nenaTab).getOutput(0))
            if not count:
                with InsertCursor(nenaTab, [ftype]) as irows:
                    irows.insertRow([uid])
                    log(f'found MAX NENA Identifier for "{ftype}": {uid}')
            else:
                # record already exists, just update it
                with UpdateCursor(nenaTab, [ftype]) as rows:
                    for i, r in enumerate(rows):
                        if i == 0:
                            rows.updateRow([uid])
                            log(f'found MAX NENA Identifier for "{ftype}": {uid}')
                        else:
                            rows.deleteRow()
                            log(f'removed NENA IDs row at index: {i}')


def add_cad_vendor_fields(cad_path: str, table: str, vendor: str, cad_fields: List[List[str]]):
    ng911_db = get_ng911_db()

    vendorFeats = ng911_db.schemaTables.CAD_VENDOR_FEATURES
    vendorFields = ng911_db.schemaTables.CAD_VENDOR_FIELDS

    where = f"CADFeatureTable = '{cad_path}'"
    tab = ng911_db.get_table_view(vendorFeats, where)
    table_name = os.path.basename(cad_path)

    if not int(arcpy.management.GetCount(tab).getOutput(0)):
        # add record
        with InsertCursor(vendorFeats, ['CADFeatureTable', 'TableName', 'FeatureType', 'CADVendor']) as irows:
            irows.insertRow([cad_path, table_name, table, vendor])
            log(f'registered new CAD Feature "{table_name}"-> {table}')

    # populate fields
    field_expressions = {f[0]: f[1] for f in cad_fields}

    # first check for updates
    where = f"TableName = '{table_name}'"
    with UpdateCursor(vendorFields, ['FieldName', 'Expression', 'TableName'], where) as rows:
        for r in rows:
            if r[0] in field_expressions:
                r[1] = field_expressions[r[0]]
                del field_expressions[r[0]]
                rows.updateRow(r)
                log(f'updated Custom CAD Field for "{table_name}": {fld} -> {exp}')

    # now insert new fields
    with InsertCursor(vendorFields, ['FieldName', 'Expression', 'TableName']) as irows:
        for fld, exp in sorted(field_expressions.items()):
            irows.insertRow([fld, exp, table_name])
            log(f'inserted new Custom CAD Field for "{table_name}": {fld} -> {exp}')