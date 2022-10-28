import os
import re
import arcpy
import time
import datetime
from ..utils import lazyprop
from ..utils.json_helpers import load_json
from ..support.munch import Munch, munchify
from .enums import FieldCategory
from ..core.fields import TYPE_MAPPING
from ..core.common import Feature, FeatureBase, LOCATION_FIELDS, is_shape_field
from ..env import get_ng911_db, DEBUG_WS
from typing import List, Dict
from ..utils import cursors, copy_schema, is_arc, PropIterator
from functools import partial
from ..logging import log
from ..utils.helpers import find_nena_guid_field

schemasDir = os.path.join(os.path.dirname(__file__), '_schemas')
esb_pattern = re.compile('(esb?_*)', re.I)

class DataType(PropIterator):
    ADDRESS_POINTS="AddressPoints"
    ROAD_CENTERLINE="RoadCenterline"
    PROVISIONING_BOUNDARY="ProvisioningBoundary"
    ZIP_CODES="ZipCodes"
    PSAP="PSAP"
    ESB="ESB"
    ESB_EMS="ESB_EMS"
    ESB_FIRE="ESB_FIRE"
    ESB_LAW="ESB_LAW"
    INCORPORATED_MUNICIPAL="IncorporatedMunicipal"
    UNINCORPORATED_MUNICIPAL="UnincorporatedMunicipal"

DATA_TYPES = DataType()

DATA_TYPES_LOOKUP = munchify({ getattr(DATA_TYPES, p): p for p in DATA_TYPES })

DEFAULT_NENA_PREFIXES = munchify(
    dict(
        ADDRESS_POINTS='SITE',
        ROAD_CENTERLINE='RCL',
        PROVISIONING_BOUNDARY='PB',
        PSAP='PSAP',
        ESB='ES',
        ESB_EMS='EMS',
        ESB_FIRE='FIRE',
        ESB_LAW='LAW',
        INCORPORATED_MUNICIPAL='INCMUNI',
        UNINCORPORATED_MUNICIPAL='UNINCMUNI',
        ZIP_CODES='ZIP'
    )
)

def load_schema(name: str) -> Munch:
    """loads a json schema

    Args:
        name (str): the name of the json schema to load

    Returns:
        Munch: the schema
    """
    if hasattr(DataType, name):
        name = getattr(DataType, name)
    isESB = esb_pattern.match(name) is not None
    fl = os.path.join(schemasDir, ('PSAP' if isESB else name) + '.json')
    if os.path.exists(fl):
        _schema = load_json(fl)
    if isESB:
        _schema.featureType = name
        _schema.layer = name
        for fld in _schema.featureSet.fields:
            if fld.name == 'PB_NGUID':
                fld.name = 'ES_NGUID'
    return _schema
        

class DataSchema(FeatureBase):
    totalCount = 0

    def __init__(self, name: str):
        self._schema = load_schema(name)
        self.ng911_db = get_ng911_db()
        self.table = self.ng911_db.get_911_table(name)
        self._features = []
        self._commited = []

    @property
    def name(self):
        return (self._schema or {}).get('featureType')

    @lazyprop
    def reservedFields(self):
        return [f.name for f in self._schema.get('fieldInfos', []) if f.category == FieldCategory.RESERVED]

    @lazyprop
    def requiredFields(self):
        return [f.name for f in self._schema.get('fieldInfos', []) if f.category == FieldCategory.MANDATORY]

    @lazyprop
    def conditionalFields(self):
        return [f.name for f in self._schema.get('fieldInfos', []) if f.category == FieldCategory.CONDITIONAL]

    @lazyprop
    def optionalFields(self):
        return [f.name for f in self._schema.get('fieldInfos', []) if f.category == FieldCategory.OPTIONAL]

    @lazyprop
    def fields(self) -> List[arcpy.Field]:
        return arcpy.ListFields(self.table)

    @lazyprop
    def fieldTypings(self):
        return munchify({f.name: TYPE_MAPPING.get(f.type, str) for f in self.fields})

    @lazyprop
    def vendorFields(self):
        where = f"FeatureType = '{self.name}'"
        print('vendor fields where: ', where)
        table = self.ng911_db.get_table(self.ng911_db.schemaTables.CAD_VENDOR_FIELDS)

        feats = {}
        with arcpy.da.SearchCursor(table, ['FeatureType', 'FieldName', 'Expression'], where) as rows:
            for r in rows:
                info = {
                    'name': r[1],
                    'expression': r[2],
                    'type': self.fieldTypings.get(r[1])
                }
                if r[0] in feats:
                    feats[r[0]].append(info) 
                else:
                    feats[r[0]] = [ info ]

        return munchify(feats)

    @lazyprop
    def customFields(self):
        table = self.ng911_db.get_table(self.ng911_db.schemaTables.CUSTOM_FIELDS)
        log(f'table for custom fields is: {table}')
        where = f"TargetTable = '{self._schema.featureType}'"
        # fieldNames = [f.name for f in arcpy.ListFields(table)]
        # print(fieldNames)
        fields = ['FieldName', 'TargetTable',  'Expression']
        flookup, ftypings = {}, {}
        for f in self.fields:
            flookup
        flookup = { f.name: f for f in self.fields }
        custFields = []

        with arcpy.da.SearchCursor(table, fields, where) as rows:
            for r in rows:
                if r[0] in self.fieldNames:
                    fld = flookup[r[0]]
                    fld.expression = r[2]
                    custFields.append(fld)

        return custFields

    @lazyprop
    def nenaIdentifier(self):
        guid_field = find_nena_guid_field(self.table)
        if guid_field:
            return guid_field
        else:
            log('could not get nena identifier field...', 'warn')
            return 'Site_NGUID'

    @lazyprop
    def agencyPrefix(self): 
        where = f"Basename = '{self._schema.layer}'"
        prefix = ''
        table = self.ng911_db.get_table(self.ng911_db.schemaTables.NG911_TABLES)
        with arcpy.da.SearchCursor(table, ['NENA_Prefix', 'Basename'], where) as rows:
            try:
                prefix = [r[0] for r in rows][0]
            except IndexError:
                pass
        return prefix

    def create_identifier(self) -> str:
        """form a unique NENA compliant identifier

        Args:
            oid (int): the objectid or number for identifier
            ft (Feature): an optional feature to pass in, if a feature is 
                found the unique identifier is automatically added to its attributes

        Returns:
            str: the NENA identifier
        """
        new_id = self.ng911_db.get_next_nena_id(self.name) 
        return f'{self.agencyPrefix}{new_id}@{self.ng911_db.agencyID}'
        

    def calculate_custom_fields(self, ft: Feature):
        """calculate all custom fields for feature

        Args:
            ft (Feature): the feature to calculate fields for
        """
        for field in self.customFields:
            expr = ft.calculate_custom_field(field.name, field.expression, self.fieldTypings.get(field.name))
            log(f'calculated {field}: {expr}')

    def calculate_vendor_fields(self, ft: Feature):
        """calculate all custom CAD Vendor fields for feature

        Args:
            ft (Feature): the feature to calculate fields for
        """
        for tab, vendorFields in self.vendorFields.items():
            log(f'calculating CAD Vendor fields for table: "{tab}"')
            fields = [v.name for v in vendorFields]

            # get type lookup
            vl = {v.name: v for v in vendorFields}
           
            if fields:
                with cursors.InsertCursor(self.table, fields) as irows:
                    try:
                        irows.insertRow([ft.create_from_expression(vl.get(f).expression, vl.get(f).get('type')) for f in fields])
                    except Exception as e:
                        log(f'failed to insert CAD Vendor Record', e, level='warn')

    def get_layer(self) -> arcpy._mp.Layer:
        """will fetch an arcpy._mp.Layer for the parent feature class

        Returns:
            arcpy._mp.Layer: the feature layer
        """
        return self.ng911_db.get_911_layer(self._schema.layer)

    def create_feature(self, geometry: arcpy.Geometry=None, **kwargs) -> Feature:
        """create a new feature

        Args:
            geometry (arcpy.Geometry, optional): [description]. Defaults to None.

        Returns:
            Feature: the feature template
        """
        if self._schema.layer == DataType.ADDRESS_POINTS:
            kwargs.update({
                LOCATION_FIELDS.STATE: self.ng911_db.state,
                LOCATION_FIELDS.COUNTRY: self.ng911_db.country,
                LOCATION_FIELDS.COUNTY: f'{self.ng911_db.county} COUNTY'
            })
    
        if self.nenaIdentifier not in kwargs:
            kwargs[self.nenaIdentifier] = self.create_identifier()
        if not 'DateUpdate' in kwargs:
            kwargs['DateUpdate'] = datetime.datetime.now().date()

        ft = Feature(self.fields, geometry, **kwargs)
        self._features.append(ft)
        return ft

    def update_feature(self, feature: Feature, **kwargs) -> Feature:
        """update an existing feature

        Args:
            feature (Feature): the feature to update
            **kwargs: the attributes to update


        Returns:
            Feature: [description]
        """
        feature.update(**kwargs)
        return feature

    def find_feature_from_oid(self, oid: int) -> Feature:
        """creates a Feature Instance from a given OBJECTID"""
        fields = self.fieldNames + ['SHAPE@']
        with arcpy.da.SearchCursor(self.table, fields, where_clause=f'{self.oidField} = {oid}') as rows:
            for r in rows:
                return self.fromRow(fields, r)

    def fromRow(self, fields: List[str], row: tuple) -> Feature:
        """create a feature from an arcpy.SearchCursor Row

        Args:
            fields (List[str]): list of fields in cursor
            row (tuple): the arcpy.SearchCursor Row

        Returns:
            Feature: a Feature with the attributes from the cursor Row
        """
        attrs = dict(zip(fields, row))
        geometry = None
        for i,f in enumerate(fields):
            if is_shape_field(f) and isinstance(row[i], arcpy.Geometry):
                geometry = row[i]
                break
        return self.create_feature(geometry, **attrs)

    def get_field(self, name: str) -> Munch:
        """returns the field info

        Args:
            name (str): the field name

        Returns:
            Munch: the field info containing the { name, category, ... }
        """
        fieldInfos = self._schema.get('fieldInfos', [])
        try:
            return [f for f in fieldInfos if f.name == name][0]
        except IndexError:
            return None

    def commit_features(self):
        """commits any created features from this schema instance to the database"""
        count = 0
        if self._features:
            editable_fields = [f.name for f in self.fields if f.editable]
            log(f'editable fields for schema "{self._schema.layer}": {editable_fields}')
            copyTab = copy_schema(self.table, time.strftime(os.path.join(DEBUG_WS, 'temp_%Y%m%d%H%M%S')))
           
            if is_arc: 
                irows = arcpy.da.InsertCursor(copyTab, editable_fields + ['SHAPE@'])
                log(f'editing in arcgis pro: "{self.table}"')
                for ft in self._features:
                    if not ft.attributes.get(self.oidField):
                        row = [ft.attributes.get(f) for f in editable_fields] + [ft.geometry]
                        log(f'inserting row values for "{self._schema.layer}": {row}')
                        irows.insertRow(row)
                        self._commited.append(ft)
                        self._features.remove(ft)
                        count += 1
                del irows                                        

                # now append to actual table
                arcpy.management.Append(copyTab, self.table, 'NO_TEST')
                log('appended feature to table')
                arcpy.management.Delete(copyTab)
                log('cleaned up temporary table')
            else:
                log('using in standalone, starting edit session')
                with cursors.InsertCursor(self.table, editable_fields + ['SHAPE@']) as irows:
                    for ft in self._features:
                        if not ft.attributes.get(self.oidField):
                            # skip creating identifier on insert
                            # self.create_identifier(ft.attributes.get(self.oidField))
                            irows.insertRow([ft.attributes.get(f) for f in editable_fields] + [ft.geometry])
                            self._commited.append(ft)
                            self._features.remove(ft)
                            count += 1
            
            # now update with ids
            nenaCount = 0
            where = f'{self.nenaIdentifier} is null'
            with cursors.UpdateCursor(self.table, ['OID@', self.nenaIdentifier, 'DateUpdate'], where) as rows:
                for r in rows:
                    log(f'attempting to create NENA identifier with OBJECTID: {r[0]}')
                    r[1] = self.create_identifier()
                    r[2] = datetime.datetime.now().date()
                    rows.updateRow(r)
                    nenaCount += 1

        log(f"Committed {count} features in {self._schema.layer} table.")

        if nenaCount:
            log(f"Created NENA Identifier for {count} features in {self._schema.layer} table.")

        # now register new nena highest id with identifiers table
        self.ng911_db.save_nena_id(self.name)
        log(f'registered new NENA Identifier in "{self.name}" table for numeric id {self.ng911_db.new_nena_ids.get(self.name)}')
        return count