import os
import re
import arcpy
import time
import datetime
from ..utils import lazyprop
from ..utils.json_helpers import load_json
from ..support.munch import Munch
from .enums import FieldCategory
from ..core.common import Feature, FeatureBase, LOCATION_FIELDS, is_shape_field
from ..env import ng911_db, is_arc
from typing import List, Dict
from ..utils import cursors, message, copy_schema
from functools import partial

schemasDir = os.path.join(os.path.dirname(__file__), '_schemas')

class DataType:
    ADDRESS_POINTS="AddressPoints"
    ROAD_CENTERLINE="RoadCenterline"
    PROVISIONING_BOUNDARY="ProvisioningBoundary"
    ZIP_CODES="ZipCodes"
    PSAP="PSAP"
    ESB="ESB"
    ESB_EMS="ESB_EMS"
    ESB_FIRE="ESB_Fire"
    ESB_LAW="ESB_Law"
    INCORPORATED_MUNICIPAL="IncorporatedMunicipal"
    UNINCORPORATED_MUNICIPAL="UnincorporatedMunicipal"

def load_schema(name: str) -> Munch:
    """loads a json schema

    Args:
        name (str): the name of the json schema to load

    Returns:
        Munch: the schema
    """
    if hasattr(DataType, name):
        name = getattr(DataType, name)
    fl = os.path.join(schemasDir, name + '.json')
    if os.path.exists(fl):
        return load_json(fl)

class DataSchema(FeatureBase):
    totalCount = 0

    def __init__(self, name: str):
        self._schema = load_schema(name)
        self.table = ng911_db.get_911_table(name)
        self._features = []
        self._commited = []

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
    def customFields(self):
        table = ng911_db.get_table(ng911_db.schemaTables.CUSTOM_FIELDS)
        print('table is: ', table)
        where = f"TargetTable = '{self._schema.featureType}'"
        # fieldNames = [f.name for f in arcpy.ListFields(table)]
        # print(fieldNames)
        fields = ['Name', 'TargetTable',  'Expression']
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
        try:
            return [f.name for f in self.fields if f.name.endswith('_NGUID')][0]
        except IndexError:
            print('could not get nena identifier field...')
            return 'Site_NGUID'

    @lazyprop
    def agencyPrefix(self): 
        where = f"Basename = '{self._schema.layer}'"
        prefix = ''
        table = ng911_db.get_table(ng911_db.schemaTables.NG911_TABLES)
        with arcpy.da.SearchCursor(table, ['NENA_Prefix', 'Basename'], where) as rows:
            try:
                prefix = [r[0] for r in rows][0]
            except IndexError:
                pass
        return prefix

    def create_identifier(self, oid: int=0) -> str:
        """form a unique NENA compliant identifier

        Args:
            oid (int): the objectid or number for identifier
            ft (Feature): an optional feature to pass in, if a feature is 
                found the unique identifier is automatically added to its attributes

        Returns:
            str: the NENA identifier
        """
        count = len(self._features) + 1
        sql_clause=(None, f'ORDER BY {self.oidField} DESC')
        pat = re.compile(f'{self.agencyPrefix}([0-9]+){ng911_db.agencyID}', re.I)
        ids = []
        with arcpy.da.SearchCursor(self.table, [self.oidField, self.nenaIdentifier], sql_clause=sql_clause) as rows:
            for i,r in enumerate(rows):
                m = pat.match(r[1])
                if m:
                    groups = m.groups()
                    try:
                        ids.append(int(groups[0]))

                    except IndexError:
                        ids.append(r[0])
                else:
                    ids.append(r[0])
                if i > 5:
                    break
        print('ids yo: ', ids)
        if ids:
            oid = max(ids) + count
            print('max id: ', oid)
        else:
            oid = int(arcpy.management.GetCount(self.table).getOutput(0)) + count
            
        return f'{self.agencyPrefix}{oid}{ng911_db.agencyID}'

    def calculate_custom_fields(self, ft: Feature):
        for field in self.customFields:
            expr = ft.calculate_custom_field(field.name, field.expression)
            print(f'calculatd {field}: {expr}')

    def get_layer(self) -> arcpy._mp.Layer:
        """will fetch an arcpy._mp.Layer for the parent feature class

        Returns:
            arcpy._mp.Layer: the feature layer
        """
        return ng911_db.get_911_layer(self._schema.layer)

    def create_feature(self, geometry: arcpy.Geometry=None, **kwargs) -> Feature:
        """create a new feature

        Args:
            geometry (arcpy.Geometry, optional): [description]. Defaults to None.

        Returns:
            Feature: the feature template
        """
        if self._schema.layer == DataType.ADDRESS_POINTS:
            kwargs.update({
                LOCATION_FIELDS.STATE: ng911_db.state,
                LOCATION_FIELDS.COUNTRY: ng911_db.country,
                LOCATION_FIELDS.COUNTY: f'{ng911_db.county} COUNTY'
            })
    
        kwargs[self.nenaIdentifier] = self.create_identifier()
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
            print('editable fields: ', editable_fields)
            copyTab = copy_schema(self.table, time.strftime(r'in_memory\temp_%Y%m%d%H%M%S'))
           
            if is_arc: 
                irows = arcpy.da.InsertCursor(copyTab, editable_fields + ['SHAPE@'])
                message('editing in arcgis pro', self.table)
                for ft in self._features:
                    if not ft.attributes.get(self.oidField):
                        row = [ft.attributes.get(f) for f in editable_fields] + [ft.geometry]
                        message(row)
                        irows.insertRow(row)
                        self._commited.append(ft)
                        self._features.remove(ft)
                        count += 1
                del irows

                # now append to actual table
                arcpy.management.Append(copyTab, self.table, 'NO_TEST')
                arcpy.management.Delete(copyTab)
            else:
                message('using in standalone, starting edit session')
                with cursors.InsertCursor(self.table, editable_fields + ['SHAPE@']) as irows:
                    for ft in self._features:
                        print('ft yo: ', ft, ft.attributes.get(self.oidField))
                        if not ft.attributes.get(self.oidField):
                            self.create_identifier
                            irows.insertRow([ft.attributes.get(f) for f in editable_fields] + [ft.geometry])
                            self._commited.append(ft)
                            self._features.remove(ft)
                            count += 1
            
            # # now update with ids
            # nenaCount = 0
            # where = f'{self.nenaIdentifier} is null'
            # with cursors.UpdateCursor(self.table, ['OID@', self.nenaIdentifier, 'DateUpdate'], where) as rows:
            #     for r in rows:
            #         r[1] = self.create_identifier(r[0])
            #         r[2] = datetime.datetime.now().date()
            #         rows.updateRow(r)
            #         nenaCount += 1
        message(f"Committed {count} features in {self._schema.layer} table.")
        # if nenaCount:
        #     message(f"Created NENA Identifier for {count} features in {self._schema.layer} table.")

        return count






 

    