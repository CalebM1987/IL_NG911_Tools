import os
import arcpy
import glob
import datetime
from ..env import NG_911_DIR, get_ng911_db
from ..logging import log
from ..utils.cursors import find_ws, UpdateCursor
from ..utils.json_helpers import load_json
from ..utils.helpers import field_types
from ..support.munch import munchify
from ..config import write_config
from ..core.database import NG911SchemaTables

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
                        log(f'added {len(dom.codedValues)} to domain: "{dom.name}"')
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
    

def create_ng911_admin_gdb(gdb_path: str, county: str, config_file='config.json') -> str:
    """creates the NG911_SchemaTables.gdb

    Args:
        gdb_path (str): the geodatabase folder path
        county (str): the county for 
        config_file (str, optional): _description_. Defaults to 'config.json'.

    Returns:
        str: _description_
    """
    out_gdb = os.path.join(gdb_path, 'NG911_Schemas.gdb')

    if not arcpy.Exists(out_gdb):
        arcpy.CreateFileGDB_management(*os.path.split(out_gdb))
        log(f'Created NG911 Tables Schema: "{out_gdb}"')

    # create all tables
    schemas_dir = os.path.join(NG_911_DIR, 'admin', 'data_structures')
    for fl in glob.glob(os.path.join(schemas_dir, '*.json')):
        basename = os.path.basename(fl)
        table = os.path.join(out_gdb, basename.split('.')[0])

        # create if missing
        if not arcpy.Exists(table):
            features_from_json(fl, table)

    # write config file
    conf = {
        'ng911GDBPath': out_gdb,
        'createdBy': os.getenv('username'),
        'created': datetime.datetime.utcnow().isoformat()
    }

    write_config(conf, config_file)

    # get ng911_db helper
    ng911_db = get_ng911_db(config_file)

    # check for relationship class for vendors to fields
    hasVendorRel = False
    vendorRel = 'CADVendorsRel'
    for dirpath, dirnames, rels in arcpy.da.Walk(out_gdb, datatype='RelationshipClass'):
        for rel in rels:
            log(f'relationship class: "{rel}"')
            if rel == vendorRel:
                hasVendorRel = True
                log('found existing CAD Vendors relationship')
                break

    if not hasVendorRel:
        # create relationship class
        cadVendors = ng911_db.get_table(NG911SchemaTables.CAD_VENDOR_FEATURES)
        cadFields = ng911_db.get_table(NG911SchemaTables.CAD_VENDOR_FIELDS)
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
            'CADVendor',
            'CADVendor',
        )

    # set agency info
    table = ng911_db.get_table(NG911SchemaTables.AGENCY_INFO)

    with UpdateCursor(table, ['County', 'AgencyID']) as rows:
        for r in rows:
            rows.updateRow([county, f'@{county}COIL.ORG'])
    log(f'set agency ID: "@{county}COIL.ORG"')