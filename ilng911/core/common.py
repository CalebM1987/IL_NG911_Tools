import re
import arcpy
import json
import datetime
# from ..schemas import DataSchema, DataType
# from ..env import get_ng911_db 
from ..support.munch import Munch, munchify
from ..utils import lazyprop, date_to_mil
from typing import List
from .parser import *
from ..logging import log
from .fields import NUMERIC_FIELDS, INTEGER_FIELDS, FLOAT_FIELDS

SHAPE_PAT = re.compile('^(shape)[@]?', re.I)
SHAPE_ATTR_PAT = re.compile('^(shape)[@._](\w+)', re.I)
WGS_84_WKID = 4326
WGS_84 = arcpy.SpatialReference(WGS_84_WKID)
WEB_MERCATOR_WKID = 102100
WEB_MERCATOR = arcpy.SpatialReference(WEB_MERCATOR_WKID)

LOCATION_FIELDS = munchify(
    dict(
        LATITUDE='Lat',
        LONGITUDE='Long',
        ZIP_CODE='Post_Code',
        ZIP_CODE4='Post_Code4',
        COUNTRY='Country',
        COUNTY='County',
        STATE='State'
    )
)

def is_shape_field(fld: str) -> bool:
    return SHAPE_PAT.fullmatch(fld) is not None

class FeatureBase:

    @lazyprop
    def fieldNames(self) -> List[str]:
        return [f.name for f in self.fields if f.type != 'Geometry']

    @lazyprop
    def numericFields(self) -> List[str]:
        return [f.name for f in self.fields if f.type in NUMERIC_FIELDS]

    @lazyprop
    def integerFields(self) -> List[str]:
        return [f.name for f in self.fields if f.type in INTEGER_FIELDS]
    
    @lazyprop
    def floatFields(self) -> List[str]:
        return [f.name for f in self.fields if f.type in FLOAT_FIELDS]

    @lazyprop
    def oidField(self):
        return [f.name for f in self.fields if f.type == 'OID'][0]

class NG911Encoder(json.JSONEncoder):
    """Encoder to make serializeable for JSON."""
    def default(self, o):
        """Encodes object for JSON.
        Args:
            o: Object.
        """
        if isinstance(o, (datetime.datetime, datetime.date)):
            return date_to_mil(o)

        elif isinstance(o, arcpy.Geometry):
            arcpy.PointGeometry.JSON
            return json.loads(o.JSON)
    
        elif isinstance(o, (dict, list)):
            return o
        try:
            return o.__dict__
        except:
            return o.__class__.__name__ #{}

class Feature(FeatureBase):
    def __init__(self, fields: List[arcpy.Field], geometry: arcpy.Geometry=None, **kwargs):
        
        self.fields = fields
        self.geometry = geometry
        self.attributes = {}
        
        oid = None
        for fld, val in kwargs.items():
            if is_shape_field(fld):
                if not self.geometry and isinstance(val, arcpy.Geometry):
                    self.geometry = val
                
            elif fld.lower() == 'oid@':
                oid = val

        if oid:
            kwargs[self.oidField] = oid
            
        # set attributes
        if (LOCATION_FIELDS.LATITUDE in self.fieldNames and LOCATION_FIELDS.LONGITUDE in self.fieldNames) and geometry:
            if geometry.spatialReference.factoryCode != WGS_84_WKID:
                wgs84 = geometry.projectAs(arcpy.SpatialReference(WGS_84_WKID))
            else:
                wgs84 = geometry
            kwargs[LOCATION_FIELDS.LATITUDE] = wgs84.centroid.Y
            kwargs[LOCATION_FIELDS.LONGITUDE] = wgs84.centroid.X

        # log(f'kwargs before filtering:\n{json.dumps(kwargs, indent=4, cls=NG911Encoder)}')
        self.attributes.update(self.filter_attrs(kwargs))
        # log(f'filtered kwargs:\n{json.dumps(self.filter_attrs(kwargs), indent=4, cls=NG911Encoder)}')

    @lazyprop
    def _writable(self):
        return [f for f in self.fieldNames if not SHAPE_ATTR_PAT.match(f)]

    def filter_attrs(self, kwargs={}) -> Munch:
        return munchify({k: kwargs.get(k) for k in self._writable if not self.attributes.get(k)})

    def get(self, attribute: str, default=None):
        """shorthand getter for any feature attributes

        Args:
            attribute (str): the attribute name (must be a valid field or field token)
            default ([type], optional): [description]. Defaults to None.

        Returns:
            the desired attribute
        """
        return self.attributes.get(attribute, default)

    def update(self, **kwargs):
        self.attributes.update(self.filter_attrs(kwargs))

    def toJson(self) -> Munch:
        """ convert Feature to JSON object """
        return munchify(
            dict(
                attributes=self.attributes,
                geometry=json.loads(self.geometry.JSON) if self.geometry else None
            )
        )

    def create_from_expression(self, expression: str='', cast=None) -> str:
        """creates a string from a given expression

        Args:
            expression (str, optional): the string expression with field tokens. Defaults to ''.

        Returns:
            str: the result of the calculated expression
        """
        tokens = get_string_tokens(expression)
        val = expression[:]
        for token in tokens:
            raw = token.strip('{}') 
            if raw in self.fieldNames:
                # replace None with 0 if numeric
                rep = 0 if raw in self.numericFields else ''
                val = re.sub(token, str(self.get(raw) or rep), val, flags=re.I)
            elif raw == CUSTOM_TOKENS.PreDirectionAbbr:
                if self.get(FIELDS.STREET.PRE_DIRECTION):
                    val = re.sub(token, STREET_DIRECTIONS_ABBR.get(self.get(FIELDS.STREET.PRE_DIRECTION) or ''), val, flags=re.I)
                else:
                    val = val.replace(token, '')
            elif raw == CUSTOM_TOKENS.PostDirectionAbbr:
                if self.get(FIELDS.STREET.POST_DIRECTION):
                    val = re.sub(token, STREET_DIRECTIONS_ABBR.get(self.get(FIELDS.STREET.POST_DIRECTION) or ''), val, flags=re.I)
                else:
                    val = val.replace(token, '')
                    
        val = ' '.join(val.split()) or None

        # really loose check for 
        if any(map(lambda o: o in val, '*/+-')):
            try:
                return safe_eval(val)
            except Exception as e:
                log(f'failed to process expression: "{expression}"')
        return cast(val) if (cast and val) else val

    def calculate_custom_field(self, field: str, expression: str, cast=None) -> str:
        """calculates a custom field from a given expression

        Args:
            field (str)
            expression (str): the string expression with field tokens. Defaults to ''.

        Returns:
            str: the result of the calculated expression
        """
        log(f'calculate custom expression is: "{expression}"')

        # check for numeric and cast
        if not cast and field in self.numericFields:
            cast = float if field in self.floatFields else int

        val = self.create_from_expression(expression, cast)
        self.attributes[field] = val
        return val

    def prettyPrint(self):
        """ pretty prints the json feature"""
        dct = self.toJson()

        # fix geometry
        if dct.get('SHAPE@'):
            del dct['SHAPE@']
            dct['geometry'] = self.geometry

        log(json.dumps(dct, cls=NG911Encoder, indent=2))

    def toRow(self, fields: List[str]):
        vals = []
        for f in fields:
            if f in self.attributes:
                vals.append(self.attributes[f])
            elif is_shape_field(f):
                vals.append(self.geometry)
            elif f.lower() == 'oid@':
                vals.append(self.objectId)
        return vals
