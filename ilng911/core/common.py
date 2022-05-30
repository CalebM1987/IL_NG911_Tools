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
    def oidField(self):
        return [f.name for f in self.fields if f.type == 'OID'][0]

class NG911Encoder(json.JSONEncoder):
    """Encoder to make serializeable for JSON."""
    def default(self, o):
        """Encodes object for JSON.
        Args:
            o: Object.
        """
        if isinstance(o, datetime.datetime):
            return date_to_mil(o)
    
        elif isinstance(o, (dict, list)):
            return o
        try:
            return o.__dict__
        except:
            return o.__class__.__name__ #{}

class Feature(FeatureBase):
    def __init__(self, fields: List[str], geometry: arcpy.Geometry=None, **kwargs):
        
        self.fields = fields
        self.geometry = geometry
        self.attributes = {}
        
        for fld, val in kwargs.items():
            if is_shape_field(fld):
                if not self.geometry and isinstance(val, arcpy.Geometry):
                    self.geometry = val
                
            elif fld.lower() == 'oid@':
                kwargs[self.oidField] = val

        # set attributes
        if (LOCATION_FIELDS.LATITUDE in self.fieldNames and LOCATION_FIELDS.LONGITUDE in self.fieldNames) and geometry:
            if geometry.spatialReference.factoryCode != WGS_84_WKID:
                wgs84 = geometry.projectAs(arcpy.SpatialReference(WGS_84_WKID))
            else:
                wgs84 = geometry
            kwargs[LOCATION_FIELDS.LATITUDE] = wgs84.centroid.Y
            kwargs[LOCATION_FIELDS.LONGITUDE] = wgs84.centroid.X

        self.attributes.update(self.filter_attrs(kwargs))

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
        return munchify(
            dict(
                attributes=self.attributes,
                geometry=json.loads(self.geometry.JSON)
            )
        )

    def create_from_expression(self, expression: str='') -> str:
        tokens = get_string_tokens(expression)
        expr = expression.split(' ')
        for i, part in enumerate(expr):
            if part in tokens:
                raw = part.strip('{}') 
                if raw in self.fieldNames:
                    expr[i] = self.get(raw)
                elif raw == CUSTOM_TOKENS.PreDirectionAbbr:
                    expr[i] = STREET_DIRECTIONS_ABBR.get(self.get(FIELDS.STREET.PRE_DIRECTION))
                elif raw == CUSTOM_TOKENS.PostDirectionAbbr:
                    expr[i] = STREET_DIRECTIONS_ABBR.get(self.get(FIELDS.STREET.POST_DIRECTION))
        return ' '.join(map(str, filter(None,expr)))

    def calculate_custom_field(self, field: str, expression: str) -> str:
        log(f'calculate custom expression is: "{expression}"')
        expr = self.create_from_expression(expression)
        self.attributes[field] = expr
        return expr

    def prettyPrint(self):
        log(json.dumps(self.toJson(), cls=NG911Encoder, indent=2))

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
